'use client'
import useSWR from 'swr'
import Link from 'next/link'
import { fetcher, type Job, type Application } from '@/lib/api'
import StatCard from '@/components/StatCard'
import PipelineStream from '@/components/PipelineStream'
import StatsChart from '@/components/StatsChart'
import { formatDate } from '@/lib/utils'
import { DollarSign } from 'lucide-react'

interface StatsResponse {
  totals: { jobs: number; applications: number }
  daily: { date: string; jobs: number; applications: number; cost: number }[]
  cost_total: number
}

export default function Dashboard() {
  const { data: jobs = [] } = useSWR<Job[]>('/api/jobs?limit=10', fetcher)
  const { data: apps = [] } = useSWR<Application[]>('/api/applications', fetcher)
  const { data: stats } = useSWR<StatsResponse>('/api/stats/daily?days=7', fetcher)

  const applied = apps.filter(a => a.status === 'applied').length
  const pending = apps.filter(a => a.status === 'pending').length
  const totalJobs = stats?.totals.jobs ?? jobs.length

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">JobHunt-Flow · 多智能体 AI 求职系统</p>
        </div>
        <PipelineStream />
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard title="Jobs Discovered" value={totalJobs} icon="briefcase" />
        <StatCard title="Applications" value={apps.length} icon="file" />
        <StatCard title="Applied" value={applied} icon="send" color="blue" />
        <StatCard title="Pending Review" value={pending} icon="clock" color="amber" />
      </div>

      {/* Chart + Cost */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="col-span-2 bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-900">Activity — Last 7 Days</h2>
          </div>
          {stats?.daily ? (
            <StatsChart data={stats.daily} />
          ) : (
            <div className="h-[220px] flex items-center justify-center text-sm text-gray-400">
              Loading…
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-500">Est. LLM Cost</p>
              <div className="p-2 rounded-lg bg-green-100 text-green-700">
                <DollarSign className="w-4 h-4" />
              </div>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              ${stats?.cost_total.toFixed(3) ?? '0.000'}
            </p>
            <p className="text-xs text-gray-400 mt-1">all-time · target &lt; $0.30/day</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Quick Actions
            </h3>
            <div className="space-y-2">
              <Link
                href="/resume"
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Upload Resume →
              </Link>
              <Link
                href="/jobs"
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Browse Jobs →
              </Link>
              <Link
                href="/applications"
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Track Applications →
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Recent jobs table */}
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
