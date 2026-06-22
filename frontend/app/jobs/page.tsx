'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { fetcher, matchJob, type Job, type MatchReport } from '@/lib/api'
import ScoreBadge from '@/components/ScoreBadge'
import { formatDate } from '@/lib/utils'
import { Search, Zap, Loader2 } from 'lucide-react'

export default function JobsPage() {
  const { data: jobs = [], isLoading } = useSWR<Job[]>('/api/jobs?limit=100', fetcher)
  const [search, setSearch] = useState('')
  const [resume, setResume] = useState('')
  const [scores, setScores] = useState<Record<string, MatchReport>>({})
  const [matching, setMatching] = useState<string | null>(null)

  const filtered = jobs.filter(j =>
    j.title.toLowerCase().includes(search.toLowerCase()) ||
    j.company.toLowerCase().includes(search.toLowerCase())
  )

  async function handleMatch(job: Job) {
    if (!resume.trim()) {
      alert('Paste your resume text above first.')
      return
    }
    setMatching(job.id)
    try {
      const report = await matchJob(resume, job.jd_text)
      setScores(prev => ({ ...prev, [job.id]: report }))
    } catch {
      // silent fail — score stays empty
    } finally {
      setMatching(null)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Jobs</h1>
      <p className="text-sm text-gray-500 mb-6">
        {jobs.length} opportunities discovered. Paste your resume to score any job.
      </p>

      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4">
        <label className="block text-xs font-medium text-gray-500 mb-1.5">
          Your Resume <span className="text-gray-400">(paste to enable match scoring)</span>
        </label>
        <textarea
          value={resume}
          onChange={e => setResume(e.target.value)}
          rows={4}
          placeholder="Paste your resume text here…"
          className="w-full border border-gray-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search title or company…"
            className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <span className="text-sm text-gray-400">{filtered.length} results</span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Position</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Match Score</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr>
                <td colSpan={5} className="py-12 text-center text-gray-400 text-sm">Loading…</td>
              </tr>
            )}
            {!isLoading && filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="py-12 text-center text-gray-400 text-sm">
                  No jobs found. Run the pipeline to discover opportunities.
                </td>
              </tr>
            )}
            {filtered.map(job => {
              const report = scores[job.id]
              return (
                <tr key={job.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{job.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{job.company}</p>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">{job.source}</span>
                  </td>
                  <td className="px-4 py-3">
                    {report ? (
                      <div className="space-y-1">
                        <ScoreBadge score={report.match_score} />
                        {report.recommendation && (
                          <p className="text-xs text-gray-400 max-w-xs truncate">{report.recommendation}</p>
                        )}
                      </div>
                    ) : (
                      <span className="text-gray-300 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">{formatDate(job.created_at)}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleMatch(job)}
                      disabled={matching === job.id || !resume.trim()}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 disabled:opacity-40 transition-colors"
                    >
                      {matching === job.id
                        ? <Loader2 className="w-3 h-3 animate-spin" />
                        : <Zap className="w-3 h-3" />}
                      {matching === job.id ? 'Matching…' : 'Match'}
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
