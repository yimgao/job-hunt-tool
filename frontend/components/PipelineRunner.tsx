'use client'
import { useState } from 'react'
import { runPipeline, type PipelineResult } from '@/lib/api'
import { Play, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'

export default function PipelineRunner() {
  const [open, setOpen] = useState(false)
  const [resume, setResume] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PipelineResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  function close() {
    setOpen(false)
    setResult(null)
    setError(null)
  }

  async function handleRun() {
    if (resume.trim().length < 100) {
      setError('Resume must be at least 100 characters.')
      return
    }
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const r = await runPipeline(resume)
      setResult(r)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

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
          <div className="bg-white rounded-xl w-full max-w-2xl shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-gray-100">
              <h2 className="text-base font-semibold text-gray-900">Run Agent Pipeline</h2>
              <button onClick={close} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Resume Text <span className="text-gray-400 font-normal">(min 100 chars)</span>
                </label>
                <textarea
                  value={resume}
                  onChange={e => setResume(e.target.value)}
                  rows={10}
                  placeholder="Paste your full resume text here..."
                  className="w-full border border-gray-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-400 mt-1">{resume.length} chars</p>
              </div>

              {error && (
                <div className="flex items-start gap-2 p-3 bg-red-50 text-red-600 rounded-lg text-sm">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  {error}
                </div>
              )}

              {result && (
                <div className="p-4 bg-green-50 rounded-lg text-sm space-y-1">
                  <div className="flex items-center gap-2 text-green-700 font-medium">
                    <CheckCircle className="w-4 h-4" />
                    Completed — {result.pipeline_status}
                  </div>
                  {result.match_score > 0 && (
                    <p className="text-green-600 pl-6">
                      Score: {(result.match_score * 100).toFixed(0)}% · Priority: {result.priority}
                    </p>
                  )}
                  {result.errors?.length > 0 && (
                    <p className="text-red-500 pl-6">Errors: {result.errors.join(', ')}</p>
                  )}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 px-6 pb-6">
              <button
                onClick={close}
                className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRun}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {loading ? 'Running…' : 'Run'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
