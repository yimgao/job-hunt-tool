'use client'
import useSWR from 'swr'
import Link from 'next/link'
import { fetcher, type Job, type Application } from '@/lib/api'
import StatCard from '@/components/StatCard'
import PipelineRunner from '@/components/PipelineRunner'
import { formatDate } from '@/lib/utils'

export default function Dashboard() {
  const { data: jobs = [] } = useSWR<Job[]>('/api/jobs?limit=10', fetcher)
  const { data: apps = [] } = useSWR<Application[]>('/api/applications', fetcher)

  const applied = apps.filter(a => a.status === 'applied').length
  const pending = apps.filter(a => a.status === 'pending').length

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">JobHunt-Flow · 多智能体 AI 求职系统</p>
        </div>
        <PipelineRunner />
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard title="Jobs Discovered" value={jobs.length} icon="briefcase" />
        <StatCard title="Applications" value={apps.length} icon="file" />
        <StatCard title="Applied" value={applied} icon="send" color="blue" />
        <StatCard title="Pending Review" value={pending} icon="clock" color="amber" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-900">Recent Jobs</h2>
          <Link href="/jobs" className="text-xs text-blue-600 hover:underline">
            View all →
          </Link>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Position</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Company</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {jobs.length === 0 && (
              <tr>
                <td colSpan={4} className="px-6 py-12 text-center text-sm text-gray-400">
                  No jobs yet. Click <strong>Run Pipeline</strong> to discover opportunities.
                </td>
              </tr>
            )}
            {jobs.map(job => (
              <tr key={job.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-3 font-medium text-gray-900">{job.title}</td>
                <td className="px-6 py-3 text-gray-600">{job.company}</td>
                <td className="px-6 py-3">
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">{job.source}</span>
                </td>
                <td className="px-6 py-3 text-gray-400 text-xs">{formatDate(job.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
