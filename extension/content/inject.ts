import { API_BASE, ExtensionTask, PageJobInfo } from '@shared/types';

const PANEL_ID = 'jh-flow-panel';
const BTN_ID = 'jh-flow-btn';

// ─── JD Extraction ───────────────────────────────────────────────────────────

const JD_SELECTORS: string[] = [
  // Greenhouse
  '#content', '.content-intro', '[class*="job-description"]',
  // Lever
  '.section-content', '[class*="posting-content"]',
  // LinkedIn
  '.jobs-description__content', '.jobs-box__html-content',
  // SmartRecruiters
  '[data-testid="job-description"]',
  // Generic
  'article', '[class*="description"]', '[id*="description"]',
  'main',
];

const TITLE_SELECTORS: string[] = [
  'h1', '[class*="job-title"]', '[data-testid*="title"]',
  '.posting-headline h2', '.job-details-jobs-unified-top-card__job-title',
];

const COMPANY_SELECTORS: string[] = [
  '[class*="company-name"]', '[class*="employer"]',
  '.jobs-unified-top-card__company-name a',
  '[data-testid*="company"]', '.posting-headline .posting-categories',
];

function extractText(selectors: string[]): string {
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.textContent && el.textContent.trim().length > 20) {
      return el.textContent.trim().replace(/\s+/g, ' ');
    }
  }
  return '';
}

function extractJobInfo(): PageJobInfo {
  const title = extractText(TITLE_SELECTORS) || document.title.split('|')[0].trim();
  const company = extractText(COMPANY_SELECTORS) || '';
  const jd_text = extractText(JD_SELECTORS) || document.body.innerText.slice(0, 8000);
  return { title, company, jd_text: jd_text.slice(0, 8000), url: location.href };
}

// ─── Message listener (popup ↔ content script) ───────────────────────────────

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === 'EXTRACT_JD') {
    sendResponse(extractJobInfo());
    return true;
  }
  if (msg.type === 'AUTOFILL' && msg.task) {
    const n = autofill(msg.task);
    sendResponse({ filled: n });
    return true;
  }
});

// ─── Form field selectors ─────────────────────────────────────────────────────

const FIELD_SELECTORS: Record<string, string[]> = {
  name: [
    '[name="name"]', '[name="full_name"]', '[name="fullName"]',
    '[id*="name" i]:not([id*="company" i])', '[placeholder*="your name" i]',
  ],
  first_name: [
    '[name="first_name"]', '[name="firstName"]',
    '[id*="first_name" i]', '[placeholder*="first name" i]',
  ],
  last_name: [
    '[name="last_name"]', '[name="lastName"]',
    '[id*="last_name" i]', '[placeholder*="last name" i]',
  ],
  email: [
    '[name="email"]', '[type="email"]', '[id*="email" i]',
    '[placeholder*="email" i]',
  ],
  phone: [
    '[name="phone"]', '[name="phone_number"]', '[type="tel"]',
    '[id*="phone" i]', '[placeholder*="phone" i]',
  ],
  cover_letter: [
    '[name*="cover" i]', '[id*="cover" i]', '[aria-label*="cover letter" i]',
    'textarea[placeholder*="cover" i]',
    '.jobs-easy-apply-form-section textarea',
  ],
};

function findField(keys: string[]): HTMLInputElement | HTMLTextAreaElement | null {
  for (const sel of keys) {
    const el = document.querySelector<HTMLInputElement | HTMLTextAreaElement>(sel);
    if (el) return el;
  }
  return null;
}

function setNativeValue(el: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  )?.set;
  const nativeTextareaValueSetter = Object.getOwnPropertyDescriptor(
    window.HTMLTextAreaElement.prototype, 'value'
  )?.set;

  if (el instanceof HTMLTextAreaElement && nativeTextareaValueSetter) {
    nativeTextareaValueSetter.call(el, value);
  } else if (nativeInputValueSetter) {
    nativeInputValueSetter.call(el, value);
  } else {
    el.value = value;
  }
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}

function autofill(task: ExtensionTask): number {
  const p = task.prefill_data;
  let filled = 0;

  const pairs: Array<[string, string]> = [
    ['name', p.name],
    ['first_name', p.name.split(' ')[0] ?? ''],
    ['last_name', p.name.split(' ').slice(1).join(' ') ?? ''],
    ['email', p.email],
    ['phone', p.phone],
    ['cover_letter', p.cover_letter],
  ];

  for (const [key, value] of pairs) {
    if (!value) continue;
    const el = findField(FIELD_SELECTORS[key]);
    if (el) {
      setNativeValue(el, value);
      filled++;
    }
  }
  return filled;
}

