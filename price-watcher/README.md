# 👗 Dress Price Watcher

Watches a product page in the cloud and emails when the price moves — with a
deliberately loud alert when it hits the target price.

Runs on **GitHub Actions**, so there is nothing to host and nothing to keep
running on your laptop. This repo is public, so the Actions minutes are free.

**Currently watching:** Azazie Doretta — Ink Blue Mermaid Pleated Stretch Satin
**Alert target:** **$60 or less**
**Checks:** every 30 minutes

---

## ⚡ Setup — 5 minutes, and it will not work until you do this

The code is deployed already. It just needs an email account to send from.

### Step 1 — Make a Gmail App Password

An App Password is a 16-character key that lets a script send mail as you,
without giving it your real password. Use whichever Gmail account should
*send* the alerts (it does not have to be Sarah's).

1. That account needs 2-Step Verification on: https://myaccount.google.com/security
2. Go to https://myaccount.google.com/apppasswords
3. Type any name (e.g. `Price Watcher`) → **Create**
4. Copy the 16-character code. Spaces don't matter.

> No "App passwords" option? 2-Step Verification isn't fully enabled yet, or
> it's a Workspace/school account where an admin has disabled them.

### Step 2 — Add 3 repository secrets

Go to **[Settings → Secrets and variables → Actions](../../settings/secrets/actions)**
→ *New repository secret*, and add these three:

| Secret name | Value |
|---|---|
| `GMAIL_USER` | the Gmail address that sends, e.g. `you@gmail.com` |
| `GMAIL_APP_PASSWORD` | the 16-character App Password from Step 1 |
| `RECIPIENT_EMAILS` | the address to alert, e.g. `friend@gmail.com` |

Optional extras:

| Secret name | Value |
|---|---|
| `OPERATOR_EMAIL` | where *setup confirmations and breakage warnings* go. Defaults to `GMAIL_USER`. Set this to your own address so the recipient only ever gets price news. |
| `SMS_RECIPIENTS` | carrier email-to-SMS gateway address(es) — see [Text alerts](#-text-alerts-optional) |
| `SMTP_HOST` / `SMTP_PORT` | to use a provider other than Gmail |
| `SCRAPER_ENDPOINT` | fallback rendering proxy — see [If it gets blocked](#if-it-gets-blocked) |

> To alert more than one person, put several addresses in `RECIPIENT_EMAILS`
> separated by commas.

> ⚠️ **Keep personal contact details in secrets, never in `config.json` or this
> README.** This repository is public — anything committed here is world-readable
> and gets scraped. Secrets are encrypted and never appear in logs.

### Step 3 — Test it

Go to **[Actions → Dress price watch](../../actions/workflows/price-watch.yml)**
→ *Run workflow*, tick **test_email**, and run it. You should get a test email
within a minute. If it arrives, everything is wired up.

Then run it once more with **dry_run** ticked — that does a real price check
and prints what it found without emailing anyone. The run summary shows the
price and which method read it.

That's it. From then on it runs itself every 30 minutes.

---

## What each email looks like

| When | Who gets it | Subject | Text too? |
|---|---|---|---|
| Price hits **$60 or less** | recipients | 🚨🎉 IT'S $54!!! THE DRESS DROPPED — GO GET IT NOW 🎉🚨 | ✅ yes |
| Any other price change | recipients | 📉 Price dropped: $99 → $89 — *(item)* | — |
| First successful check | operator only | ✅ Price watch is live — … is $99 | — |
| Broken for 3 checks running | operator only | ⚠️ Price watcher can't read the price | — |

Preview them in a browser without sending anything:

```bash
cd price-watcher && node test/preview.js && open test/preview-index.html
```

### It will not spam anyone

- Price unchanged → **no email at all**.
- Price sitting at $54 for a week → **one** alert, not 336 of them.
- Price drops *further* ($54 → $39) → alerts again, because that's news.
- Price goes back above $60 → the alert re-arms, so the next drop alerts again.

---

## 📱 Text alerts (optional)

A text can be sent alongside the email at no cost, using the recipient's
carrier email-to-SMS gateway. No Twilio account, no phone number to rent —
the same Gmail account sends it.

**Setup:** add an `SMS_RECIPIENTS` secret containing the 10-digit number
@-joined to the carrier's gateway domain, e.g. `5551234567@vtext.com`.
Multiple numbers can be comma-separated.

| Carrier | Gateway address |
|---|---|
| Verizon (also Visible, Xfinity Mobile) | `5551234567@vtext.com` |
| T-Mobile (also Mint, Ultra) | `5551234567@tmomail.net` |
| AT&T (also Cricket via `sms.cricketwireless.net`) | `5551234567@txt.att.net` |
| Google Fi | `5551234567@msg.fi.google.com` |
| US Cellular | `5551234567@email.uscc.net` |
| Metro by T-Mobile | `5551234567@mymetropcs.com` |
| Boost | `5551234567@sms.myboostmobile.com` |

Not sure of the carrier? [freecarrierlookup.com](https://freecarrierlookup.com)
will tell you from the number. If the number was ported between carriers, the
area code proves nothing — look it up.

**By default only the $60 deal alert sends a text.** Routine price changes stay
email-only, because a text interrupts and an email waits. Change
`sms.notifyOn` in `config.json` to `"all"` or `"none"` to adjust.

Test it with the `test_email` workflow run — it sends a sample text too, so you
can confirm the gateway works before relying on it.

> ### ⚠️ Honest caveat about gateway texts
>
> These gateways are free and unofficial, and carriers have been tightening
> spam filtering on them for years — some have deprecated them outright.
> Delivery is **usually** fine but is not guaranteed or supported by anyone.
>
> Treat the text as a bonus on top of the email, not a replacement. The email
> is the reliable channel. If texts prove flaky and it matters, the upgrade is
> Twilio (~$1/month for a number plus well under a cent per message) — though
> sending to US numbers now also requires A2P 10DLC brand registration, which
> takes a few days to get approved.

**Message length:** the Azazie product URL is ~150 characters on its own, so the
text arrives as two joined segments. Phones stitch these together seamlessly. To
get it under the 160-character single-segment limit, put a shortened link in
`shortUrl` in `config.json` — the text uses it automatically when set.

---

## Changing what's watched

Everything tweakable lives in [`config.json`](config.json) — no code changes:

```jsonc
{
  "dealThreshold": 60,          // the "get excited" price
  "watch": [
    {
      "id": "azazie-doretta-ink-blue",
      "label": "Azazie Doretta — Ink Blue Mermaid…",
      "url": "https://www.azazie.com/products/…",
      "priceSelector": null,     // optional CSS override if auto-detection is wrong
      "sanity": { "min": 10, "max": 900 }  // ignore absurd numbers
    }
  ],
  "notifyOnPriceIncrease": true // false = only tell us about drops
}
```

Add more products by adding entries to `watch` — each needs a unique `id`.

To check more or less often, edit the `cron:` line in
[`.github/workflows/price-watch.yml`](../.github/workflows/price-watch.yml).
Note GitHub's scheduler is best-effort and can run several minutes late; it is
not built for to-the-minute precision.

---

## How it reads the price

`azazie.com` is behind Cloudflare bot protection, which serves a "Just a
moment…" challenge instead of the page to ordinary scripts. So the watcher
escalates until something works:

1. **Plain HTTP request** — instant and free when the site allows it.
2. **Real headless Chromium** (Playwright) — executes the challenge JavaScript.
3. **A rendering proxy** — only if you set `SCRAPER_ENDPOINT`.

Whichever page it gets, it then tries several extraction strategies in order of
trustworthiness — structured `JSON-LD` product data, `<meta>` price tags,
microdata, the site's embedded hydration JSON, live DOM elements, and finally a
plain text scan — and takes the most trustworthy number that falls inside the
`sanity` range. That range is what stops it from reporting "$199" off a *free
shipping over $199* banner.

The run summary always names the method and strategy that won (`via browser /
json-ld`), so if a number ever looks wrong you can see exactly where it came
from.

### If it gets blocked

If Cloudflare starts refusing the GitHub runner, you'll get the ⚠️ breakage
email rather than silence. The fix is to add a rendering proxy: sign up for any
scraping API (ScraperAPI, ScrapingBee, ZenRows — all have free tiers) and set
the `SCRAPER_ENDPOINT` secret to their URL template with `{url}` where the
target goes, e.g.

```
https://api.scraperapi.com/?api_key=YOURKEY&render=true&url={url}
```

No code change needed — the watcher picks it up automatically.

---

## Tests

```bash
cd price-watcher
npm install
node test/run-tests.js   # extraction + alert/dedupe logic (28 assertions)
node test/e2e.js         # full run against a local fixture site (21 assertions)
```

`test/e2e.js` stands up a fake product page and walks the price through the
whole story — first check, drop, no-change, hitting $60, staying there, dropping
further, bouncing back, and the site going down — asserting who gets emailed at
each step.

---

## Troubleshooting

**No emails at all.** Check
[the Actions tab](../../actions/workflows/price-watch.yml) for red runs. The
most common cause is a missing or mistyped secret; the run log says which.

**`Invalid login` / `535` in the log.** The App Password is wrong, or you used
your normal Gmail password. Regenerate it in Step 1.

**Run fails on the commit step with a permissions error.** In
**Settings → Actions → General → Workflow permissions**, select *Read and write
permissions*.

**The price looks wrong.** Run the workflow with `dry_run` ticked and read the
summary — it names the strategy that produced the number. If it picked up an
unrelated figure, set `priceSelector` in `config.json` to the exact CSS selector
of the price element, or tighten `sanity`.

**It just stops after ~2 months.** GitHub disables scheduled workflows on repos
with no activity for 60 days. The watcher writes its price state back to the
repo, which normally counts as activity — but if it ever goes quiet, open the
Actions tab and re-enable the workflow.

---

## How state works

`state/prices.json` holds the last seen price, a price history, and the alert
bookkeeping. The workflow commits it after each run *only when it changes*, so
the log stays quiet — when the price is flat, the file changes at most once a
day. Those commits are how the bot remembers anything between runs, since each
run starts from a fresh machine.
