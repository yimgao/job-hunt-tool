import React, { useCallback, useEffect, useRef, useState } from 'react';
import { API_BASE, ExtensionTask, MatchReport, PageJobInfo } from '@shared/types';

// ─── Styles ──────────────────────────────────────────────────────────────────

const S = {
  root: { width: 380, minHeight: 200, fontFamily: '-apple-system, sans-serif', fontSize: 13, background: '#f8fafc', color: '#1e293b' } as React.CSSProperties,
  header: { background: 'linear-gradient(135deg,#1e40af,#3b82f6)', color: '#fff', padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 8 } as React.CSSProperties,
  logo: { fontWeight: 700, fontSize: 15, letterSpacing: -0.5 } as React.CSSProperties,
  badge: { marginLeft: 4, background: 'rgba(255,255,255,0.25)', borderRadius: 20, padding: '2px 7px', fontSize: 11 } as React.CSSProperties,
  tabs: { display: 'flex', borderBottom: '1px solid #e2e8f0', background: '#fff' } as React.CSSProperties,
  tab: (active: boolean) => ({ flex: 1, padding: '8px 0', border: 'none', background: 'none', cursor: 'pointer', fontSize: 12, fontWeight: active ? 600 : 400, color: active ? '#1d4ed8' : '#64748b', borderBottom: active ? '2px solid #3b82f6' : '2px solid transparent' } as React.CSSProperties),
  body: { padding: '12px 14px' } as React.CSSProperties,
  empty: { textAlign: 'center', color: '#94a3b8', padding: '32px 0', fontSize: 13 } as React.CSSProperties,
  card: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: 12, marginBottom: 10 } as React.CSSProperties,
  jobTitle: { fontWeight: 600, fontSize: 14, marginBottom: 2 } as React.CSSProperties,
  company: { color: '#64748b', marginBottom: 8, fontSize: 12 } as React.CSSProperties,
  label: { fontSize: 11, fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: 0.5, color: '#94a3b8', marginBottom: 4 } as React.CSSProperties,
  chip: { display: 'inline-block', background: '#eff6ff', color: '#1d4ed8', borderRadius: 4, padding: '2px 6px', marginRight: 4, marginBottom: 4, fontSize: 11 } as React.CSSProperties,
  chipRed: { display: 'inline-block', background: '#fef2f2', color: '#b91c1c', borderRadius: 4, padding: '2px 6px', marginRight: 4, marginBottom: 4, fontSize: 11 } as React.CSSProperties,
  coverPreview: { background: '#f8fafc', borderRadius: 4, padding: '6px 8px', fontSize: 11, color: '#475569', maxHeight: 60, overflow: 'hidden', marginBottom: 8, lineHeight: 1.5 } as React.CSSProperties,
  actions: { display: 'flex', gap: 6, marginTop: 10 } as React.CSSProperties,
  btn: (v: 'primary' | 'ghost' | 'danger' | 'outline') => ({
    flex: v === 'ghost' || v === 'outline' ? 0 : 1,
    padding: '7px 12px',
    borderRadius: 6,
    border: v === 'outline' ? '1px solid #e2e8f0' : 'none',
    cursor: 'pointer',
    fontWeight: 500,
    fontSize: 12,
    background: v === 'primary' ? '#3b82f6' : v === 'danger' ? '#fee2e2' : '#f1f5f9',
    color: v === 'primary' ? '#fff' : v === 'danger' ? '#b91c1c' : '#475569',
  } as React.CSSProperties),
  score: (s: number) => ({
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 64,
    height: 64,
    borderRadius: '50%',
    background: s >= 0.6 ? '#dcfce7' : s >= 0.3 ? '#fef9c3' : '#fee2e2',
    color: s >= 0.6 ? '#15803d' : s >= 0.3 ? '#92400e' : '#b91c1c',
    fontSize: 18,
    fontWeight: 700,
  } as React.CSSProperties),
  error: { color: '#ef4444', padding: '6px 0', fontSize: 12 } as React.CSSProperties,
  textarea: { width: '100%', borderRadius: 6, border: '1px solid #e2e8f0', padding: '8px', fontSize: 12, fontFamily: 'inherit', resize: 'vertical' as const, outline: 'none', boxSizing: 'border-box' as const } as React.CSSProperties,
};

// ─── Task card ────────────────────────────────────────────────────────────────

