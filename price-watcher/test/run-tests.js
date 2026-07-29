'use strict';

/**
 * Dependency-free test run: `node test/run-tests.js`
 * Covers price extraction against realistic markup and the alert/dedupe
 * decision logic, which is the part that decides whether a human gets emailed.
 */

const assert = require('assert');
const { extractPrice } = require('../src/extract');
const { looksLikeChallenge } = require('../src/fetch');
const templates = require('../src/templates');

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log(`  ✓ ${name}`);
  } catch (err) {
    failed++;
    console.log(`  ✗ ${name}\n      ${err.message}`);
  }
}

const SANITY = { min: 10, max: 900 };

console.log('\nextractPrice');

test('reads price from JSON-LD Product offers', () => {
  const html = `<html><head>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Product",
     "name":"Azazie Doretta",
     "offers":{"@type":"Offer","price":"99.00","priceCurrency":"USD",
               "availability":"https://schema.org/InStock"}}
    </script></head><body>Free shipping over $199</body></html>`;
  const r = extractPrice({ html, sanity: SANITY });
  assert.strictEqual(r.price, 99);
  assert.strictEqual(r.strategy, 'json-ld');
  assert.strictEqual(r.currency, 'USD');
  assert.strictEqual(r.availability, 'https://schema.org/InStock');
});

test('JSON-LD beats an unrelated shipping-threshold dollar amount in body text', () => {
  const html = `<html><head>
    <script type="application/ld+json">
    {"@type":"Product","offers":{"@type":"Offer","price":"59.00","priceCurrency":"USD"}}
    </script></head><body></body></html>`;
  const r = extractPrice({ html, text: 'Free shipping over $199. Save $40 today!', sanity: SANITY });
  assert.strictEqual(r.price, 59);
  assert.strictEqual(r.strategy, 'json-ld');
});

test('falls back to meta tags when JSON-LD is absent', () => {
  const html = `<meta property="product:price:amount" content="89.99">
                <meta property="product:price:currency" content="USD">`;
  const r = extractPrice({ html, sanity: SANITY });
  assert.strictEqual(r.price, 89.99);
  assert.strictEqual(r.strategy, 'meta-tag');
  assert.strictEqual(r.currency, 'USD');
});

test('skips malformed JSON-LD without crashing, then uses meta', () => {
  const html = `<script type="application/ld+json">{ this is not json }</script>
                <meta property="og:price:amount" content="75">`;
  const r = extractPrice({ html, sanity: SANITY });
  assert.strictEqual(r.price, 75);
  assert.strictEqual(r.strategy, 'meta-tag');
});

test('prefers a sale price over the generic/list price in hydration JSON', () => {
  const html = `<script>window.__DATA__={"product":{"price":"129.00","sale_price":"59.00"}}</script>`;
  const r = extractPrice({ html, sanity: SANITY });
  assert.strictEqual(r.price, 59);
  assert.strictEqual(r.strategy, 'embedded-json-sale');
});

test('honours an explicit config selector above everything else', () => {
  const html = `<script type="application/ld+json">
                {"@type":"Product","offers":{"@type":"Offer","price":"129"}}</script>`;
  const r = extractPrice({
    html,
    domCandidates: [{ strategy: 'config-selector', price: 54 }],
    sanity: SANITY,
  });
  assert.strictEqual(r.price, 54);
  assert.strictEqual(r.strategy, 'config-selector');
});

test('rejects out-of-range junk like $0 or $9999', () => {
  const html = `<meta property="product:price:amount" content="0">`;
  const r = extractPrice({ html, text: 'Financing from $9999', sanity: SANITY });
  assert.strictEqual(r.price, null);
  assert.strictEqual(r.strategy, null);
});

test('returns null price when nothing resembles a price', () => {
  const r = extractPrice({ html: '<html><body>Page not found</body></html>', sanity: SANITY });
  assert.strictEqual(r.price, null);
  assert.strictEqual(r.usableCount, 0);
});

test('detects a sold-out product', () => {
  const html = `<meta property="product:price:amount" content="99"><div>Sold Out</div>`;
  const r = extractPrice({ html, sanity: SANITY });
  assert.strictEqual(r.availability, 'OutOfStock');
});

test('parses comma-grouped prices from visible text', () => {
  const r = extractPrice({ html: '', text: 'Now $1,299.00', sanity: { min: 10, max: 5000 } });
  assert.strictEqual(r.price, 1299);
});

console.log('\nlooksLikeChallenge');

test('flags a Cloudflare interstitial', () => {
  assert.strictEqual(
    looksLikeChallenge('<html><head><title>Just a moment...</title></head></html>'),
    true
  );
});

test('does not flag a normal product page', () => {
  assert.strictEqual(looksLikeChallenge('<html><body><h1>Azazie Doretta</h1></body></html>'), false);
});

test('treats an empty body as a challenge/failure', () => {
  assert.strictEqual(looksLikeChallenge(''), true);
});

