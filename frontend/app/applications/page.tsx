'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { fetcher, patchApplicationStatus, type Application } from '@/lib/api'
import { formatDate } from '@/lib/utils'

const STATUSES = ['pending', 'applied', 'interview', 'offer', 'rejected'] as const

const statusColors: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600',
  applied: 'bg-blue-100 text-blue-700',
  interview: 'bg-purple-100 text-purple-700',
  offer: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-600',
}

export default function ApplicationsPage() {
  const { data: apps = [], isLoading, mutate } = useSWR<Application[]>('/api/applications', fetcher)
  const [filter, setFilter] = useState('all')
  const [updating, setUpdating] = useState<string | null>(null)

  const filtered = filter === 'all' ? apps : apps.filter(a => a.status === filter)

  async function handleStatus(id: string, status: string) {
    setUpdating(id)
    try {
      await patchApplicationStatus(id, status)
      await mutate()
    } catch {
      // silent fail
    } finally {
      setUpdating(null)
    }
  }

  const counts: Record<string, number> = { all: apps.length }
  for (const s of STATUSES) counts[s] = apps.filter(a => a.status === s).length

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Applications</h1>
      <p className="text-sm text-gray-500 mb-6">Track and update your application pipeline.</p>

      <div className="flex flex-wrap gap-2 mb-6">
        {(['all', ...STATUSES] as const).map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              filter === s
                ? 'bg-slate-900 text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
            <span className="ml-1.5 text-xs opacity-60">{counts[s] ?? 0}</span>
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Job ID</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Updated</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr>
                <td colSpan={4} className="py-12 text-center text-sm text-gray-400">Loading…</td>
              </tr>
            )}
            {!isLoading && filtered.length === 0 && (
              <tr>
                <td colSpan={4} className="py-12 text-center text-sm text-gray-400">
                  No applications {filter !== 'all' ? `with status "${filter}"` : 'yet'}.
                </td>
              </tr>
            )}
            {filtered.map(app => (
              <tr key={app.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-3 font-mono text-xs text-gray-500">
                  {app.job_id.slice(0, 8)}…
                </td>
                <td className="px-6 py-3">
                  <select
                    value={app.status}
                    disabled={updating === app.id}
                    onChange={e => handleStatus(app.id, e.target.value)}
                    className={`px-2.5 py-1 rounded-md text-xs font-medium border-0 cursor-pointer appearance-none ${statusColors[app.status]}`}
                  >
                    {STATUSES.map(s => (
                      <option key={s} value={s}>
                        {s.charAt(0).toUpperCase() + s.slice(1)}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-6 py-3 text-xs text-gray-400">{formatDate(app.created_at)}</td>
                <td className="px-6 py-3 text-xs text-gray-400">{formatDate(app.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
