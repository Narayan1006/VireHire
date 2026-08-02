import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, LogOut } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { cn } from '../../utils/cn'
import { useAuth } from '../../context/AuthContext'

const navLinks = [
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Signals', href: '#signals' },
  { label: 'For Recruiters', to: '/dashboard' },
]

export function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isAuthenticated, authDisabled, logout } = useAuth()

  const isLanding = location.pathname === '/'
  const onHero = isLanding && !scrolled

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 48)
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <motion.header
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className={cn(
        'fixed top-0 right-0 left-0 z-50 transition-all duration-300',
        scrolled || !isLanding
          ? 'border-b border-border bg-surface/90 backdrop-blur-md shadow-sm shadow-ink/[0.03]'
          : 'bg-cream/20 backdrop-blur-sm',
      )}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 md:px-10">
        <Link to="/" className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-ink" strokeWidth={2} />
          <span className="font-instrument text-xl text-ink md:text-2xl">VeriHire</span>
        </Link>

        <nav className="hidden items-center gap-10 md:flex">
          {navLinks.map((link) =>
            link.to ? (
              <Link
                key={link.label}
                to={link.to}
                className={cn(
                  'text-sm transition-colors',
                  onHero ? 'text-ink/75 hover:text-ink' : 'text-muted hover:text-ink',
                )}
              >
                {link.label}
              </Link>
            ) : (
              <a
                key={link.label}
                href={isLanding ? link.href : `/${link.href}`}
                className={cn(
                  'text-sm transition-colors',
                  onHero ? 'text-ink/75 hover:text-ink' : 'text-muted hover:text-ink',
                )}
              >
                {link.label}
              </a>
            ),
          )}
        </nav>

        <div className="flex items-center gap-4 md:gap-6">
          {/* Authenticated state */}
          {(isAuthenticated || authDisabled) && user ? (
            <>
              <span className={cn(
                'hidden text-xs sm:block max-w-[160px] truncate',
                onHero ? 'text-ink/60' : 'text-muted',
              )}>
                {user.email}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                title="Sign out"
                className={cn(
                  'flex items-center gap-1.5 text-sm transition-colors',
                  onHero ? 'text-ink/75 hover:text-ink' : 'text-muted hover:text-ink',
                )}
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:block">Sign out</span>
              </button>
            </>
          ) : (
            /* Guest state */
            <>
              <Link
                to="/login"
                className={cn(
                  'hidden text-sm transition-colors sm:block',
                  onHero ? 'text-ink/75 hover:text-ink' : 'text-muted hover:text-ink',
                )}
              >
                Sign in
              </Link>
              <AnimatePresence>
                {!onHero && (
                  <motion.div
                    key="signup-btn"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Link
                      to="/signup"
                      className="rounded-full bg-ink px-5 py-2.5 text-sm font-medium text-cream hover:opacity-90"
                    >
                      Get Early Access
                    </Link>
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          )}
        </div>
      </div>
    </motion.header>
  )
}
