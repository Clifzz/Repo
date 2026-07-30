'use strict';

/**
 * Writes sample emails to test/preview-*.html so the layouts can be eyeballed
 * in a browser without sending anything. Usage: node test/preview.js
 */

const fs = require('fs');
const path = require('path');
const templates = require('../src/templates');
const config = require('../config.json');

const item = config.watch[0];
const threshold = config.dealThreshold;
const outDir = __dirname;

const samples = [
  ['deal', templates.dealAlert({ item, price: 54, previousPrice: 99, threshold, currency: 'USD' })],
  ['change-drop', templates.priceChange({ item, price: 89, previousPrice: 99, threshold, currency: 'USD' })],
  ['change-rise', templates.priceChange({ item, price: 109, previousPrice: 99, threshold, currency: 'USD' })],
  ['started', templates.watchStarted({ item, price: 99, threshold, currency: 'USD', strategy: 'json-ld', method: 'browser' })],
  ['failure', templates.failureAlert({ item, consecutiveFailures: 3, attempts: [{ method: 'http', ok: false, error: 'HTTP 403' }, { method: 'browser', ok: false, error: 'bot challenge not cleared' }], runUrl: 'https://github.com/Clifzz/Repo/actions' })],
];

const index = [];
for (const [name, mail] of samples) {
  const file = path.join(outDir, `preview-${name}.html`);
  fs.writeFileSync(file, `<!doctype html><meta charset="utf-8"><title>${mail.subject}</title>
<div style="padding:10px 14px;background:#22222a;color:#fff;font:13px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <strong>Subject:</strong> ${mail.subject.replace(/</g, '&lt;')}
</div>${mail.html}`);
  index.push({ name, subject: mail.subject, file: `preview-${name}.html` });
  console.log(`${name}\n  subject: ${mail.subject}\n  -> ${file}`);
}

fs.writeFileSync(
  path.join(outDir, 'preview-index.html'),
  `<!doctype html><meta charset="utf-8"><title>Email previews</title>
<body style="margin:0;font:15px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f4f4f7;">
<div style="max-width:760px;margin:0 auto;padding:28px 16px;">
<h1 style="font-size:22px;">Price watcher — email previews</h1>
<p style="color:#555;">What each notification looks like in an inbox.</p>
${index
  .map(
    (i) => `<div style="background:#fff;border-radius:10px;padding:16px;margin:0 0 12px;">
  <div style="font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#888;font-weight:700;">${i.name}</div>
  <div style="margin:6px 0 10px;font-weight:600;">${i.subject.replace(/</g, '&lt;')}</div>
  <a href="${i.file}" style="color:#2563eb;">open preview →</a>
</div>`
  )
  .join('\n')}
</div></body>`
);
console.log('\nIndex: test/preview-index.html');
