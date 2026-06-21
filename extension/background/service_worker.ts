import { API_BASE, ExtensionTask } from '@shared/types';

const POLL_ALARM = 'jh-poll';
const POLL_MINUTES = 1;

async function pollAndUpdateBadge() {
  try {
    const resp = await fetch(`${API_BASE}/api/ext/tasks/pending`);
    if (!resp.ok) { setBadge(0); return; }

    const tasks: ExtensionTask[] = await resp.json();
    setBadge(tasks.length);
  } catch {
    setBadge(0);
  }
}

function setBadge(count: number) {
  if (count > 0) {
    chrome.action.setBadgeText({ text: String(count) });
    chrome.action.setBadgeBackgroundColor({ color: '#3b82f6' });
  } else {
    chrome.action.setBadgeText({ text: '' });
  }
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(POLL_ALARM, { periodInMinutes: POLL_MINUTES });
  pollAndUpdateBadge();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === POLL_ALARM) pollAndUpdateBadge();
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === 'POLL_NOW') {
    pollAndUpdateBadge().then(() => sendResponse({ ok: true }));
    return true;
  }
});
