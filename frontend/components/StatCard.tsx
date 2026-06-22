import { Briefcase, FileText, Send, Clock, type LucideIcon } from 'lucide-react'

const icons: Record<string, LucideIcon> = {
  briefcase: Briefcase,
  file: FileText,
  send: Send,
  clock: Clock,
}

const colorMap: Record<string, string> = {
  default: 'bg-slate-100 text-slate-700',
  blue: 'bg-blue-100 text-blue-700',
  green: 'bg-green-100 text-green-700',
  amber: 'bg-amber-100 text-amber-700',
}

interface Props {
  title: string
  value: number
  icon: string
  color?: string
}

export default function StatCard({ title, value, icon, color = 'default' }: Props) {
  const Icon = icons[icon] ?? Briefcase
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        <div className={`p-2 rounded-lg ${colorMap[color]}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
    </div>
  )
}
