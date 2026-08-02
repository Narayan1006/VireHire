import { Bell, Search } from 'lucide-react'

export function TopBar() {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-border bg-white px-8 py-4">
      <div className="flex max-w-md flex-1 items-center gap-3 rounded-lg border border-border bg-cream/50 px-4 py-2.5">
        <Search className="h-4 w-4 shrink-0 text-muted" />
        <input
          type="search"
          placeholder="Search candidates..."
          className="w-full bg-transparent text-sm text-ink outline-none placeholder:text-muted"
        />
      </div>

      <div className="flex items-center gap-4">
        <button
          type="button"
          className="relative flex h-9 w-9 items-center justify-center rounded-full border border-border transition-colors hover:bg-cream"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4 text-muted" />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-emerald-500" />
        </button>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-ink text-xs font-medium text-cream">
          AK
        </div>
      </div>
    </header>
  )
}
