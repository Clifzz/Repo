'use strict';

const fs = require('fs');
const path = require('path');

const STATE_PATH =
  process.env.STATE_PATH || path.join(__dirname, '..', 'state', 'prices.json');

function loadState() {
  try {
    const raw = fs.readFileSync(STATE_PATH, 'utf8');
    const parsed = JSON.parse(raw);
    if (!parsed.items) parsed.items = {};
    return parsed;
  } catch {
    return { version: 1, items: {} };
  }
}

function blankItem() {
  return {
    label: null,
    url: null,
    lastPrice: null,
    currency: 'USD',
    availability: null,
    // Date-only on purpose: the file then changes at most once a day when the
    // price is flat, which keeps commit noise down while still proving the
    // watcher ran (and keeps the repo active so GitHub doesn't disable cron).
    lastCheckedOn: null,
    lastChangedAt: null,
    dealAlertSentAtPrice: null,
    consecutiveFailures: 0,
    lastFailureNotifiedAt: null,
    history: [],
  };
}

function getItem(state, id) {
  if (!state.items[id]) state.items[id] = blankItem();
  else state.items[id] = Object.assign(blankItem(), state.items[id]);
  return state.items[id];
}

function recordHistory(item, price, limit = 250) {
  item.history.push({ t: new Date().toISOString(), price });
  if (item.history.length > limit) {
    item.history = item.history.slice(item.history.length - limit);
  }
}

function serialize(state) {
  return `${JSON.stringify(state, null, 2)}\n`;
}

/** @returns {boolean} true when the file content actually changed. */
function saveState(state) {
  const next = serialize(state);
  let current = null;
  try {
    current = fs.readFileSync(STATE_PATH, 'utf8');
  } catch {
    /* first write */
  }
  if (current === next) return false;

  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
  fs.writeFileSync(STATE_PATH, next, 'utf8');
  return true;
}

module.exports = { loadState, saveState, getItem, recordHistory, STATE_PATH };
