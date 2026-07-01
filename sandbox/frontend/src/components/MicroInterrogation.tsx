import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'
import type { RankedCandidate } from '../lib/api'
import type { UserWeights } from '../lib/rerank'

interface Props {
  cand: RankedCandidate | null
  kind: 'shortlist_override' | 'skip_override' | null
  onClose: () => void
  weights: UserWeights
  onAdjust: (next: UserWeights) => void
}

// Each reason maps to a small, bounded adjustment of one or two weights.
// The adjustments are designed to be visible but non-destructive: one click
// nudges a category by 10-15%. Multiple clicks compound.
interface Reason {
  id: string
  label: string
  adjust: (w: UserWeights) => UserWeights
}

const SHORTLIST_REASONS: Reason[] = [
  {
    id: 'domain_specific',
    label: 'Strong domain experience we missed',
    adjust: w => ({ ...w, substance: clamp(w.substance + 0.10, 0, 1.5) }),
  },
  {
    id: 'company_fit',
    label: 'Right company stage / culture match',
    adjust: w => ({ ...w, substance: clamp(w.substance + 0.05, 0, 1.5), location: clamp(w.location + 0.025, 0, 0.5) }),
  },
  {
    id: 'narrative',
    label: 'Project narrative resonates with our work',
    adjust: w => ({ ...w, substance: clamp(w.substance + 0.10, 0, 1.5), retrieval: clamp(w.retrieval - 0.025, 0, 1.0) }),
  },
  {
    id: 'availability_ok',
    label: 'Availability concerns are acceptable for this role',
    adjust: w => ({ ...w, behavioural_sensitivity: clamp(w.behavioural_sensitivity - 0.2, 0.3, 2.5) }),
  },
]

const SKIP_REASONS: Reason[] = [
  {
    id: 'pedigree_dependent',
    label: 'Too dependent on big-brand pedigree',
    adjust: w => ({ ...w, substance: clamp(w.substance + 0.10, 0, 1.5), must_have: clamp(w.must_have - 0.05, 0, 2.0) }),
  },
  {
    id: 'paper_only',
    label: 'Looks good on paper but lacks substance',
    adjust: w => ({ ...w, substance: clamp(w.substance + 0.15, 0, 1.5) }),
  },
  {
    id: 'wrong_stage',
    label: 'Wrong company stage / culture for us',
    adjust: w => ({ ...w, location: clamp(w.location + 0.05, 0, 0.5) }),
  },
  {
    id: 'unavailable',
    label: 'Realistically unavailable',
    adjust: w => ({ ...w, behavioural_sensitivity: clamp(w.behavioural_sensitivity + 0.3, 0.3, 2.5) }),
  },
]

function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v))
}

