import {
  LayoutDashboard,
  Trophy,
  FileText,
  Zap,
  Settings,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { cn } from '../../utils/cn'

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', to: '/dashboard', end: true },
  { icon: Trophy, label: 'Rankings', to: '/dashboard' },
  { icon: FileText, label: 'Job Descriptions', to: '/dashboard' },
  { icon: Settings, label: 'Settings', to: '/settings' },
]

export function Sidebar() {
  return (
    <aside className="hidden h-screen w-60 shrink-0 flex-col border-r border-border bg-white lg:flex">
      <div className="flex items-center gap-2 px-6 py-6">
        <Zap className="h-4 w-4 text-ink" />
        <span className="font-instrument text-2xl text-ink">VeriHire</span>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3">
        {navItems.map(({ icon: Icon, label, to, end }) => (
          <NavLink
            key={label}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-4 py-3 text-sm transition-colors',
                isActive
                  ? 'bg-ink text-cream'
                  : 'text-muted hover:bg-ink/5 hover:text-ink',
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