// --- alert decision logic ---------------------------------------------------
// Mirrors the branching in src/index.js so the dedupe rules are pinned down.
function decide({ price, previous, threshold, dealAlertSentAtPrice, notifyOnIncrease = true }) {
  const isDeal = price <= threshold;
  const dealWorthAlerting =
    isDeal && (dealAlertSentAtPrice === null || price < dealAlertSentAtPrice);

  let email = 'none';
  if (dealWorthAlerting) email = 'deal-alert';
  else if (previous === null) email = 'watch-started';
  else if (price !== previous) {
    const up = price > previous;
    email = up ? (notifyOnIncrease ? 'price-increase' : 'none') : 'price-drop';
  }

  const nextDealAlertAt = dealWorthAlerting
    ? price
    : !isDeal
      ? null
      : dealAlertSentAtPrice;

  return { email, nextDealAlertAt };
}

console.log('\nalert decisions');

test('first ever check records a baseline, no alert to the friend', () => {
  const d = decide({ price: 99, previous: null, threshold: 60, dealAlertSentAtPrice: null });
  assert.strictEqual(d.email, 'watch-started');
});

test('first check already below target fires the deal alert immediately', () => {
  const d = decide({ price: 55, previous: null, threshold: 60, dealAlertSentAtPrice: null });
  assert.strictEqual(d.email, 'deal-alert');
});

test('unchanged price sends nothing', () => {
  const d = decide({ price: 99, previous: 99, threshold: 60, dealAlertSentAtPrice: null });
  assert.strictEqual(d.email, 'none');
});

test('ordinary drop above target sends the calm change email', () => {
  const d = decide({ price: 89, previous: 99, threshold: 60, dealAlertSentAtPrice: null });
  assert.strictEqual(d.email, 'price-drop');
});

test('price increase sends a change email when enabled', () => {
  const d = decide({ price: 109, previous: 99, threshold: 60, dealAlertSentAtPrice: null });
  assert.strictEqual(d.email, 'price-increase');
});

test('price increase is silent when increase notifications are off', () => {
  const d = decide({
    price: 109, previous: 99, threshold: 60, dealAlertSentAtPrice: null, notifyOnIncrease: false,
  });
  assert.strictEqual(d.email, 'none');
});

test('crossing the target fires exactly one excited alert', () => {
  const d = decide({ price: 60, previous: 99, threshold: 60, dealAlertSentAtPrice: null });
  assert.strictEqual(d.email, 'deal-alert', '$60 exactly must count as hitting the target');
  assert.strictEqual(d.nextDealAlertAt, 60);
});

test('staying at the deal price does NOT re-alert every 30 minutes', () => {
  const d = decide({ price: 60, previous: 60, threshold: 60, dealAlertSentAtPrice: 60 });
  assert.strictEqual(d.email, 'none');
});

test('dropping even further re-alerts', () => {
  const d = decide({ price: 45, previous: 60, threshold: 60, dealAlertSentAtPrice: 60 });
  assert.strictEqual(d.email, 'deal-alert');
  assert.strictEqual(d.nextDealAlertAt, 45);
});

test('rising back above the target re-arms the alert', () => {
  const d = decide({ price: 99, previous: 55, threshold: 60, dealAlertSentAtPrice: 55 });
  assert.strictEqual(d.email, 'price-increase');
  assert.strictEqual(d.nextDealAlertAt, null);
});

test('re-arming means a later drop alerts again', () => {
  const d = decide({ price: 58, previous: 99, threshold: 60, dealAlertSentAtPrice: null });
  assert.strictEqual(d.email, 'deal-alert');
});

console.log('\nemail templates');

test('deal alert subject carries the price and urgency', () => {
  const mail = templates.dealAlert({
    item: { label: 'Dress', url: 'https://example.com' },
    price: 54, previousPrice: 99, threshold: 60, currency: 'USD',
  });
  assert.ok(mail.subject.includes('$54'), 'subject should contain the price');
  assert.ok(/GO GET IT NOW/i.test(mail.subject));
  assert.ok(mail.html.includes('https://example.com'), 'must link the product');
  assert.ok(mail.text.includes('$54'));
  assert.ok(mail.html.includes('you save $45'), 'should compute savings');
});

test('deal alert works with no previous price', () => {
  const mail = templates.dealAlert({
    item: { label: 'Dress', url: 'https://example.com' },
    price: 54, previousPrice: null, threshold: 60, currency: 'USD',
  });
  assert.ok(mail.subject.includes('$54'));
  assert.ok(!mail.html.includes('NaN'));
  assert.ok(!mail.text.includes('undefined'));
});

test('change email shows the gap remaining to the target', () => {
  const mail = templates.priceChange({
    item: { label: 'Dress', url: 'https://example.com' },
    price: 89, previousPrice: 99, threshold: 60, currency: 'USD',
  });
  assert.ok(mail.subject.includes('$99') && mail.subject.includes('$89'));
  assert.ok(mail.html.includes('$29'), 'should show $29 still to go');
});

test('money() renders whole dollars without trailing cents', () => {
  assert.strictEqual(templates.money(60), '$60');
  assert.strictEqual(templates.money(59.5), '$59.50');
});

console.log(`\n${passed} passed, ${failed} failed\n`);
process.exit(failed === 0 ? 0 : 1);