export default function MicroInterrogation({ cand, kind, onClose, weights, onAdjust }: Props) {
  const [selected, setSelected] = useState<string | null>(null)
  const [free, setFree] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (cand) {
      setSelected(null)
      setFree('')
      setSubmitting(false)
    }
  }, [cand])

  // Picking a reason IS the action. Auto-submit with a short visual beat so
  // the user sees the radio register before the modal slides out. If they
  // also typed free text, we wait for an explicit Submit so they don't lose
  // unsent text.
  const handleSelect = (id: string) => {
    setSelected(id)
    if (free.trim().length > 0) return  // wait for explicit Submit
    setSubmitting(true)
    window.setTimeout(() => {
      const reason = (kind === 'shortlist_override' ? SHORTLIST_REASONS : SKIP_REASONS).find(r => r.id === id)
      if (reason) onAdjust(reason.adjust(weights))
      onClose()
    }, 280)
  }

  useEffect(() => {
    if (!cand) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        e.preventDefault()
        onClose()
      } else if (e.key === 'Enter') {
        // Intercept Enter inside the modal so the deck's Enter handler
        // doesn't fire underneath. Submit if a reason is picked.
        if (e.target instanceof HTMLTextAreaElement) return
        e.stopPropagation()
        e.preventDefault()
        if (selected || free.trim().length > 0) {
          handleSubmit()
        }
      }
    }
    // capture-phase so we run BEFORE the deck's window-level handler
    window.addEventListener('keydown', handler, true)
    return () => window.removeEventListener('keydown', handler, true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cand, selected, free, onClose])

  const reasons = kind === 'shortlist_override' ? SHORTLIST_REASONS : SKIP_REASONS
  const isOverride = kind === 'shortlist_override'

  const handleSubmit = () => {
    if (!selected && !free) {
      onClose()
      return
    }
    if (selected) {
      const reason = reasons.find(r => r.id === selected)
      if (reason) onAdjust(reason.adjust(weights))
    }
    // Persist a contextual memory buffer of user-stated reasons.
    // vision.md's Track B: the system remembers qualitative feedback across
    // sessions so it can surface it next time. We don't change probe weights
    // from the free text; we just keep a log for the recruiter to see.
    if (free.trim().length > 0 && cand) {
      try {
        const KEY = 'matrix.memoryBuffer'
        const raw = window.localStorage.getItem(KEY) ?? '[]'
        const buffer = JSON.parse(raw) as Array<{ at: string; cand: string; kind: string; note: string }>
        buffer.push({
          at: new Date().toISOString(),
          cand: cand.name,
          kind: kind ?? 'note',
          note: free.trim(),
        })
        // Keep last 50 entries
        const trimmed = buffer.slice(-50)
        window.localStorage.setItem(KEY, JSON.stringify(trimmed))
      } catch {
        /* ignore — localStorage might be disabled */
      }
    }
    onClose()
  }

  return (
    <AnimatePresence>
      {cand && kind && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-ink/10 backdrop-blur-[2px] z-50"
            onClick={onClose}
          />

          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.2 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-lg px-4 max-h-[92vh]"
            onClick={e => e.stopPropagation()}
          >
            <div className="bg-canvas border border-hairline rounded-2xl p-6 shadow-2xl max-h-[92vh] overflow-y-auto">
              <p className="font-sans text-micro uppercase text-ink-tertiary mb-2">
                {isOverride ? 'Shortlisted against our rank' : 'Skipped a top pick'}
              </p>
              <h3 className="font-serif text-title text-ink leading-snug">
                {isOverride
                  ? `Interesting. What did we miss about ${cand.name}?`
                  : `Interesting. What stood out to you about ${cand.name} as a no?`}
              </h3>
              <p className="mt-1.5 font-sans text-small text-ink-tertiary leading-relaxed">
                Telling us why helps tune the ranking for your eye.
              </p>

              <ul className="mt-4 space-y-2">
                {reasons.map(r => {
                  const isSelected = selected === r.id
                  return (
                    <li key={r.id}>
                      <label
                        className={`flex items-start gap-3 cursor-pointer group rounded-lg px-3 py-2 transition-colors ${
                          isSelected ? 'bg-card border border-action' : 'border border-transparent hover:bg-card'
                        }`}
                      >
                        <input
                          type="radio"
                          name="interrogation"
                          value={r.id}
                          checked={isSelected}
                          onChange={() => handleSelect(r.id)}
                          disabled={submitting}
                          className="mt-1 accent-action"
                        />
                        <span className="font-sans text-body text-ink-secondary group-hover:text-ink transition-colors leading-snug">
                          {r.label}
                        </span>
                      </label>
                    </li>
                  )
                })}
                <li className="pt-1">
                  <label className="block font-sans text-small text-ink-tertiary">
                    Something else
                    <textarea
                      value={free}
                      onChange={e => setFree(e.target.value)}
                      rows={2}
                      placeholder="(optional, will be saved for next session)"
                      className="mt-1.5 w-full px-3 py-2 bg-card border border-hairline rounded font-sans text-small text-ink resize-none focus:outline-none focus:border-action"
                    />
                  </label>
                </li>
              </ul>

              <div className="mt-5 flex items-center gap-4">
                {/* Submit button only shown when there's free-text — radio
                    selection auto-submits, so a Submit button would be a
                    second confirmation the user doesn't need. */}
                {free.trim().length > 0 && (
                  <button
                    onClick={handleSubmit}
                    className="font-sans text-body bg-action text-canvas px-6 py-2.5 rounded-full
                               hover:bg-ink transition-all"
                  >
                    {selected ? 'Adjust ranking' : 'Submit note'}
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="font-sans text-body text-ink-tertiary hover:text-ink transition-colors ml-auto"
                >
                  Skip and continue
                </button>
              </div>

            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
