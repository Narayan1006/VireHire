import { Link } from 'react-router-dom'
import { SubmitForm } from '../components/CandidateSubmit/SubmitForm'

export function CandidateSubmit() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-cream px-6 py-16">
      <Link
        to="/"
        className="mb-8 text-sm text-muted/50 transition-colors hover:text-muted"
      >
        ← VeriHire
      </Link>
      <SubmitForm />
    </div>
  )
}
