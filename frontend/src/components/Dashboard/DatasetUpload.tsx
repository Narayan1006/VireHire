import { useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { FileSpreadsheet, Upload, CheckCircle2 } from 'lucide-react'

export interface UploadedDataset {
  filePath: string
  filename: string
  validCandidates: number
  totalRows: number
}

interface DatasetUploadProps {
  onUpload: (file: File) => Promise<UploadedDataset>
  dataset: UploadedDataset | null
  defaultLabel?: string
}

export function DatasetUpload({
  onUpload,
  dataset,
  defaultLabel = 'Using built-in sample dataset until you upload your own CSV.',
}: DatasetUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Please upload a .csv file.')
      return
    }
    setError(null)
    setUploading(true)
    try {
      await onUpload(file)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setUploading(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-editorial p-6"
    >
      <div className="mb-4 flex items-center gap-2">
        <FileSpreadsheet className="h-4 w-4 text-muted" />
        <label className="text-sm font-medium text-ink">Candidate Dataset</label>
      </div>

      <p className="mb-4 text-sm text-muted">
        Upload a CSV with candidate records. Required:{' '}
        <code className="rounded bg-cream px-1.5 py-0.5 text-xs">role</code>{' '}
        (or <code className="rounded bg-cream px-1.5 py-0.5 text-xs">job_title</code>
        , <code className="rounded bg-cream px-1.5 py-0.5 text-xs">position</code>
        ). Optional: name, email, skills, online_links.
      </p>
      <p className="mb-4 text-xs text-muted">
        <a
          href="/sample-candidates.csv"
          download
          className="font-medium text-ink underline underline-offset-2"
        >
          Download sample CSV template
        </a>
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center justify-center rounded-lg border border-dashed px-4 py-10 transition-colors ${
          dragOver
            ? 'border-ink bg-cream/80'
            : 'border-border bg-cream/30 hover:bg-cream/50'
        }`}
      >
        <Upload className="h-6 w-6 text-muted" />
        <p className="mt-3 text-sm text-ink">
          Drag & drop CSV here, or{' '}
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="font-medium underline underline-offset-2"
            disabled={uploading}
          >
            browse files
          </button>
        </p>
        <p className="mt-1 text-xs text-muted">Max 50 MB · .csv only</p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) handleFile(file)
            e.target.value = ''
          }}
        />
      </div>

      {uploading && (
        <p className="mt-3 text-sm text-muted">Uploading and validating CSV…</p>
      )}

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {dataset ? (
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />
          <div className="text-sm">
            <p className="font-medium text-emerald-900">{dataset.filename}</p>
            <p className="text-emerald-800/80">
              {dataset.validCandidates} valid candidates from {dataset.totalRows} rows — ready to rank
            </p>
          </div>
        </div>
      ) : (
        <p className="mt-4 text-xs text-muted">{defaultLabel}</p>
      )}
    </motion.div>
  )
}
