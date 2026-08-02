import { Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import { GitHubIcon, TwitterIcon, LinkedInIcon } from '../ui/SocialIcons'

const navLinks = [
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Signals', href: '#signals' },
  { label: 'For Recruiters', to: '/dashboard' },
]

const socials = [
  { icon: GitHubIcon, label: 'GitHub', href: 'https://github.com' },
  { icon: TwitterIcon, label: 'Twitter', href: 'https://twitter.com' },
  { icon: LinkedInIcon, label: 'LinkedIn', href: 'https://linkedin.com' },
]

export function Footer() {
  return (
    <footer className="border-t border-border bg-white">
      <div className="mx-auto max-w-6xl px-6 py-14 md:px-10">
        <div className="flex flex-col gap-10 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-ink" />
              <span className="font-instrument text-xl text-ink">VeriHire</span>
            </div>
            <p className="mt-3 max-w-xs text-sm text-muted">
              Evidence-backed hiring intelligence for modern recruiting teams.
            </p>
          </div>

          <nav className="flex flex-wrap gap-8">
            {navLinks.map((link) =>
              link.to ? (
                <Link
                  key={link.label}
                  to={link.to}
                  className="text-sm text-muted transition-colors hover:text-ink"
                >
                  {link.label}
                </Link>
              ) : (
                <a
                  key={link.label}
                  href={link.href}
                  className="text-sm text-muted transition-colors hover:text-ink"
                >
                  {link.label}
                </a>
              ),
            )}
          </nav>

          <div className="flex items-center gap-4">
            {socials.map(({ icon: Icon, label, href }) => (
              <a
                key={label}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={label}
                className="text-muted transition-colors hover:text-ink"
              >
                <Icon className="h-4 w-4" />
              </a>
            ))}
          </div>
        </div>

        <div className="section-divider mt-12" />

        <p className="mt-8 text-center text-[11px] text-muted/50">
          Are you a candidate?{' '}
          <Link
            to="/candidate"
            className="text-muted/70 underline-offset-2 transition-colors hover:text-muted hover:underline"
          >
            Submit your profile →
          </Link>
        </p>

        <p className="mt-4 text-center text-xs text-muted">
          © {new Date().getFullYear()} VeriHire. All rights reserved.
        </p>
      </div>
    </footer>
  )
}