function TaskCard({ task, onComplete }: { task: ExtensionTask; onComplete: (id: string, s: 'applied' | 'skipped') => void }) {
  const [copied, setCopied] = useState(false);
  const hasCover = task.prefill_data.cover_letter.length > 0;

  const copyCover = async () => {
    await navigator.clipboard.writeText(task.prefill_data.cover_letter);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div style={S.card}>
      <div style={S.jobTitle}>{task.job_title}</div>
      <div style={S.company}>{task.company}</div>

      {task.prefill_data.resume_highlights.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <div style={S.label}>匹配亮点</div>
          {task.prefill_data.resume_highlights.map((h, i) => <span key={i} style={S.chip}>{h}</span>)}
        </div>
      )}

      {hasCover && (
        <div style={{ marginBottom: 4 }}>
          <div style={S.label}>求职信预览</div>
          <div style={S.coverPreview}>{task.prefill_data.cover_letter}</div>
        </div>
      )}

      <div style={S.actions}>
        {hasCover && <button style={S.btn('ghost')} onClick={copyCover}>{copied ? '✓ 已复制' : '📋 求职信'}</button>}
        <button style={S.btn('primary')} onClick={() => onComplete(task.task_id, 'applied')}>✅ 已投递</button>
        <button style={S.btn('danger')} onClick={() => onComplete(task.task_id, 'skipped')}>跳过</button>
      </div>

      {task.apply_url && (
        <div style={{ marginTop: 8 }}>
          <a href={task.apply_url} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: '#3b82f6' }}>
            前往投递页面 ↗
          </a>
        </div>
      )}
    </div>
  );
}

// ─── Tasks tab ────────────────────────────────────────────────────────────────

