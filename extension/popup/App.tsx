import React, { useCallback, useEffect, useState } from 'react';
import { API_BASE, ExtensionTask } from '@shared/types';

const S = {
  header: {
    background: 'linear-gradient(135deg, #1e40af, #3b82f6)',
    color: '#fff',
    padding: '12px 16px',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  } as React.CSSProperties,
  logo: { fontSize: 18, fontWeight: 700, letterSpacing: -0.5 } as React.CSSProperties,
  badge: {
    marginLeft: 'auto',
    background: 'rgba(255,255,255,0.25)',
    borderRadius: 20,
    padding: '2px 8px',
    fontSize: 11,
  } as React.CSSProperties,
  body: { padding: '12px 16px' } as React.CSSProperties,
  empty: { textAlign: 'center', color: '#94a3b8', padding: '32px 0' } as React.CSSProperties,
  card: {
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
  } as React.CSSProperties,
  jobTitle: { fontWeight: 600, fontSize: 14, marginBottom: 2 } as React.CSSProperties,
  company: { color: '#64748b', marginBottom: 8 } as React.CSSProperties,
  sectionLabel: {
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    color: '#94a3b8',
    marginBottom: 4,
  } as React.CSSProperties,
  highlight: {
    display: 'inline-block',
    background: '#eff6ff',
    color: '#1d4ed8',
    borderRadius: 4,
    padding: '2px 6px',
    marginRight: 4,
    marginBottom: 4,
    fontSize: 11,
  } as React.CSSProperties,
  coverPreview: {
    background: '#f8fafc',
    borderRadius: 4,
    padding: '6px 8px',
    fontSize: 11,
    color: '#475569',
    maxHeight: 60,
    overflow: 'hidden',
    marginBottom: 8,
    lineHeight: 1.5,
  } as React.CSSProperties,
  actions: { display: 'flex', gap: 6, marginTop: 10 } as React.CSSProperties,
  btn: (variant: 'primary' | 'ghost' | 'danger') => ({
    flex: variant === 'ghost' ? 0 : 1,
    padding: '7px 12px',
    borderRadius: 6,
    border: 'none',
    cursor: 'pointer',
    fontWeight: 500,
    fontSize: 12,
    background: variant === 'primary' ? '#3b82f6' : variant === 'danger' ? '#fee2e2' : '#f1f5f9',
    color: variant === 'primary' ? '#fff' : variant === 'danger' ? '#b91c1c' : '#475569',
  } as React.CSSProperties),
  error: { color: '#ef4444', padding: '8px 0', fontSize: 12 } as React.CSSProperties,
};

function TaskCard({
  task,
  onComplete,
}: {
  task: ExtensionTask;
  onComplete: (id: string, status: 'applied' | 'skipped') => void;
}) {
  const [copied, setCopied] = useState(false);

  const copyCover = async () => {
    await navigator.clipboard.writeText(task.prefill_data.cover_letter);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const highlights = task.prefill_data.resume_highlights;
  const hasCover = task.prefill_data.cover_letter.length > 0;

  return (
    <div style={S.card}>
      <div style={S.jobTitle}>{task.job_title}</div>
      <div style={S.company}>{task.company}</div>

      {highlights.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <div style={S.sectionLabel}>匹配亮点</div>
          {highlights.map((h, i) => (
            <span key={i} style={S.highlight}>{h}</span>
          ))}
        </div>
      )}

      {hasCover && (
        <div style={{ marginBottom: 4 }}>
          <div style={S.sectionLabel}>求职信预览</div>
          <div style={S.coverPreview}>{task.prefill_data.cover_letter}</div>
        </div>
      )}

      <div style={S.actions}>
        {hasCover && (
          <button style={S.btn('ghost')} onClick={copyCover}>
            {copied ? '✓ 已复制' : '📋 复制求职信'}
          </button>
        )}
        <button style={S.btn('primary')} onClick={() => onComplete(task.task_id, 'applied')}>
          ✅ 已投递
        </button>
        <button style={S.btn('danger')} onClick={() => onComplete(task.task_id, 'skipped')}>
          跳过
        </button>
      </div>

      {task.apply_url && (
        <div style={{ marginTop: 8 }}>
          <a
            href={task.apply_url}
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: 11, color: '#3b82f6' }}
          >
            前往投递页面 ↗
          </a>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [tasks, setTasks] = useState<ExtensionTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchPending = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/ext/tasks/pending`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: ExtensionTask[] = await resp.json();
      setTasks(data);
      setError('');
    } catch (e) {
      setError('无法连接到 JobHunt-Flow 后端（请确认服务在 localhost:8001 运行）');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPending();
    const id = setInterval(fetchPending, 10_000);
    return () => clearInterval(id);
  }, [fetchPending]);

  const handleComplete = async (taskId: string, status: 'applied' | 'skipped') => {
    try {
      await fetch(`${API_BASE}/api/ext/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId, status }),
      });
      setTasks(prev => prev.filter(t => t.task_id !== taskId));
    } catch {
      setError('更新状态失败，请重试');
    }
  };

  return (
    <>
      <div style={S.header}>
        <span style={S.logo}>🎯 JobHunt-Flow</span>
        {tasks.length > 0 && <span style={S.badge}>{tasks.length} 待投递</span>}
      </div>

      <div style={S.body}>
        {loading && <div style={S.empty}>加载中…</div>}
        {error && <div style={S.error}>{error}</div>}
        {!loading && !error && tasks.length === 0 && (
          <div style={S.empty}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>✨</div>
            <div>暂无待投递任务</div>
            <div style={{ fontSize: 11, marginTop: 4, color: '#cbd5e1' }}>
              运行 POST /api/agents/run 触发流水线
            </div>
          </div>
        )}
        {tasks.map(t => (
          <TaskCard key={t.task_id} task={t} onComplete={handleComplete} />
        ))}
      </div>
    </>
  );
}