// ─── Panel UI ─────────────────────────────────────────────────────────────────

function buildPanel(task: ExtensionTask): HTMLDivElement {
  const panel = document.createElement('div');
  panel.id = PANEL_ID;
  Object.assign(panel.style, {
    position: 'fixed',
    bottom: '80px',
    right: '20px',
    width: '320px',
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
    zIndex: '2147483647',
    fontFamily: '-apple-system, sans-serif',
    fontSize: '13px',
    color: '#1e293b',
    overflow: 'hidden',
  });

  const highlights = task.prefill_data.resume_highlights.slice(0, 4)
    .map(h => `<span style="background:#eff6ff;color:#1d4ed8;padding:2px 6px;border-radius:4px;font-size:11px;margin-right:4px;">${h}</span>`)
    .join('');

  panel.innerHTML = `
    <div style="background:linear-gradient(135deg,#1e40af,#3b82f6);color:#fff;padding:10px 14px;display:flex;align-items:center;gap:8px;">
      <span style="font-weight:700;font-size:14px;">🎯 JobHunt-Flow</span>
      <button id="jh-close" style="margin-left:auto;background:none;border:none;color:#fff;cursor:pointer;font-size:16px;line-height:1;">&times;</button>
    </div>
    <div style="padding:12px 14px;">
      <div style="font-weight:600;margin-bottom:2px;">${task.job_title}</div>
      <div style="color:#64748b;margin-bottom:10px;font-size:12px;">${task.company}</div>
      ${highlights ? `<div style="margin-bottom:10px;">${highlights}</div>` : ''}
      <div id="jh-status" style="min-height:20px;font-size:12px;color:#64748b;margin-bottom:8px;"></div>
      <div style="display:flex;gap:6px;">
        <button id="jh-fill" style="flex:1;padding:7px;border:none;border-radius:6px;background:#3b82f6;color:#fff;font-weight:500;cursor:pointer;font-size:12px;">⚡ 自动填表</button>
        <button id="jh-done" style="flex:1;padding:7px;border:none;border-radius:6px;background:#dcfce7;color:#15803d;font-weight:500;cursor:pointer;font-size:12px;">✅ 已投递</button>
        <button id="jh-skip" style="padding:7px 10px;border:none;border-radius:6px;background:#f1f5f9;color:#475569;cursor:pointer;font-size:12px;">跳过</button>
      </div>
    </div>
  `;

  panel.querySelector('#jh-close')!.addEventListener('click', () => panel.remove());

  panel.querySelector('#jh-fill')!.addEventListener('click', () => {
    const n = autofill(task);
    const status = panel.querySelector<HTMLDivElement>('#jh-status')!;
    status.style.color = n > 0 ? '#15803d' : '#94a3b8';
    status.textContent = n > 0 ? `已填入 ${n} 个字段` : '未检测到可填字段';
  });

  const complete = async (status: 'applied' | 'skipped') => {
    await fetch(`${API_BASE}/api/ext/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: task.task_id, status }),
    }).catch(() => null);
    panel.remove();
  };

  panel.querySelector('#jh-done')!.addEventListener('click', () => complete('applied'));
  panel.querySelector('#jh-skip')!.addEventListener('click', () => complete('skipped'));

  return panel;
}

// ─── Floating trigger button ──────────────────────────────────────────────────

function buildTriggerButton(task: ExtensionTask): HTMLButtonElement {
  const btn = document.createElement('button');
  btn.id = BTN_ID;
  Object.assign(btn.style, {
    position: 'fixed',
    bottom: '24px',
    right: '20px',
    width: '48px',
    height: '48px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg,#1e40af,#3b82f6)',
    border: 'none',
    color: '#fff',
    fontSize: '20px',
    cursor: 'pointer',
    boxShadow: '0 4px 16px rgba(59,130,246,0.4)',
    zIndex: '2147483646',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  });
  btn.title = `JobHunt-Flow: ${task.job_title} @ ${task.company}`;
  btn.textContent = '🎯';

  btn.addEventListener('click', () => {
    const existing = document.getElementById(PANEL_ID);
    if (existing) { existing.remove(); return; }
    document.body.appendChild(buildPanel(task));
  });

  return btn;
}

// ─── Entry point ──────────────────────────────────────────────────────────────

async function init() {
  const resp = await fetch(`${API_BASE}/api/ext/tasks/pending`).catch(() => null);
  if (!resp?.ok) return;

  const tasks: ExtensionTask[] = await resp.json();
  if (!tasks.length) return;

  const task = tasks[0];

  if (!document.getElementById(BTN_ID)) {
    document.body.appendChild(buildTriggerButton(task));
  }
}

init();
setInterval(init, 30_000);
