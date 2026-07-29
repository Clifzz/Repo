'use strict';

const { extractPrice } = require('./extract');

/**
 * Page fetching, cheapest method first.
 *
 * azazie.com sits behind Cloudflare bot protection, which answers plain HTTP
 * clients from datacenter IPs with a 403 "Just a moment..." challenge page.
 * So we escalate: plain HTTP (free, sometimes enough) -> real headless
 * Chromium (executes the challenge JS) -> an optional third-party rendering
 * proxy, if the operator supplied one.
 */

const BROWSER_HEADERS = {
  'user-agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  accept:
    'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
  'accept-language': 'en-US,en;q=0.9',
  'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"macOS"',
  'sec-fetch-dest': 'document',
  'sec-fetch-mode': 'navigate',
  'sec-fetch-site': 'none',
  'sec-fetch-user': '?1',
  'upgrade-insecure-requests': '1',
};

const CHALLENGE_MARKERS = [
  'just a moment',
  'cf-browser-verification',
  'challenges.cloudflare.com',
  'enable javascript and cookies to continue',
  'checking your browser',
];

function looksLikeChallenge(html) {
  if (!html) return true;
  const head = html.slice(0, 6000).toLowerCase();
  return CHALLENGE_MARKERS.some((marker) => head.includes(marker));
}

async function fetchViaHttp(url, timeoutMs = 30000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      headers: BROWSER_HEADERS,
      redirect: 'follow',
      signal: controller.signal,
    });
    const html = await res.text();
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    if (looksLikeChallenge(html)) throw new Error('bot challenge page returned');
    return { html, text: '', domCandidates: [] };
  } finally {
    clearTimeout(timer);
  }
}

/** Harvest prices straight off the live DOM, which the raw HTML may not contain. */
async function harvestDom(page, priceSelector) {
  return page.evaluate((selector) => {
    const out = [];
    const num = (s) => {
      const cleaned = String(s || '').replace(/[^0-9.]/g, '');
      const n = Number(cleaned);
      return Number.isFinite(n) && n > 0 ? n : null;
    };

    if (selector) {
      for (const el of document.querySelectorAll(selector)) {
        const n = num(el.textContent);
        if (n !== null) out.push({ strategy: 'config-selector', price: n });
      }
    }

    const nodes = document.querySelectorAll(
      '[class*="price" i], [class*="Price"], [data-testid*="price" i], [id*="price" i]'
    );
    for (const el of nodes) {
      // Leaf-ish nodes only: containers concatenate list + sale + shipping text.
      if (el.children.length > 2) continue;
      const raw = (el.textContent || '').trim();
      if (!raw || raw.length > 40) continue;
      if (!/\$\s*\d/.test(raw)) continue;
      const strike =
        el.tagName === 'DEL' ||
        el.tagName === 'S' ||
        /through|strike|original|was|list|compare|old/i.test(el.className || '');
      const m = raw.match(/\$\s*([0-9.,]+)/);
      if (!m) continue;
      const n = num(m[1]);
      if (n !== null && !strike) out.push({ strategy: 'dom-price-class', price: n, source: raw });
    }
    return out;
  }, priceSelector || null);
}

async function fetchViaBrowser(url, opts = {}) {
  const { priceSelector = null, timeoutMs = 90000 } = opts;
  let chromium;
  try {
    ({ chromium } = require('playwright'));
  } catch {
    throw new Error('playwright is not installed');
  }

  const launchArgs = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled'];
  // channel:'chromium' runs the full browser in new-headless mode rather than
  // the headless shell, which bot filters fingerprint far more readily.
  const browser = await chromium.launch({ channel: 'chromium', args: launchArgs });

  try {
    const context = await browser.newContext({
      userAgent: BROWSER_HEADERS['user-agent'],
      locale: 'en-US',
      timezoneId: 'America/New_York',
      viewport: { width: 1440, height: 900 },
      extraHTTPHeaders: { 'accept-language': BROWSER_HEADERS['accept-language'] },
    });

    // Cheap tell that a page is automated; some bot filters check it.
    await context.addInitScript(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    });

    const page = await context.newPage();
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: timeoutMs });

    // Give a Cloudflare interstitial room to solve itself and hand off.
    for (let i = 0; i < 6; i++) {
      const html = await page.content();
      if (!looksLikeChallenge(html)) break;
      await page.waitForTimeout(5000);
    }

    await page
      .waitForFunction(() => /\$\s*\d/.test(document.body?.innerText || ''), { timeout: 20000 })
      .catch(() => {}); // absent price is handled by the extractor, not fatal here

    const html = await page.content();
    if (looksLikeChallenge(html)) throw new Error('bot challenge not cleared in browser');

    const text = await page.evaluate(() => document.body?.innerText || '');
    const domCandidates = await harvestDom(page, priceSelector);
    return { html, text, domCandidates };
  } finally {
    await browser.close().catch(() => {});
  }
}

/**
 * Optional escape hatch. Set SCRAPER_ENDPOINT to a URL template containing
 * {url}; the target URL is substituted in, encoded. Works with any rendering
 * proxy (ScraperAPI, ScrapingBee, ZenRows, self-hosted) without pinning us to
 * a vendor. Unset by default.
 */
async function fetchViaScraperProxy(url, template, timeoutMs = 90000) {
  const endpoint = template.replace('{url}', encodeURIComponent(url));
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(endpoint, { signal: controller.signal });
    const html = await res.text();
    if (!res.ok) throw new Error(`scraper proxy HTTP ${res.status}`);
    if (looksLikeChallenge(html)) throw new Error('scraper proxy returned a challenge page');
    return { html, text: '', domCandidates: [] };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Run the escalation ladder and extract a price.
 * @returns {{price:number|null, currency:string, strategy:string|null,
 *            availability:string|null, method:string|null, attempts:Array,
 *            candidates:Array}}
 */
async function fetchPrice(item, env = process.env) {
  const attempts = [];
  const methods = [
    { name: 'http', run: () => fetchViaHttp(item.url) },
    { name: 'browser', run: () => fetchViaBrowser(item.url, { priceSelector: item.priceSelector }) },
  ];

  if (env.SCRAPER_ENDPOINT) {
    methods.push({
      name: 'scraper-proxy',
      run: () => fetchViaScraperProxy(item.url, env.SCRAPER_ENDPOINT),
    });
  }

  for (const method of methods) {
    try {
      const page = await method.run();
      const result = extractPrice({
        html: page.html,
        text: page.text,
        domCandidates: page.domCandidates,
        sanity: item.sanity,
      });

      if (result.price === null) {
        attempts.push({ method: method.name, ok: false, error: 'page loaded but no price matched' });
        continue;
      }

      attempts.push({ method: method.name, ok: true });
      return Object.assign(result, { method: method.name, attempts });
    } catch (err) {
      attempts.push({ method: method.name, ok: false, error: err.message });
    }
  }

  return {
    price: null,
    currency: 'USD',
    strategy: null,
    availability: null,
    method: null,
    attempts,
    candidates: [],
  };
}

module.exports = { fetchPrice, fetchViaHttp, fetchViaBrowser, looksLikeChallenge };
