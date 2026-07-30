'use strict';

const fs = require('fs');
const path = require('path');

const { fetchPrice } = require('./fetch');
const { sendMail, sendSms, verifyTransport, parseRecipients } = require('./mailer');
const { loadState, saveState, getItem, recordHistory } = require('./state');
const templates = require('./templates');

const CONFIG_PATH = process.env.CONFIG_PATH || path.join(__dirname, '..', 'config.json');
const argv = process.argv.slice(2);
const DRY_RUN = argv.includes('--dry-run');
const TEST_EMAIL = argv.includes('--test-email');

const summaryLines = [];
function say(line) {
  console.log(line);
  summaryLines.push(line);
}

function writeStepSummary() {
  const file = process.env.GITHUB_STEP_SUMMARY;
  if (!file) return;
  try {
    fs.appendFileSync(file, `${summaryLines.join('\n')}\n`);
  } catch {
    /* summary is a nicety, never fail the run over it */
  }
}

function setOutput(key, value) {
  const file = process.env.GITHUB_OUTPUT;
  if (!file) return;
  try {
    fs.appendFileSync(file, `${key}=${value}\n`);
  } catch {
    /* ignore */
  }
}

function runUrl() {
  const { GITHUB_SERVER_URL, GITHUB_REPOSITORY, GITHUB_RUN_ID } = process.env;
  if (!GITHUB_SERVER_URL || !GITHUB_REPOSITORY || !GITHUB_RUN_ID) return null;
  return `${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}`;
}

function hoursSince(iso) {
  if (!iso) return Infinity;
  return (Date.now() - new Date(iso).getTime()) / 36e5;
}

