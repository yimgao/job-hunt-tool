'use client'
import { useState } from 'react'
import { API_BASE } from '@/lib/api'
import { Upload, CheckCircle, AlertCircle, Loader2, FileText } from 'lucide-react'

interface ChunkResult {
  chunk_id: string
  embedding_dim: number
  message: string
}

const CHUNK_TYPE_LABELS: Record<string, string> = {
  experience: 'Experience',
  education: 'Education',
  project: 'Projects',
  skill: 'Skills',
  other: 'Other',
}

export default function ResumePage() {
  const [resumeText, setResumeText] = useState('')
  const [userId, setUserId] = useState('user-demo')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<ChunkResult[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleIngest() {
    if (resumeText.trim().length < 100) {
      setError('Resume must be at least 100 characters.')
      return
    }
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const resp = await fetch(`${API_BASE}/api/resume/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, resume_text: resumeText }),
      })
      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}))
        throw new Error(detail?.detail ?? `HTTP ${resp.status}`)
      }
      const data: ChunkResult[] = await resp.json()
      setResults(data)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Resume Ingest</h1>
        <p className="text-sm text-gray-500 mt-1">
          Vectorize your resume so the pipeline can run semantic similarity matching.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Input panel */}
        <div className="col-span-2 space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-gray-500" />
                Resume Text
              </div>
            </label>
            <textarea
              value={resumeText}
              onChange={e => setResumeText(e.target.value)}
              rows={18}
              placeholder="Paste your full resume text here. The system will automatically split it into chunks by paragraph and embed each chunk using OpenAI text-embedding-3-small…"
              className="w-full border border-gray-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
            />
            <div className="flex items-center justify-between mt-2">
              <p className="text-xs text-gray-400">
                {resumeText.length} chars
                {resumeText.length >= 100 && (
                  <span className="text-green-500 ml-2">✓ ready to ingest</span>
                )}
              </p>
              <button
                onClick={handleIngest}
                disabled={loading || resumeText.trim().length < 100}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
              >
                {loading
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Upload className="w-4 h-4" />}
                {loading ? 'Ingesting…' : 'Ingest Resume'}
              </button>
            </div>
          </div>
        </div>

        {/* Right panel */}
        <div className="space-y-4">
          {/* User ID */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <label className="block text-xs font-medium text-gray-500 mb-1.5">User ID</label>
            <input
              value={userId}
              onChange={e => setUserId(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-400 mt-1.5">
              Must be a valid UUID. Use &ldquo;user-demo&rdquo; for testing.
            </p>
          </div>

          {/* How it works */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-3">How It Works</h3>
            <ol className="space-y-2 text-xs text-gray-500">
              <li className="flex gap-2">
                <span className="font-bold text-gray-400">1.</span>
                Resume text is split by paragraph (double newline)
              </li>
              <li className="flex gap-2">
                <span className="font-bold text-gray-400">2.</span>
                Each chunk &gt; 50 chars is kept (max 20 chunks)
              </li>
              <li className="flex gap-2">
                <span className="font-bold text-gray-400">3.</span>
                OpenAI <code className="bg-gray-100 px-1 rounded">text-embedding-3-small</code> creates 1536-dim vectors
              </li>
              <li className="flex gap-2">
                <span className="font-bold text-gray-400">4.</span>
                Stored in PostgreSQL with pgvector for cosine similarity search
              </li>
            </ol>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-50 text-red-600 rounded-lg text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {/* Results */}
          {results && (
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center gap-2 text-green-700 font-medium text-sm mb-3">
                <CheckCircle className="w-4 h-4" />
                {results.length} chunks ingested
              </div>
              <div className="space-y-1.5 max-h-64 overflow-y-auto">
                {results.map((r, i) => (
                  <div key={r.chunk_id} className="flex items-center justify-between text-xs p-2 bg-gray-50 rounded-lg">
                    <span className="text-gray-500 font-mono">
                      #{i + 1} {r.chunk_id.slice(0, 8)}…
                    </span>
                    <span className="text-gray-400">{r.embedding_dim}d</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
