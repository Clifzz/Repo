'use strict';

/**
 * Email bodies. Inline styles only and table-free layout where possible —
 * Gmail strips <style> blocks, and the deal alert has to survive that intact.
 */

const money = (n) => `$${Number(n).toFixed(Number.isInteger(Number(n)) ? 0 : 2)}`;

function shell(inner, accent) {
  return `<div style="margin:0;padding:24px 12px;background:#f4f4f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;border-top:6px solid ${accent};box-shadow:0 2px 10px rgba(0,0,0,.07);">
    ${inner}
  </div>
  <p style="max-width:560px;margin:16px auto 0;color:#8a8a94;font-size:11px;line-height:1.5;text-align:center;">
    Sent by your price watcher robot. It checks the page automatically and only emails when something actually changes.
  </p>
</div>`;
}

function button(url, label, color) {
  return `<a href="${url}" style="display:inline-block;background:${color};color:#ffffff;text-decoration:none;font-weight:700;font-size:16px;padding:14px 30px;border-radius:999px;">${label}</a>`;
}

/** The loud one: price hit the target or better. */
function dealAlert({ item, price, previousPrice, threshold, currency }) {
  const saved = previousPrice ? previousPrice - price : null;
  const pct = previousPrice && previousPrice > 0 ? Math.round((1 - price / previousPrice) * 100) : null;

  const subject = `🚨🎉 IT'S ${money(price)}!!! THE DRESS DROPPED — GO GET IT NOW 🎉🚨`;

  const html = shell(
    `<div style="background:linear-gradient(135deg,#ff2d78,#ff6a3d);padding:30px 24px;text-align:center;">
      <div style="font-size:34px;line-height:1;letter-spacing:4px;">🚨🎉🚨🎉🚨</div>
      <h1 style="margin:14px 0 6px;color:#ffffff;font-size:27px;line-height:1.2;text-transform:uppercase;letter-spacing:.5px;">
        This is not a drill
      </h1>
      <p style="margin:0;color:#ffe9f2;font-size:15px;font-weight:600;">
        The dress you've been watching just hit your price!
      </p>
    </div>

    <div style="padding:28px 24px;text-align:center;">
      <p style="margin:0 0 6px;color:#6b6b76;font-size:13px;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;">It is now</p>
      <div style="font-size:66px;font-weight:800;color:#ff2d78;line-height:1;">${money(price)}</div>
      ${
        previousPrice
          ? `<p style="margin:12px 0 0;font-size:16px;color:#444;">
               was <span style="text-decoration:line-through;color:#9a9aa4;">${money(previousPrice)}</span>
               ${saved > 0 ? `&nbsp;·&nbsp;<strong style="color:#12a150;">you save ${money(saved)}${pct ? ` (${pct}% off)` : ''}</strong>` : ''}
             </p>`
          : ''
      }
      <p style="margin:16px 0 0;font-size:15px;color:#333;line-height:1.5;">
        Your alert target was <strong>${money(threshold)} or less</strong> — and it's there. 🥳<br />
        <strong>Sizes and colors at this price can sell out fast, so grab it now!</strong>
      </p>

      <div style="margin:26px 0 10px;">${button(item.url, '🛒 GO BUY IT NOW', '#ff2d78')}</div>

      <p style="margin:18px 0 0;padding-top:16px;border-top:1px solid #eeeef2;font-size:13px;color:#77777f;line-height:1.5;">
        ${item.label}
      </p>
    </div>`,
    '#ff2d78'
  );

  const text = `🚨🎉 IT'S ${money(price)} — GO GET IT NOW! 🎉🚨

The dress you've been watching just hit your target price.

NOW: ${money(price)} ${currency}
${previousPrice ? `WAS: ${money(previousPrice)}${saved > 0 ? `  (you save ${money(saved)}${pct ? `, ${pct}% off` : ''})` : ''}\n` : ''}
Your alert target was ${money(threshold)} or less — and it's there!
Sizes at this price can sell out fast, so grab it now.

${item.label}
BUY IT HERE: ${item.url}
`;

  return { subject, html, text };
}

