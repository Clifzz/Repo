'use strict';

/**
 * End-to-end run against a local fixture server: exercises fetch -> extract ->
 * decide -> state persistence, with email stubbed out via --dry-run.
 * Usage: node test/e2e.js
 */

const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFile } = require('child_process');
const { promisify } = require('util');

const execFileAsync = promisify(execFile);

let currentPrice = '99.00';

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
  res.end(`<!doctype html><html><head><title>Azazie Doretta</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product",
 "name":"Azazie Doretta Ink Blue Mermaid",
 "offers":{"@type":"Offer","price":"${currentPrice}","priceCurrency":"USD",
           "availability":"https://schema.org/InStock"}}
</script></head>
<body><h1>Azazie Doretta</h1><p>Free shipping on orders over $199</p></body></html>`);
});

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'pw-e2e-'));
const statePath = path.join(tmp, 'prices.json');
const configPath = path.join(tmp, 'config.json');

let port;
const assertions = [];
const check = (name, cond) => {
  assertions.push({ name, cond });
  console.log(`  ${cond ? '✓' : '✗'} ${name}`);
};

async function runCheck(label) {
  console.log(`\n─── ${label} ─────────────────────────────`);
  const env = Object.assign({}, process.env, {
    CONFIG_PATH: configPath,
    STATE_PATH: statePath,
    RECIPIENT_EMAILS: 'friend@example.com',
    OPERATOR_EMAIL: 'owner@example.com',
    SMS_RECIPIENTS: '5555550123@vtext.example',
  });
  delete env.GITHUB_STEP_SUMMARY;
  delete env.GITHUB_OUTPUT;

  try {
    const { stdout } = await execFileAsync(
      process.execPath,
      [path.join(__dirname, '..', 'src', 'index.js'), '--dry-run'],
      { env, encoding: 'utf8', timeout: 120000 }
    );
    console.log(stdout.trim());
    return { out: stdout, code: 0 };
  } catch (err) {
    const out = (err.stdout || '') + (err.stderr || '');
    console.log(out.trim());
    return { out, code: err.code === undefined ? 1 : err.code };
  }
}

// --dry-run never writes state, so persist manually between phases to simulate
// the run-to-run continuity the workflow gets from the committed state file.
function persist(price, dealAlertSentAtPrice) {
  fs.writeFileSync(
    statePath,
    JSON.stringify(
      {
        version: 1,
        items: {
          'e2e-dress': {
            label: 'E2E Dress',
            url: `http://127.0.0.1:${port}/`,
            lastPrice: price,
            currency: 'USD',
            lastCheckedOn: '2000-01-01',
            dealAlertSentAtPrice: dealAlertSentAtPrice ?? null,
            consecutiveFailures: 0,
            lastFailureNotifiedAt: null,
            history: [],
          },
        },
      },
      null,
      2
    )
  );
}

function writeConfig(url, extra) {
  fs.writeFileSync(
    configPath,
    JSON.stringify(
      Object.assign(
        {
          dealThreshold: 60,
          currency: 'USD',
          watch: [
            { id: 'e2e-dress', label: 'E2E Dress', url, priceSelector: null, sanity: { min: 10, max: 900 } },
          ],
          notifyOnPriceIncrease: true,
          historyLimit: 10,
        },
        extra || {}
      ),
      null,
      2
    )
  );
}

async function main() {
  writeConfig(`http://127.0.0.1:${port}/`);
  fs.writeFileSync(statePath, JSON.stringify({ version: 1, items: {} }, null, 2));

  let r = await runCheck('1. First check ever ($99) → baseline, operator only');
  check('read $99 via http/json-ld', /Price: \*\*\$99\*\*/.test(r.out) && /http ✓/.test(r.out));
  check('used the json-ld strategy', /json-ld/.test(r.out));
  check('ignored the $199 shipping threshold', !/\$199/.test(r.out));
  check('sent watch-started to operator', /confirmation sent to the operator/.test(r.out));
  check('friend was NOT emailed on baseline', /would email owner@example\.com/.test(r.out) && !/would email friend@example\.com/.test(r.out));

  persist(99, null);
  currentPrice = '89.00';
  r = await runCheck('2. Price drops to $89 (above target) → calm change email, no text');
  check('detected $89', /Price: \*\*\$89\*\*/.test(r.out));
  check('change email sent to friend', /Change email sent to friend@example\.com/.test(r.out));
  check('subject shows the transition', /Price dropped: \$99 → \$89/.test(r.out));
  check('did NOT text for a non-deal change', !/would text/.test(r.out));

  persist(89, null);
  r = await runCheck('3. Unchanged at $89 → silence');
  check('no email on unchanged price', /No change since last check/.test(r.out) && !/would email/.test(r.out));

  persist(89, null);
  currentPrice = '54.00';
  r = await runCheck('4. Price hits $54 (≤ $60) → EXCITED alert');
  check('deal alert fired', /DEAL ALERT SENT/.test(r.out));
  check('alert went to the friend', /would email friend@example\.com/.test(r.out));
  check('subject is loud and has the price', /GO GET IT NOW/.test(r.out) && /\$54/.test(r.out));
  check('text ALSO sent for the deal', /would text 5555550123@vtext\.example/.test(r.out));
  check('text body carries the price', /sms body.*\$54/.test(r.out));

  persist(54, 54);
  r = await runCheck('5. Still $54 → must NOT re-spam (email or text)');
  check('no repeat deal alert', !/DEAL ALERT SENT/.test(r.out) && !/would email/.test(r.out));
  check('no repeat text either', !/would text/.test(r.out));

  persist(54, 54);
  currentPrice = '39.00';
  r = await runCheck('6. Drops further to $39 → alert again');
  check('re-alerted on deeper drop', /DEAL ALERT SENT/.test(r.out) && /\$39/.test(r.out));

  persist(39, 39);
  currentPrice = '99.00';
  r = await runCheck('7. Back up to $99 → re-arm the alert');
  check('deal alert re-armed', /deal alert re-armed/.test(r.out));
  check('increase email sent', /Change email sent/.test(r.out));

  // Failure path: unreachable origin, browser fallback also unavailable here.
  writeConfig('http://127.0.0.1:1/', {
    failureAlertAfterConsecutive: 1,
    failureAlertCooldownHours: 0,
  });
  persist(99, null);
  r = await runCheck('8. Site unreachable → failure notice to operator, run goes red');
  check('could not read a price', /Could not read a price/.test(r.out));
  check('failure notice sent to operator', /failure notice to the operator/i.test(r.out));
  check('exited non-zero so GitHub flags it', r.code !== 0);

  // Real state persistence (the --dry-run path deliberately skips writing).
  process.env.STATE_PATH = statePath;
  const { loadState, saveState, getItem } = require('../src/state');
  const st = loadState();
  getItem(st, 'e2e-dress').lastPrice = 12345;
  check('saveState reports a real change', saveState(st) === true);
  check('saveState is a no-op when nothing changed', saveState(st) === false);

  const failedCount = assertions.filter((a) => !a.cond).length;
  console.log(`\n${assertions.length - failedCount} passed, ${failedCount} failed\n`);
  server.close();
  process.exit(failedCount === 0 ? 0 : 1);
}

server.listen(0, '127.0.0.1', () => {
  port = server.address().port;
  main().catch((err) => {
    console.error(err);
    server.close();
    process.exit(1);
  });
});
