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

test('reports OutOfStock from structured availability data', () => {
  const html = `<meta property="product:price:amount" content="99">
    <script type="application/ld+json">
    {"@type":"Product","offers":{"@type":"Offer","price":"99",
     "availability":"https://schema.org/OutOfStock"}}</script>`;
  const r = extractPrice({ html, sanity: SANITY });
  assert.strictEqual(r.availability, 'https://schema.org/OutOfStock');
});

test('a sold-out SIZE does not mark the whole product unavailable', () => {
  // Size pickers routinely label individual variants "Sold Out"; treating that
  // as product-level stock status produced a false OutOfStock on the real page.
  const html = `<meta property="product:price:amount" content="99">
    <select><option>A0</option><option>A2 - Sold Out</option></select>`;
  const r = extractPrice({ html, sanity: SANITY });
  assert.strictEqual(r.availability, null);
  assert.strictEqual(r.price, 99, 'price must still be read normally');
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

console.log('\nSMS templates');

const SMS_ITEM = {
  label: 'Azazie Doretta',
  url: 'https://www.azazie.com/products/azazie-doretta-ink-blue-mermaid-pleated-stretch-satin-floor-length-bridesmaid-dress/36463173?size=bd_a0&from_color_filter=1',
  shortUrl: null,
};

test('deal text leads with the price and includes a link', () => {
  const sms = templates.smsDeal({ item: SMS_ITEM, price: 54, previousPrice: 99, threshold: 60 });
  assert.ok(sms.text.includes('$54'));
  assert.ok(sms.text.includes('$99'));
  assert.ok(sms.text.includes('PRICE DROP'));
  assert.ok(sms.text.includes('azazie.com'));
});

test('SMS bodies are plain ASCII (no emoji/HTML for gateways)', () => {
  for (const sms of [
    templates.smsDeal({ item: SMS_ITEM, price: 54, previousPrice: 99, threshold: 60 }),
    templates.smsChange({ item: SMS_ITEM, price: 89, previousPrice: 99, threshold: 60 }),
  ]) {
    // eslint-disable-next-line no-control-regex
    assert.ok(/^[\x00-\x7F]*$/.test(sms.text), `non-ASCII in: ${sms.text}`);
    assert.ok(!/<[a-z]/i.test(sms.text), 'must not contain HTML');
  }
});

test('the message stays short once a shortUrl is supplied', () => {
  const item = Object.assign({}, SMS_ITEM, { shortUrl: 'https://bit.ly/abcd123' });
  const sms = templates.smsDeal({ item, price: 54, previousPrice: 99, threshold: 60 });
  assert.ok(sms.text.length <= 160, `expected <=160 chars, got ${sms.text.length}`);
  assert.ok(sms.text.includes('bit.ly/abcd123'));
});

test('the informative part precedes the link, so truncation keeps the news', () => {
  const sms = templates.smsDeal({ item: SMS_ITEM, price: 54, previousPrice: 99, threshold: 60 });
  assert.ok(sms.text.indexOf('$54') < sms.text.indexOf('http'));
  assert.ok(sms.text.indexOf('$54') < 60, 'price must survive a 160-char cut');
});

test('deal text handles a missing previous price', () => {
  const sms = templates.smsDeal({ item: SMS_ITEM, price: 54, previousPrice: null, threshold: 60 });
  assert.ok(!sms.text.includes('undefined') && !sms.text.includes('NaN'));
  assert.ok(sms.text.includes('$54'));
});

test('change text states the remaining gap to the target', () => {
  const sms = templates.smsChange({ item: SMS_ITEM, price: 89, previousPrice: 99, threshold: 60 });
  assert.ok(sms.text.includes('down'));
  assert.ok(sms.text.includes('$29'), 'should show the $29 gap');
});

test('change text omits the gap once at or below target', () => {
  const sms = templates.smsChange({ item: SMS_ITEM, price: 55, previousPrice: 99, threshold: 60 });
  assert.ok(!/over your/.test(sms.text));
});

test('SMS subject is empty so gateways do not prepend noise', () => {
  assert.strictEqual(
    templates.smsDeal({ item: SMS_ITEM, price: 54, previousPrice: 99, threshold: 60 }).subject,
    ''
  );
});

console.log('\nSMS routing rules');

function smsWanted(eventType, config) {
  const mode = (config.sms && config.sms.notifyOn) || 'deal';
  if (mode === 'none') return false;
  if (mode === 'all') return ['deal-alert', 'price-drop', 'price-increase'].includes(eventType);
  return eventType === 'deal-alert';
}

test('default mode texts only for the deal alert', () => {
  const cfg = { sms: { notifyOn: 'deal' } };
  assert.strictEqual(smsWanted('deal-alert', cfg), true);
  assert.strictEqual(smsWanted('price-drop', cfg), false);
  assert.strictEqual(smsWanted('price-increase', cfg), false);
});

test('"all" mode texts on any price movement', () => {
  const cfg = { sms: { notifyOn: 'all' } };
  assert.strictEqual(smsWanted('deal-alert', cfg), true);
  assert.strictEqual(smsWanted('price-drop', cfg), true);
});

test('"none" mode never texts', () => {
  const cfg = { sms: { notifyOn: 'none' } };
  assert.strictEqual(smsWanted('deal-alert', cfg), false);
});

test('missing sms config falls back to deal-only', () => {
  assert.strictEqual(smsWanted('deal-alert', {}), true);
  assert.strictEqual(smsWanted('price-drop', {}), false);
});

test('never texts for operator-only events', () => {
  for (const mode of ['deal', 'all', 'none']) {
    const cfg = { sms: { notifyOn: mode } };
    assert.strictEqual(smsWanted('watch-started', cfg), false);
    assert.strictEqual(smsWanted('none', cfg), false);
  }
});

console.log(`\n${passed} passed, ${failed} failed\n`);
process.exit(failed === 0 ? 0 : 1);
