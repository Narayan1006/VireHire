import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Sidebar } from '../components/Dashboard/Sidebar'
import { Navbar } from '../components/shared/Navbar'
import { Menu, Zap, Save, CheckCircle2, XCircle } from 'lucide-react'
import { getSettings, saveSettings, testGithub, testGroq, testOllama } from '../services/api'

export function Settings() {
  const [provider, setProvider] = useState<'groq' | 'ollama'>('groq')
  const [githubToken, setGithubToken] = useState('')
  const [groqKey, setGroqKey] = useState('')
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434')

  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  
  const [toast, setToast] = useState<{msg: string, type: 'success' | 'error'} | null>(null)

  const showToast = (msg: string, type: 'success' | 'error') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 5000)
  }

  useEffect(() => {
    async function loadSettings() {
      try {
        const data = await getSettings()
        if (data) {
          setProvider(data.aiProvider as 'groq' | 'ollama' || 'groq')
          setGithubToken(data.githubToken || '')
          setGroqKey(data.groqApiKey || '')
          setOllamaUrl(data.ollamaBaseUrl || 'http://localhost:11434')
        }
      } catch (e: any) {
        // Not found is fine for new users
        if (e.message !== 'Not Found') {
          showToast('Failed to load settings', 'error')
        }
      } finally {
        setIsLoading(false)
      }
    }
    loadSettings()
  }, [])

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const saved = await saveSettings({
        aiProvider: provider,
        githubToken: githubToken,
        groqApiKey: groqKey,
        ollamaBaseUrl: ollamaUrl,
      })
      setGithubToken(saved.githubToken || '')
      setGroqKey(saved.groqApiKey || '')
      showToast('Settings saved successfully', 'success')
    } catch (e: any) {
      showToast(e.message || 'Failed to save', 'error')
    } finally {
      setIsSaving(false)
    }
  }

  const handleTestGithub = async () => {
    try {
      const res = await testGithub(githubToken)
      showToast(res.message, 'success')
    } catch (e: any) {
      showToast(e.message, 'error')
    }
  }

  const handleTestGroq = async () => {
    try {
      const res = await testGroq(groqKey)
      showToast(res.message, 'success')
    } catch (e: any) {
      showToast(e.message, 'error')
    }
  }

  const handleTestOllama = async () => {
    try {
      const res = await testOllama(ollamaUrl)
      showToast(res.message, 'success')
    } catch (e: any) {
      showToast(e.message, 'error')
    }
  }

  return (
    <div className="min-h-screen bg-cream">
      <Navbar />
      <div className="flex pt-[72px]">
        <Sidebar />

        <div className="flex min-h-[calc(100vh-72px)] flex-1 flex-col">
          {/* Mobile header */}
          <div className="flex items-center gap-3 border-b border-border bg-white px-6 py-4 lg:hidden">
            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-border"
              aria-label="Menu"
            >
              <Menu className="h-4 w-4" />
            </button>
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              <span className="font-instrument text-xl">VeriHire</span>
            </div>
          </div>

          <main className="flex-1 space-y-8 p-8 max-w-4xl mx-auto w-full">
            <div className="flex items-center justify-between">
              <h1 className="font-instrument text-3xl font-bold tracking-tight text-ink">Settings</h1>
            </div>

            {isLoading ? (
              <div className="animate-pulse space-y-4">
                <div className="h-40 bg-border rounded-xl"></div>
                <div className="h-40 bg-border rounded-xl"></div>
              </div>
            ) : (
              <div className="space-y-6">
                
                {/* General Configuration */}
                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="card-editorial p-6">
                  <h2 className="text-xl font-medium text-ink mb-4">AI Provider</h2>
                  <p className="text-sm text-muted mb-4">Choose the LLM backend for running candidate evaluations.</p>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <button
                      onClick={() => setProvider('groq')}
                      className={`flex flex-col items-center justify-center p-4 rounded-xl border ${provider === 'groq' ? 'border-ink bg-ink/5' : 'border-border bg-cream/30'} transition-all`}
                    >
                      <span className={`font-semibold ${provider === 'groq' ? 'text-ink' : 'text-muted'}`}>Groq</span>
                      <span className="text-xs text-muted mt-1">Cloud API (Llama 3)</span>
                    </button>

                    <button
                      onClick={() => setProvider('ollama')}
                      className={`flex flex-col items-center justify-center p-4 rounded-xl border ${provider === 'ollama' ? 'border-ink bg-ink/5' : 'border-border bg-cream/30'} transition-all`}
                    >
                      <span className={`font-semibold ${provider === 'ollama' ? 'text-ink' : 'text-muted'}`}>Ollama</span>
                      <span className="text-xs text-muted mt-1">Local Inference (Llama 3)</span>
                    </button>
                  </div>
                </motion.div>

                {/* Credentials */}
                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="card-editorial p-6">
                  <h2 className="text-xl font-medium text-ink mb-6">Credentials</h2>
                  
                  <div className="space-y-6">
                    <div>
                      <label className="block text-sm font-medium text-ink mb-2">GitHub Personal Access Token (Optional)</label>
                      <p className="text-xs text-muted mb-3">Required for deep GitHub repository analysis. Leave blank to skip GitHub verification.</p>
                      <div className="flex gap-3">
                        <input
                          type={githubToken.includes('****') ? 'text' : 'password'}
                          value={githubToken}
                          onChange={(e) => setGithubToken(e.target.value)}
                          placeholder="ghp_..."
                          className="flex-1 rounded-lg border border-border bg-cream/30 px-4 py-2.5 text-sm outline-none focus:border-ink/30"
                        />
                        <button onClick={handleTestGithub} className="px-4 py-2 text-sm font-medium border border-border rounded-lg hover:bg-border/50 transition-colors">Test</button>
                      </div>
                    </div>

                    <div className="h-px bg-border my-2"></div>

                    {provider === 'groq' && (
                      <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}>
                        <label className="block text-sm font-medium text-ink mb-2">Groq API Key</label>
                        <p className="text-xs text-muted mb-3">Required for the Groq Cloud AI provider.</p>
                        <div className="flex gap-3">
                          <input
                            type={groqKey.includes('****') ? 'text' : 'password'}
                            value={groqKey}
                            onChange={(e) => setGroqKey(e.target.value)}
                            placeholder="gsk_..."
                            className="flex-1 rounded-lg border border-border bg-cream/30 px-4 py-2.5 text-sm outline-none focus:border-ink/30"
                          />
                          <button onClick={handleTestGroq} className="px-4 py-2 text-sm font-medium border border-border rounded-lg hover:bg-border/50 transition-colors">Test</button>
                        </div>
                      </motion.div>
                    )}

                    {provider === 'ollama' && (
                      <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}>
                        <label className="block text-sm font-medium text-ink mb-2">Ollama Base URL</label>
                        <p className="text-xs text-muted mb-3">The address where your local Ollama instance is running.</p>
                        <div className="flex gap-3">
                          <input
                            type="url"
                            value={ollamaUrl}
                            onChange={(e) => setOllamaUrl(e.target.value)}
                            placeholder="http://localhost:11434"
                            className="flex-1 rounded-lg border border-border bg-cream/30 px-4 py-2.5 text-sm outline-none focus:border-ink/30"
                          />
                          <button onClick={handleTestOllama} className="px-4 py-2 text-sm font-medium border border-border rounded-lg hover:bg-border/50 transition-colors">Test</button>
                        </div>
                      </motion.div>
                    )}
                  </div>
                </motion.div>

                <div className="flex justify-end pt-4">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleSave}
                    disabled={isSaving}
                    className="flex items-center gap-2 rounded-full bg-ink px-6 py-2.5 text-sm font-medium text-cream disabled:opacity-50"
                  >
                    <Save className="h-4 w-4" />
                    {isSaving ? 'Saving...' : 'Save Settings'}
                  </motion.button>
                </div>
              </div>
            )}
          </main>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-xl border border-border bg-white px-5 py-3.5 shadow-lg">
          {toast.type === 'success' ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <XCircle className="h-4 w-4 text-red-600" />}
          <p className="text-sm text-ink">{toast.msg}</p>
        </div>
      )}
    </div>
  )
}