async function testEmail(config, recipients, operatorRecipients, smsRecipients) {
  const item = config.watch[0];
  const user = await verifyTransport();
  say(`SMTP connection OK as ${user}`);

  // Test mail goes to the operator *and* the real recipients: the point is to
  // prove delivery end to end, and an address that silently spam-filters the
  // alert is exactly what this run needs to catch. Deduped case-insensitively
  // so nobody gets two copies when the operator is also a recipient.
  const seen = new Set();
  const testTarget = [...operatorRecipients, ...recipients].filter((addr) => {
    const key = addr.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  const mail = templates.watchStarted({
    item,
    price: 99,
    threshold: config.dealThreshold,
    currency: config.currency,
    strategy: 'test',
    method: 'test',
  });
  await sendMail({
    to: testTarget,
    subject: `[TEST] ${mail.subject}`,
    html: mail.html,
    text: mail.text,
    dryRun: DRY_RUN,
  });
  say(`Test email sent to ${testTarget.join(', ')}`);

  // Gateway delivery is the least predictable part of the setup, so prove it
  // works before relying on it for the real alert.
  if (smsRecipients.length > 0) {
    const sms = templates.smsDeal({
      item,
      price: 54,
      previousPrice: 99,
      threshold: config.dealThreshold,
    });
    await sendSms({
      to: smsRecipients,
      subject: sms.subject,
      text: `[TEST] ${sms.text}`,
      dryRun: DRY_RUN,
    });
    say(`Test text sent to ${smsRecipients.length} number(s). If it doesn't arrive within`);
    say('a few minutes, the carrier gateway is wrong or is filtering it — see the README.');
  } else {
    say('No SMS_RECIPIENTS set, so no test text was sent.');
  }
}

/**
 * A text interrupts someone; an email waits. Default is deal-only so the
 * phone buzzes for the thing that actually matters.
 */
function smsWanted(eventType, config) {
  const mode = (config.sms && config.sms.notifyOn) || 'deal';
  if (mode === 'none') return false;
  if (mode === 'all') return ['deal-alert', 'price-drop', 'price-increase'].includes(eventType);
  return eventType === 'deal-alert';
}

async function processItem(item, config, state, recipients, operatorRecipients, smsRecipients) {
  const stored = getItem(state, item.id);
  stored.label = item.label;
  stored.url = item.url;

  const today = new Date().toISOString().slice(0, 10);
  const threshold = config.dealThreshold;

  say(`\n### ${item.label}`);

  const result = await fetchPrice(item);
  const attemptLog = result.attempts
    .map((a) => `${a.method}${a.ok ? ' ✓' : ` ✗ (${a.error})`}`)
    .join(' → ');
  say(`- Fetch: ${attemptLog}`);

  // ---- failure path -------------------------------------------------------
  if (result.price === null) {
    stored.consecutiveFailures += 1;
    stored.lastCheckedOn = today;
    say(`- **Could not read a price** (failure #${stored.consecutiveFailures})`);

    const threshHit = stored.consecutiveFailures >= (config.failureAlertAfterConsecutive || 3);
    const cooledDown =
      hoursSince(stored.lastFailureNotifiedAt) >= (config.failureAlertCooldownHours || 12);

    if (threshHit && cooledDown && operatorRecipients.length > 0) {
      const mail = templates.failureAlert({
        item,
        consecutiveFailures: stored.consecutiveFailures,
        attempts: result.attempts,
        runUrl: runUrl(),
      });
      try {
        await sendMail({ to: operatorRecipients, ...mail, dryRun: DRY_RUN });
        stored.lastFailureNotifiedAt = new Date().toISOString();
        say('- Sent failure notice to the operator.');
      } catch (err) {
        say(`- Failure notice could NOT be emailed: ${err.message}`);
      }
    }
    return { ok: false, failedHard: threshHit };
  }

  // ---- success path -------------------------------------------------------
  const price = result.price;
  const previous = stored.lastPrice;

  stored.consecutiveFailures = 0;
  stored.lastCheckedOn = today;
  stored.currency = result.currency || config.currency;
  stored.availability = result.availability;

  say(`- Price: **${templates.money(price)}** (via ${result.method} / ${result.strategy})`);
  if (result.availability) say(`- Availability: ${result.availability}`);
  say(`- Previous: ${previous === null ? '(none — first check)' : templates.money(previous)}`);

  const isDeal = price <= threshold;
  const changed = previous !== null && price !== previous;
  let emailSent = 'none';

  // Alert once when we cross into deal territory, and again only if it drops
  // further — otherwise every check for the rest of the sale would re-alert.
  const alreadyAlerted = stored.dealAlertSentAtPrice;
  const dealWorthAlerting = isDeal && (alreadyAlerted === null || price < alreadyAlerted);

  if (dealWorthAlerting) {
    const mail = templates.dealAlert({
      item,
      price,
      previousPrice: previous,
      threshold,
      currency: stored.currency,
    });
    await sendMail({ to: recipients, ...mail, dryRun: DRY_RUN });
    stored.dealAlertSentAtPrice = price;
    emailSent = 'deal-alert';
    say(`- 🚨 **DEAL ALERT SENT** to ${recipients.join(', ')}`);

    if (smsRecipients.length > 0 && smsWanted('deal-alert', config)) {
      const sms = templates.smsDeal({ item, price, previousPrice: previous, threshold });
      await sendSms({ to: smsRecipients, ...sms, dryRun: DRY_RUN });
      say(`- 📱 Text sent to ${smsRecipients.length} number(s)`);
    }
  } else if (previous === null) {
    if (operatorRecipients.length > 0) {
      const mail = templates.watchStarted({
        item,
        price,
        threshold,
        currency: stored.currency,
        strategy: result.strategy,
        method: result.method,
      });
      await sendMail({ to: operatorRecipients, ...mail, dryRun: DRY_RUN });
      emailSent = 'watch-started';
      say('- Baseline recorded; confirmation sent to the operator.');
    } else {
      say('- Baseline recorded (no operator address set, so no confirmation email).');
    }
  } else if (changed) {
    const isIncrease = price > previous;
    if (isIncrease && config.notifyOnPriceIncrease === false) {
      say('- Price rose, but increase notifications are disabled.');
    } else {
      const mail = templates.priceChange({
        item,
        price,
        previousPrice: previous,
        threshold,
        currency: stored.currency,
      });
      await sendMail({ to: recipients, ...mail, dryRun: DRY_RUN });
      emailSent = isIncrease ? 'price-increase' : 'price-drop';
      say(`- 📧 Change email sent to ${recipients.join(', ')}`);

      if (smsRecipients.length > 0 && smsWanted(emailSent, config)) {
        const sms = templates.smsChange({ item, price, previousPrice: previous, threshold });
        await sendSms({ to: smsRecipients, ...sms, dryRun: DRY_RUN });
        say(`- 📱 Text sent to ${smsRecipients.length} number(s)`);
      }
    }
  } else {
    say('- No change since last check; no email sent.');
  }

  // Leaving deal territory re-arms the alert for the next time it drops.
  if (!isDeal && stored.dealAlertSentAtPrice !== null) {
    stored.dealAlertSentAtPrice = null;
    say('- Price is back above the target; deal alert re-armed.');
  }

  if (previous === null || price !== previous) {
    stored.lastChangedAt = new Date().toISOString();
    recordHistory(stored, price, config.historyLimit);
  }
  stored.lastPrice = price;

  setOutput('price', String(price));
  setOutput('email_sent', emailSent);
  return { ok: true, price, emailSent };
}

async function main() {
  const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));

  const recipients = parseRecipients(process.env.RECIPIENT_EMAILS);
  const operatorRecipients = parseRecipients(
    process.env.OPERATOR_EMAIL || process.env.SMTP_USER || process.env.GMAIL_USER
  );
  const smsRecipients = parseRecipients(process.env.SMS_RECIPIENTS);

  if (recipients.length === 0) {
    throw new Error(
      'RECIPIENT_EMAILS is empty. Set it as a repository secret (comma-separated addresses).'
    );
  }

  say(`## Price watch — ${new Date().toUTCString()}`);
  say(`- Alert target: **${templates.money(config.dealThreshold)} or less**`);
  say(`- Alerts go to: ${recipients.join(', ')}`);
  if (smsRecipients.length > 0) {
    const mode = (config.sms && config.sms.notifyOn) || 'deal';
    say(`- Texts go to: ${smsRecipients.length} number(s) (mode: ${mode})`);
  }
  if (DRY_RUN) say('- **DRY RUN** — no email will actually be sent.');

  if (TEST_EMAIL) {
    await testEmail(config, recipients, operatorRecipients, smsRecipients);
    writeStepSummary();
    return;
  }

  const state = loadState();
  let hardFailure = false;

  for (const item of config.watch) {
    try {
      const res = await processItem(
        item,
        config,
        state,
        recipients,
        operatorRecipients,
        smsRecipients
      );
      if (res.failedHard) hardFailure = true;
    } catch (err) {
      hardFailure = true;
      say(`- **Unhandled error for ${item.label}:** ${err.message}`);
      console.error(err);
    }
  }

  const wrote = DRY_RUN ? false : saveState(state);
  setOutput('state_changed', wrote ? 'true' : 'false');
  say(`\n_State file ${wrote ? 'updated' : 'unchanged'}._`);

  writeStepSummary();

  // Surface a persistent problem as a red run so GitHub notifies the owner
  // even if email delivery is the thing that's broken.
  if (hardFailure) process.exit(1);
}

main().catch((err) => {
  say(`\n**Fatal:** ${err.message}`);
  writeStepSummary();
  console.error(err);
  process.exit(1);
});
