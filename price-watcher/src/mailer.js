'use strict';

const nodemailer = require('nodemailer');

/**
 * SMTP delivery. Defaults to Gmail, but any SMTP host works via SMTP_HOST /
 * SMTP_PORT so the account can be swapped without touching code.
 */

function buildTransport(env = process.env) {
  const user = env.SMTP_USER || env.GMAIL_USER;
  const pass = env.SMTP_PASSWORD || env.GMAIL_APP_PASSWORD;

  if (!user || !pass) {
    throw new Error(
      'Missing SMTP credentials. Set repository secrets GMAIL_USER and GMAIL_APP_PASSWORD ' +
        '(or SMTP_USER / SMTP_PASSWORD).'
    );
  }

  const host = env.SMTP_HOST || 'smtp.gmail.com';
  const port = Number(env.SMTP_PORT || 465);

  const transport = nodemailer.createTransport({
    host,
    port,
    secure: port === 465,
    auth: { user, pass },
  });

  return { transport, user };
}

function parseRecipients(raw) {
  return String(raw || '')
    .split(/[,;\s]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

async function sendMail({ to, subject, html, text, env = process.env, dryRun = false }) {
  const recipients = Array.isArray(to) ? to : parseRecipients(to);
  if (recipients.length === 0) throw new Error('No recipients configured.');

  if (dryRun) {
    console.log(`[dry-run] would email ${recipients.join(', ')}`);
    console.log(`[dry-run] subject: ${subject}`);
    return { dryRun: true, accepted: recipients };
  }

  const { transport, user } = buildTransport(env);
  const fromName = env.MAIL_FROM_NAME || 'Dress Price Watcher';

  const info = await transport.sendMail({
    from: `"${fromName}" <${user}>`,
    to: recipients.join(', '),
    subject,
    text,
    html,
  });

  console.log(`Email sent to ${recipients.join(', ')} (id ${info.messageId})`);
  return info;
}

/**
 * Text-only delivery for carrier email-to-SMS gateways.
 *
 * Gateways reject or mangle multipart/HTML mail, so this sends a bare
 * text/plain body. A gateway rejecting one number must not take down the
 * email alerts, so failures are logged and swallowed rather than thrown.
 */
async function sendSms({ to, text, subject = '', env = process.env, dryRun = false }) {
  const recipients = Array.isArray(to) ? to : parseRecipients(to);
  if (recipients.length === 0) return { skipped: true };

  if (dryRun) {
    console.log(`[dry-run] would text ${recipients.join(', ')}`);
    console.log(`[dry-run] sms body (${text.length} chars): ${text}`);
    return { dryRun: true, accepted: recipients };
  }

  try {
    const { transport, user } = buildTransport(env);
    const info = await transport.sendMail({
      from: user, // bare address: gateways choke on display-name formatting
      to: recipients.join(', '),
      subject,
      text,
    });
    console.log(`SMS sent via gateway to ${recipients.join(', ')} (id ${info.messageId})`);
    return info;
  } catch (err) {
    console.error(`SMS delivery failed (email alerts unaffected): ${err.message}`);
    return { error: err.message };
  }
}

async function verifyTransport(env = process.env) {
  const { transport, user } = buildTransport(env);
  await transport.verify();
  return user;
}

module.exports = { sendMail, sendSms, verifyTransport, parseRecipients };