/** The calm one: price moved, but not into deal territory. */
function priceChange({ item, price, previousPrice, threshold, currency }) {
  const dropped = price < previousPrice;
  const delta = Math.abs(price - previousPrice);
  const pct = previousPrice > 0 ? Math.round((delta / previousPrice) * 100) : null;
  const accent = dropped ? '#12a150' : '#e08a00';
  const arrow = dropped ? '📉' : '📈';
  const word = dropped ? 'dropped' : 'went up';
  const toGo = price - threshold;

  const subject = `${arrow} Price ${word}: ${money(previousPrice)} → ${money(price)} — ${item.label}`;

  const html = shell(
    `<div style="padding:26px 24px;">
      <p style="margin:0 0 4px;color:#6b6b76;font-size:12px;text-transform:uppercase;letter-spacing:1.4px;font-weight:700;">
        ${arrow} Price ${word}
      </p>
      <h1 style="margin:0 0 18px;font-size:19px;line-height:1.35;color:#1b1b20;">${item.label}</h1>

      <div style="background:#f7f7fa;border-radius:10px;padding:18px;text-align:center;">
        <span style="font-size:22px;color:#9a9aa4;text-decoration:line-through;">${money(previousPrice)}</span>
        <span style="font-size:22px;color:#9a9aa4;padding:0 8px;">→</span>
        <span style="font-size:38px;font-weight:800;color:${accent};">${money(price)}</span>
        <p style="margin:8px 0 0;font-size:14px;color:${accent};font-weight:600;">
          ${dropped ? '−' : '+'}${money(delta)}${pct ? ` (${pct}%)` : ''}
        </p>
      </div>

      <p style="margin:18px 0 0;font-size:14px;color:#444;line-height:1.6;">
        ${
          toGo > 0
            ? `Still <strong>${money(toGo)}</strong> above the ${money(threshold)} alert price. We'll keep watching and shout the moment it gets there. 👀`
            : `That's at or under the ${money(threshold)} alert price!`
        }
      </p>

      <div style="margin:22px 0 0;text-align:center;">${button(item.url, 'View the dress', accent)}</div>
    </div>`,
    accent
  );

  const text = `${arrow} Price ${word}: ${money(previousPrice)} -> ${money(price)} ${currency}

${item.label}

${dropped ? '-' : '+'}${money(delta)}${pct ? ` (${pct}%)` : ''}
${toGo > 0 ? `Still ${money(toGo)} above the ${money(threshold)} alert price. Still watching.` : `At or under the ${money(threshold)} alert price!`}

${item.url}
`;

  return { subject, html, text };
}

/** First successful check — confirms to the operator that the plumbing works. */
function watchStarted({ item, price, threshold, currency, strategy, method }) {
  const subject = `✅ Price watch is live — ${item.label} is ${money(price)}`;
  const html = shell(
    `<div style="padding:26px 24px;">
      <h1 style="margin:0 0 10px;font-size:20px;color:#1b1b20;">✅ Watch is live</h1>
      <p style="margin:0 0 18px;font-size:14px;color:#444;line-height:1.6;">
        Baseline recorded. You'll get an email whenever this price changes, and a very loud one if it hits
        <strong>${money(threshold)} or less</strong>.
      </p>
      <div style="background:#f7f7fa;border-radius:10px;padding:18px;text-align:center;">
        <p style="margin:0 0 6px;font-size:13px;color:#6b6b76;">Current price</p>
        <div style="font-size:40px;font-weight:800;color:#1b1b20;">${money(price)}</div>
      </div>
      <p style="margin:16px 0 0;font-size:13px;color:#77777f;line-height:1.6;">
        ${item.label}<br />
        <span style="color:#9a9aa4;">Read via ${method} / ${strategy}</span>
      </p>
      <div style="margin:22px 0 0;text-align:center;">${button(item.url, 'View the dress', '#4b5563')}</div>
    </div>`,
    '#4b5563'
  );
  const text = `✅ Price watch is live.

${item.label}
Current price: ${money(price)} ${currency}
Alert target: ${money(threshold)} or less
Read via ${method} / ${strategy}

${item.url}
`;
  return { subject, html, text };
}

/** Sent to the operator only, when scraping keeps failing. */
function failureAlert({ item, consecutiveFailures, attempts, runUrl }) {
  const lines = attempts.map((a) => `  - ${a.method}: ${a.ok ? 'ok' : a.error}`).join('\n');
  const times = consecutiveFailures === 1 ? '1 check' : `${consecutiveFailures} checks`;
  const subject = `⚠️ Price watcher can't read the price (${times} in a row)`;
  const html = shell(
    `<div style="padding:26px 24px;">
      <h1 style="margin:0 0 10px;font-size:20px;color:#b42318;">⚠️ The watcher is stuck</h1>
      <p style="margin:0 0 14px;font-size:14px;color:#444;line-height:1.6;">
        It has failed to read a price <strong>${consecutiveFailures} times in a row</strong> for:<br />
        <strong>${item.label}</strong>
      </p>
      <p style="margin:0 0 8px;font-size:13px;color:#444;">What each method reported:</p>
      <pre style="background:#f7f7fa;border-radius:8px;padding:14px;font-size:12px;color:#333;white-space:pre-wrap;margin:0;">${lines}</pre>
      <p style="margin:14px 0 0;font-size:13px;color:#444;line-height:1.6;">
        Usually this means the site changed its markup, blocked the runner, or the product URL is dead.
        No alerts are going out until this is fixed.
      </p>
      ${runUrl ? `<div style="margin:20px 0 0;text-align:center;">${button(runUrl, 'Open the run log', '#b42318')}</div>` : ''}
    </div>`,
    '#b42318'
  );
  const text = `⚠️ Price watcher failed ${consecutiveFailures} checks in a row for: ${item.label}

Attempts:
${lines}

The site may have changed its markup, blocked the runner, or the URL is dead.
No alerts will go out until this is fixed.
${runUrl ? `\nRun log: ${runUrl}\n` : ''}
${item.url}
`;
  return { subject, html, text };
}

module.exports = { dealAlert, priceChange, watchStarted, failureAlert, money };
