'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, Briefcase, FileText } from 'lucide-react'

const nav = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/jobs', label: 'Jobs', icon: Briefcase },
  { href: '/applications', label: 'Applications', icon: FileText },
]

export default function Sidebar() {
  const path = usePathname()
  return (
    <aside className="w-60 bg-slate-900 text-white flex flex-col flex-shrink-0">
      <div className="px-6 py-5 border-b border-slate-700">
        <h1 className="text-base font-bold tracking-tight">JobHunt-Flow</h1>
        <p className="text-xs text-slate-400 mt-0.5">多智能体 AI 求职系统</p>
      </div>
      <nav className="flex-1 py-3">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 px-6 py-2.5 text-sm transition-colors ${
              path === href
                ? 'bg-slate-700 text-white font-medium'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </Link>
        ))}
      </nav>
      <div className="px-6 py-4 border-t border-slate-700">
        <p className="text-xs text-slate-500">v0.1.0 · Phase 4</p>
      </div>
    </aside>
  )
}
