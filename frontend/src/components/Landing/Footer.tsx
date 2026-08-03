import { FileText, Book, Code, Zap } from 'lucide-react'
import { GitHubIcon, LinkedInIcon } from '../ui/SocialIcons'

export function Footer() {
  return (
    <footer className="border-t border-border bg-white px-6 py-12 md:px-10 lg:py-16">
      <div className="mx-auto max-w-6xl">
        <div className="grid grid-cols-1 gap-10 md:grid-cols-4 lg:gap-16">
          <div className="md:col-span-1 text-center md:text-left">
            <div className="flex items-center justify-center md:justify-start gap-2 mb-4">
              <Zap className="h-5 w-5 text-ink" />
              <span className="font-instrument text-2xl text-ink">VeriHire AI</span>
            </div>
            <p className="text-sm text-muted">
              An open-source, three-layer AI pipeline for evidence-based candidate ranking.
            </p>
          </div>

          <div className="md:col-span-3 grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="flex flex-col space-y-4">
              <span className="text-sm font-semibold text-ink uppercase tracking-wider">Repository</span>
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-sm text-muted hover:text-ink transition-colors flex items-center gap-2">
                <GitHubIcon className="h-4 w-4" /> Source Code
              </a>
              <a href="#" className="text-sm text-muted hover:text-ink transition-colors flex items-center gap-2">
                <FileText className="h-4 w-4" /> Architecture PDF
              </a>
            </div>

            <div className="flex flex-col space-y-4">
              <span className="text-sm font-semibold text-ink uppercase tracking-wider">Documentation</span>
              <a href="#" className="text-sm text-muted hover:text-ink transition-colors flex items-center gap-2">
                <Book className="h-4 w-4" /> Readme
              </a>
              <a href="#" className="text-sm text-muted hover:text-ink transition-colors flex items-center gap-2">
                <Code className="h-4 w-4" /> API Docs (Swagger)
              </a>
            </div>

            <div className="flex flex-col space-y-4">
              <span className="text-sm font-semibold text-ink uppercase tracking-wider">Connect</span>
              <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" className="text-sm text-muted hover:text-ink transition-colors flex items-center gap-2">
                <LinkedInIcon className="h-4 w-4" /> LinkedIn
              </a>
            </div>
          </div>
        </div>

        <div className="mt-16 flex flex-col items-center justify-between border-t border-border pt-8 md:flex-row">
          <p className="text-sm text-muted">
            © {new Date().getFullYear()} VeriHire AI. Built for the open-source community.
          </p>
        </div>
      </div>
    </footer>
  )
}
