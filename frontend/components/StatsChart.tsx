'use client'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface DailyStat {
  date: string
  jobs: number
  applications: number
  cost: number
}

interface Props {
  data: DailyStat[]
}

export default function StatsChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 4, right: 16, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="gJobs" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gApps" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip
          contentStyle={{ fontSize: 12, border: '1px solid #e5e7eb', borderRadius: 8, boxShadow: 'none' }}
          formatter={(val, name) => [val, name === 'jobs' ? 'Jobs' : 'Applications']}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
          formatter={(val: string) => val === 'jobs' ? 'Jobs Discovered' : 'Applications'}
        />
        <Area type="monotone" dataKey="jobs" stroke="#3b82f6" strokeWidth={2} fill="url(#gJobs)" dot={false} />
        <Area type="monotone" dataKey="applications" stroke="#8b5cf6" strokeWidth={2} fill="url(#gApps)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