function TasksTab() {
  const [tasks, setTasks] = useState<ExtensionTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetch_ = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/api/ext/tasks/pending`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setTasks(await r.json());
      setError('');
    } catch {
      setError('无法连接到后端 (localhost:8001)');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch_(); const t = setInterval(fetch_, 10_000); return () => clearInterval(t); }, [fetch_]);

  const handleComplete = async (id: string, status: 'applied' | 'skipped') => {
    await fetch(`${API_BASE}/api/ext/complete`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: id, status }),
    }).catch(() => null);
    setTasks(p => p.filter(t => t.task_id !== id));
  };

  return (
    <div style={S.body}>
      {loading && <div style={S.empty}>加载中…</div>}
      {error && <div style={S.error}>{error}</div>}
      {!loading && !error && tasks.length === 0 && (
        <div style={S.empty}>
          <div style={{ fontSize: 28, marginBottom: 6 }}>✨</div>
          <div>暂无待投递任务</div>
          <div style={{ fontSize: 11, marginTop: 4, color: '#cbd5e1' }}>切换到「分析」标签页分析当前职位</div>
        </div>
      )}
      {tasks.map(t => <TaskCard key={t.task_id} task={t} onComplete={handleComplete} />)}
    </div>
  );
}

// ─── Analyze tab ──────────────────────────────────────────────────────────────

type AnalyzeState = 'idle' | 'extracting' | 'analyzing' | 'done' | 'preparing' | 'ready';

function AnalyzeTab({ resume }: { resume: string }) {
  const [state, setState] = useState<AnalyzeState>('idle');
  const [jobInfo, setJobInfo] = useState<PageJobInfo | null>(null);
  const [report, setReport] = useState<MatchReport | null>(null);
  const [error, setError] = useState('');

  const extractAndAnalyze = async () => {
    if (!resume) { setError('请先在「设置」标签页填入简历'); return; }
    setError('');
    setState('extracting');

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) { setError('无法获取当前页面'); setState('idle'); return; }

    let info: PageJobInfo;
    try {
      info = await chrome.tabs.sendMessage(tab.id, { type: 'EXTRACT_JD' });
    } catch {
      setError('无法提取职位信息（请刷新页面后重试）');
      setState('idle');
      return;
    }

    if (!info?.jd_text || info.jd_text.length < 50) {
      setError('职位描述内容不足，无法分析');
      setState('idle');
      return;
    }

    setJobInfo(info);
    setState('analyzing');

    try {
      const r = await fetch(`${API_BASE}/api/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_text: resume, jd_text: info.jd_text }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setReport(data.report ?? data);
      setState('done');
    } catch (e) {
      setError(`分析失败: ${e}`);
      setState('idle');
    }
  };

  const preparePipeline = async () => {
    if (!jobInfo || !resume) return;
    setState('preparing');
    setError('');
    try {
      const r = await fetch(`${API_BASE}/api/agents/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_text: resume, keywords: jobInfo.title.split(' ').slice(0, 3) }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setState('ready');
    } catch (e) {
      setError(`流水线失败: ${e}`);
      setState('done');
    }
  };

  const score = report?.match_score ?? 0;
  const busy = state === 'extracting' || state === 'analyzing' || state === 'preparing';

  return (
    <div style={S.body}>
      {jobInfo && (
        <div style={{ marginBottom: 12 }}>
          <div style={S.jobTitle}>{jobInfo.title || '未知职位'}</div>
          <div style={S.company}>{jobInfo.company || new URL(jobInfo.url).hostname}</div>
        </div>
      )}

      {report && (
        <div style={{ ...S.card, display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 10 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={S.score(score)}>{Math.round(score * 100)}%</div>
            <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>匹配度</div>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, color: '#475569', marginBottom: 6, lineHeight: 1.4 }}>{report.summary}</div>
            {report.strengths?.length > 0 && (
              <div style={{ marginBottom: 4 }}>
                {report.strengths.slice(0, 3).map((s, i) => <span key={i} style={S.chip}>{s}</span>)}
              </div>
            )}
            {report.gaps?.length > 0 && (
              <div>
                {report.gaps.slice(0, 2).map((g, i) => <span key={i} style={S.chipRed}>{g}</span>)}
              </div>
            )}
          </div>
        </div>
      )}

      {error && <div style={S.error}>{error}</div>}

      {state === 'ready' && (
        <div style={{ ...S.card, background: '#f0fdf4', borderColor: '#bbf7d0', color: '#15803d', textAlign: 'center', marginBottom: 10 }}>
          ✅ 已生成定制简历，请切换到「任务」标签查看
        </div>
      )}

      <div style={S.actions}>
        <button style={{ ...S.btn('primary'), opacity: busy ? 0.6 : 1 }} onClick={extractAndAnalyze} disabled={busy}>
          {state === 'extracting' ? '提取中…' : state === 'analyzing' ? '分析中…' : '🔍 分析当前职位'}
        </button>
        {(state === 'done' || state === 'preparing') && score >= 0.3 && (
          <button style={S.btn('outline')} onClick={preparePipeline} disabled={busy}>
            {busy ? '处理中…' : '✨ 定制简历'}
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Settings tab ─────────────────────────────────────────────────────────────

function SettingsTab({ resume, onSave }: { resume: string; onSave: (r: string) => void }) {
  const [text, setText] = useState(resume);
  const [saved, setSaved] = useState(false);

  const save = () => {
    chrome.storage.local.set({ resume_text: text });
    onSave(text);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  return (
    <div style={S.body}>
      <div style={{ marginBottom: 8 }}>
        <div style={S.label}>简历全文</div>
        <textarea
          style={{ ...S.textarea, minHeight: 180 }}
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="粘贴你的简历全文（纯文本）…"
        />
      </div>
      <button style={S.btn('primary')} onClick={save}>{saved ? '✓ 已保存' : '💾 保存简历'}</button>
      <div style={{ marginTop: 10, fontSize: 11, color: '#94a3b8', lineHeight: 1.5 }}>
        后端地址: <code style={{ fontSize: 10 }}>{API_BASE}</code>
      </div>
    </div>
  );
}

// ─── Root ─────────────────────────────────────────────────────────────────────

type Tab = 'tasks' | 'analyze' | 'settings';

export default function App() {
  const [tab, setTab] = useState<Tab>('tasks');
  const [resume, setResume] = useState('');
  const [taskCount, setTaskCount] = useState(0);

  useEffect(() => {
    chrome.storage.local.get('resume_text', d => {
      if (d.resume_text) setResume(d.resume_text);
    });
    const pollCount = async () => {
      const r = await fetch(`${API_BASE}/api/ext/tasks/pending`).catch(() => null);
      if (r?.ok) setTaskCount((await r.json()).length);
    };
    pollCount();
  }, []);

  return (
    <div style={S.root}>
      <div style={S.header}>
        <span style={S.logo}>🎯 JobHunt-Flow</span>
        {taskCount > 0 && <span style={S.badge}>{taskCount}</span>}
      </div>
      <div style={S.tabs}>
        <button style={S.tab(tab === 'tasks')} onClick={() => setTab('tasks')}>任务{taskCount > 0 ? ` (${taskCount})` : ''}</button>
        <button style={S.tab(tab === 'analyze')} onClick={() => setTab('analyze')}>分析</button>
        <button style={S.tab(tab === 'settings')} onClick={() => setTab('settings')}>设置</button>
      </div>
      {tab === 'tasks' && <TasksTab />}
      {tab === 'analyze' && <AnalyzeTab resume={resume} />}
      {tab === 'settings' && <SettingsTab resume={resume} onSave={setResume} />}
    </div>
  );
}
