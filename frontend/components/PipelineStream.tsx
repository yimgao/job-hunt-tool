'use client'
import { useState, useRef } from 'react'
import { API_BASE } from '@/lib/api'
import {
  Play, X, CheckCircle, AlertCircle, Loader2,
  Search, Brain, FileEdit, Send, BarChart2,
} from 'lucide-react'
import ScoreBadge from '@/components/ScoreBadge'

interface StreamEvent {
  type: 'start' | 'node' | 'done' | 'error'
  node?: string
  label?: string
  pipeline_status?: string
  match_score?: number
  errors?: string[]
  message?: string
}

const NODE_ICONS: Record<string, React.ReactNode> = {
  scraper: <Search className="w-4 h-4" />,
  matcher: <Brain className="w-4 h-4" />,
  tailor: <FileEdit className="w-4 h-4" />,
  applicant: <Send className="w-4 h-4" />,
  tracker: <BarChart2 className="w-4 h-4" />,
}

export default function PipelineStream() {
  const [open, setOpen] = useState(false)
  const [resume, setResume] = useState('')
  const [events, setEvents] = useState<StreamEvent[]>([])
  const [running, setRunning] = useState(false)
  const [done, setDone] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  function close() {
    abortRef.current?.abort()
    setOpen(false)
    setEvents([])
    setDone(false)
    setRunning(false)
  }

  async function handleRun() {
    if (resume.trim().length < 50) return
    setEvents([])
    setDone(false)
    setRunning(true)

    const abort = new AbortController()
    abortRef.current = abort

    try {
      const resp = await fetch(`${API_BASE}/api/agents/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_text: resume }),
        signal: abort.signal,
      })

      const reader = resp.body!.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { value, done: streamDone } = await reader.read()
        if (streamDone) break
        buf += decoder.decode(value, { stream: true })

        const lines = buf.split('\n\n')
        buf = lines.pop() ?? ''

        for (const line of lines) {
          const dataLine = line.replace(/^data: /, '').trim()
          if (!dataLine) continue
          try {
            const evt: StreamEvent = JSON.parse(dataLine)
            setEvents(prev => [...prev, evt])
            if (evt.type === 'done' || evt.type === 'error') setDone(true)
          } catch { /* malformed line */ }
        }
      }
    } catch (e: unknown) {
      if ((e as Error).name !== 'AbortError') {
        setEvents(prev => [...prev, { type: 'error', message: String(e) }])
        setDone(true)
      }
    } finally {
      setRunning(false)
    }
  }

  const nodeEvents = events.filter(e => e.type === 'node')
  const lastEvent = events[events.length - 1]

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
      >
        <Play className="w-4 h-4" />
        Run Pipeline
      </button>

      {open && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl w-full max-w-2xl shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-6 border-b border-gray-100">
              <h2 className="text-base font-semibold text-gray-900">Run Agent Pipeline</h2>
              <button onClick={close} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-y-auto flex-1 p-6 space-y-4">
              {!running && !done && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Resume Text <span className="text-gray-400 font-normal">(min 50 chars)</span>
                  </label>
                  <textarea
                    value={resume}
                    onChange={e => setResume(e.target.value)}
                    rows={10}
                    placeholder="Paste your full resume text here…"
                    className="w-full border border-gray-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-400 mt-1">{resume.length} chars</p>
                </div>
              )}

              {(running || done) && (
                <div className="space-y-2">
                  {nodeEvents.map((evt, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-gray-50">
                      <div className="text-blue-500 mt-0.5">
                        {NODE_ICONS[evt.node ?? ''] ?? <Play className="w-4 h-4" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-800">{evt.label}</p>
                        {evt.match_score != null && (
                          <div className="mt-1">
                            <ScoreBadge score={evt.match_score} />
                          </div>
                        )}
                        {evt.errors && evt.errors.length > 0 && (
                          <p className="text-xs text-red-500 mt-0.5">{evt.errors.join(', ')}</p>
                        )}
                      </div>
                      <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                    </div>
                  ))}

                  {running && (
                    <div className="flex items-center gap-3 p-3 rounded-lg border border-blue-100 bg-blue-50">
                      <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                      <p className="text-sm text-blue-700">
                        {nodeEvents.length === 0 ? 'Starting pipeline…' : 'Processing…'}
                      </p>
                    </div>
                  )}

                  {done && lastEvent?.type === 'done' && (
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-green-50">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      <p className="text-sm text-green-700 font-medium">Pipeline complete</p>
                    </div>
                  )}

                  {done && lastEvent?.type === 'error' && (
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-red-50">
                      <AlertCircle className="w-4 h-4 text-red-500" />
                      <p className="text-sm text-red-600">{lastEvent.message}</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-100">
              {done ? (
                <button
                  onClick={() => { setEvents([]); setDone(false) }}
                  className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  Run Again
                </button>
              ) : (
                <button
                  onClick={close}
                  className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
              )}
              {!running && !done && (
                <button
                  onClick={handleRun}
                  disabled={resume.trim().length < 50}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
                >
                  <Play className="w-4 h-4" />
                  Run
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
