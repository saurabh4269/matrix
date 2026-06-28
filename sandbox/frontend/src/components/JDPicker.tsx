// Sheet that lets the recruiter switch the active JD or paste a brand new one.
// Lives behind the "Change JD" link on the arrival screen.
//
// Two paths:
//   1. Pick a pre-built JD from jds/*.yaml (one POST /api/jd/select).
//   2. Paste raw JD text and let the LLM bootstrap a YAML for it
//      (one POST /api/jd/bootstrap — takes ~15-30s for the model call).

import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'
import {
  bootstrapJd,
  listJds,
  selectJd,
  type JdListItem,
  type JDDigest,
} from '../lib/api'

interface Props {
  open: boolean
  onClose: () => void
  onJdChanged: (digest: JDDigest) => void
}

export default function JDPicker({ open, onClose, onJdChanged }: Props) {
  const [jds, setJds] = useState<JdListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)  // slug being switched/bootstrapped
  const [error, setError] = useState<string | null>(null)
  const [customText, setCustomText] = useState('')
  const [customName, setCustomName] = useState('')
  const [bootstrapping, setBootstrapping] = useState(false)

  // Lazy-load on open
  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError(null)
    listJds()
      .then(d => setJds(d.jds))
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [open])

  const handlePick = async (item: JdListItem) => {
    if (item.is_active) { onClose(); return }
    setBusy(item.name)
    setError(null)
    try {
      const r = await selectJd(item.name)
      onJdChanged(r.digest)
      onClose()
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(null)
    }
  }

  const handleBootstrap = async () => {
    if (customText.trim().length < 80) {
      setError('Paste at least a few lines of the JD.')
      return
    }
    setBootstrapping(true)
    setError(null)
    try {
      const r = await bootstrapJd(customText, customName || undefined)
      onJdChanged(r.digest)
      setCustomText('')
      setCustomName('')
      onClose()
    } catch (e) {
      setError(String(e))
    } finally {
      setBootstrapping(false)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-ink/15 backdrop-blur-[2px] z-40"
            onClick={onClose}
          />

          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="fixed top-0 right-0 bottom-0 z-50 w-full max-w-xl bg-canvas border-l border-hairline shadow-2xl overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-8">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-sans text-micro uppercase text-ink-tertiary mb-2">
                    Job description
                  </p>
                  <h2 className="font-serif text-title text-ink">
                    Choose, or paste your own.
                  </h2>
                </div>
                <button
                  onClick={onClose}
                  className="font-sans text-small text-ink-tertiary hover:text-ink transition-colors"
                  title="Close"
                >
                  Close
                </button>
              </div>

              <p className="mt-2 font-sans text-small text-ink-tertiary max-w-[52ch] leading-relaxed">
                The ranker is JD-agnostic. Every probe, weight, and vocabulary
                lives in <span className="font-mono">jds/*.yaml</span>. Swap the
                YAML, retarget the role.
              </p>

              {loading && (
                <p className="mt-8 font-sans text-small text-ink-tertiary">Loading…</p>
              )}

              {!loading && jds.length > 0 && (
                <section className="mt-8">
                  <p className="font-sans text-micro uppercase text-ink-tertiary mb-3">
                    Pre-built
                  </p>
                  <ul className="space-y-3">
                    {jds.map(j => (
                      <li key={j.name}>
                        <button
                          onClick={() => handlePick(j)}
                          disabled={busy !== null}
                          className={`w-full text-left p-4 rounded-lg border transition-colors ${
                            j.is_active
                              ? 'border-action bg-card'
                              : 'border-hairline hover:border-ink-secondary hover:bg-card/60'
                          } disabled:opacity-50 disabled:cursor-wait`}
                        >
                          <div className="flex items-baseline justify-between">
                            <h3 className="font-serif text-body text-ink">
                              {j.display_name}
                            </h3>
                            {j.is_active && (
                              <span className="font-sans text-micro uppercase text-accent">
                                Active
                              </span>
                            )}
                            {busy === j.name && (
                              <span className="font-sans text-micro text-ink-tertiary">
                                Switching…
                              </span>
                            )}
                          </div>
                          <p className="mt-1 font-sans text-small text-ink-tertiary">
                            {j.digest.location} · {j.digest.experience}
                          </p>
                          <p className="mt-1 font-sans text-small text-ink-tertiary italic">
                            {j.digest.style}
                          </p>
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <section className="mt-10">
                <p className="font-sans text-micro uppercase text-ink-tertiary mb-3">
                  Paste your own
                </p>
                <p className="font-sans text-small text-ink-tertiary mb-4 max-w-[52ch] leading-relaxed">
                  We'll extract the role, location, must-haves, and anti-patterns
                  via an LLM call and save a starter YAML. Takes about 15-30 seconds.
                </p>
                <label className="block">
                  <span className="font-sans text-small text-ink-tertiary">Role slug (optional)</span>
                  <input
                    type="text"
                    value={customName}
                    onChange={e => setCustomName(e.target.value)}
                    placeholder="e.g. backend_engineer"
                    disabled={bootstrapping}
                    className="mt-1 w-full px-3 py-2 bg-card border border-hairline rounded font-sans text-small text-ink focus:outline-none focus:border-action disabled:opacity-50"
                  />
                </label>
                <label className="block mt-3">
                  <span className="font-sans text-small text-ink-tertiary">JD text</span>
                  <textarea
                    value={customText}
                    onChange={e => setCustomText(e.target.value)}
                    rows={10}
                    placeholder="Paste the full JD here, ideally including 'Responsibilities', 'Required', and 'Nice to have' sections."
                    disabled={bootstrapping}
                    className="mt-1 w-full px-3 py-2 bg-card border border-hairline rounded font-sans text-small text-ink focus:outline-none focus:border-action disabled:opacity-50 resize-y"
                  />
                </label>
                <div className="mt-4 flex items-center gap-4">
                  <button
                    onClick={handleBootstrap}
                    disabled={bootstrapping || customText.trim().length < 80}
                    className="font-sans text-body bg-action text-canvas px-5 py-2.5 rounded-full
                               hover:bg-ink disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                  >
                    {bootstrapping ? 'Bootstrapping JD…' : 'Bootstrap & activate'}
                  </button>
                  {bootstrapping && (
                    <p className="font-serif italic text-small text-accent">
                      Extracting fields with Claude Haiku, then validating the YAML…
                    </p>
                  )}
                </div>
              </section>

              {error && (
                <p className="mt-6 font-sans text-small text-signal-concern max-w-[52ch] leading-snug">
                  {error}
                </p>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
