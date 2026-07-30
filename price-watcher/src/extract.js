'use strict';

/**
 * Price extraction.
 *
 * Retail markup changes without warning, so we never rely on a single CSS
 * selector. We run several independent strategies over the page, keep every
 * candidate, and pick the one from the most trustworthy source that also
 * passes a sanity range. The winning strategy name is reported so a wrong
 * number is diagnosable from the email/run summary instead of silently
 * becoming "the price".
 */

const STRATEGY_RANK = [
  'config-selector', // explicit human override always wins
  'json-ld',
  'meta-tag',
  'microdata',
  'embedded-json-sale',
  'embedded-json-generic',
  'dom-price-class',
  'text-scan',
];

function toNumber(raw) {
  if (raw === null || raw === undefined) return null;
  const cleaned = String(raw).replace(/[^0-9.]/g, '');
  if (!cleaned || (cleaned.match(/\./g) || []).length > 1) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

function inRange(price, sanity) {
  if (price === null) return false;
  const min = sanity && typeof sanity.min === 'number' ? sanity.min : 0;
  const max = sanity && typeof sanity.max === 'number' ? sanity.max : Infinity;
  return price >= min && price <= max;
}

function push(candidates, strategy, price, extra) {
  const n = toNumber(price);
  if (n === null || n <= 0) return;
  candidates.push(Object.assign({ strategy, price: n }, extra || {}));
}

/** Walk arbitrarily nested JSON looking for schema.org Product/Offer nodes. */
function walkJsonLd(node, out, depth = 0) {
  if (!node || typeof node !== 'object' || depth > 12) return;
  if (Array.isArray(node)) {
    for (const child of node) walkJsonLd(child, out, depth + 1);
    return;
  }

  const types = []
    .concat(node['@type'] || [])
    .map((t) => String(t).toLowerCase());

  if (types.includes('offer') || types.includes('aggregateoffer')) {
    out.push({
      price: node.price ?? node.lowPrice ?? node.highPrice ?? null,
      currency: node.priceCurrency || null,
      availability: node.availability || null,
    });
  }

  if (types.includes('product') && node.offers) {
    walkJsonLd(node.offers, out, depth + 1);
  }

  for (const key of Object.keys(node)) {
    if (key === '@type') continue;
    walkJsonLd(node[key], out, depth + 1);
  }
}

function fromJsonLd(html, candidates) {
  const re = /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    let parsed;
    try {
      parsed = JSON.parse(m[1].trim());
    } catch {
      continue; // malformed blocks are common; ignore and keep going
    }
    const offers = [];
    walkJsonLd(parsed, offers);
    for (const offer of offers) {
      push(candidates, 'json-ld', offer.price, {
        currency: offer.currency,
        availability: offer.availability,
      });
    }
  }
}

function fromMetaTags(html, candidates) {
  const props = [
    'product:price:amount',
    'og:price:amount',
    'twitter:data1',
  ];
  for (const prop of props) {
    const re = new RegExp(
      `<meta[^>]+(?:property|name)=["']${prop}["'][^>]+content=["']([^"']+)["']`,
      'i'
    );
    const m = html.match(re);
    if (m) push(candidates, 'meta-tag', m[1], { source: prop });
  }

  const currency = html.match(
    /<meta[^>]+(?:property|name)=["'](?:product:price:currency|og:price:currency)["'][^>]+content=["']([^"']+)["']/i
  );
  if (currency) {
    for (const c of candidates) {
      if (c.strategy === 'meta-tag' && !c.currency) c.currency = currency[1];
    }
  }
}

function fromMicrodata(html, candidates) {
  const re = /itemprop=["']price["'][^>]*content=["']([^"']+)["']/gi;
  let m;
  while ((m = re.exec(html)) !== null) push(candidates, 'microdata', m[1]);
}

/**
 * Single-page apps hydrate from a JSON blob in the HTML. Sale-ish keys are
 * ranked above the generic `price` key, which on many storefronts still holds
 * the pre-discount list price.
 */
function fromEmbeddedJson(html, candidates) {
  const saleKeys =
    'sale_price|salePrice|final_price|finalPrice|current_price|currentPrice|discount_price|discountPrice|now_price|nowPrice|special_price|specialPrice';
  const genericKeys =
    'price|product_price|productPrice|min_price|minPrice|lowest_price|lowestPrice|list_price|listPrice|original_price|originalPrice';

  const scan = (keys, strategy) => {
    const re = new RegExp(
      `["'](${keys})["']\\s*:\\s*["']?\\$?\\s*([0-9]+(?:\\.[0-9]{1,2})?)["']?`,
      'gi'
    );
    let m;
    const seen = new Set();
    while ((m = re.exec(html)) !== null) {
      const key = m[1];
      const val = m[2];
      const dedupe = `${key}:${val}`;
      if (seen.has(dedupe)) continue;
      seen.add(dedupe);
      push(candidates, strategy, val, { source: key });
    }
  };

  scan(saleKeys, 'embedded-json-sale');
  scan(genericKeys, 'embedded-json-generic');
}

function fromTextScan(text, candidates) {
  const re = /(?:US)?\$\s*([0-9]{1,4}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)/g;
  let m;
  const seen = new Set();
  while ((m = re.exec(text)) !== null) {
    if (seen.has(m[1])) continue;
    seen.add(m[1]);
    push(candidates, 'text-scan', m[1]);
  }
}

function detectAvailability(html) {
  const lower = html.toLowerCase();
  if (/"availability"\s*:\s*"[^"]*outofstock/i.test(html)) return 'OutOfStock';
  if (/"availability"\s*:\s*"[^"]*instock/i.test(html)) return 'InStock';
  if (/\bsold\s*out\b/.test(lower)) return 'OutOfStock';
  return null;
}

/**
 * @param {object} input
 * @param {string} input.html      Raw or rendered HTML.
 * @param {string} [input.text]    Visible page text, when a browser rendered it.
 * @param {Array}  [input.domCandidates] Candidates already harvested from a live DOM.
 * @param {object} [input.sanity]  { min, max } plausible price window.
 * @returns {{price:number|null, currency:string, strategy:string|null, availability:string|null, candidates:Array}}
 */
function extractPrice(input) {
  const { html = '', text = '', domCandidates = [], sanity } = input;
  const candidates = [...domCandidates];

  fromJsonLd(html, candidates);
  fromMetaTags(html, candidates);
  fromMicrodata(html, candidates);
  fromEmbeddedJson(html, candidates);
  if (text) fromTextScan(text, candidates);

  const usable = candidates.filter((c) => inRange(c.price, sanity));

  usable.sort((a, b) => {
    const ra = STRATEGY_RANK.indexOf(a.strategy);
    const rb = STRATEGY_RANK.indexOf(b.strategy);
    if (ra !== rb) return (ra < 0 ? 99 : ra) - (rb < 0 ? 99 : rb);
    // Within one strategy the shopper pays the lowest advertised number.
    return a.price - b.price;
  });

  const winner = usable[0] || null;

  return {
    price: winner ? winner.price : null,
    currency: (winner && winner.currency) || 'USD',
    strategy: winner ? winner.strategy : null,
    availability: (winner && winner.availability) || detectAvailability(html),
    candidates,
    usableCount: usable.length,
  };
}

module.exports = { extractPrice, toNumber, STRATEGY_RANK };
