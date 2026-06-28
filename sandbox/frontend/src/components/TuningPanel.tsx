import { motion, AnimatePresence } from 'framer-motion'
import { useEffect } from 'react'
import { DEFAULT_WEIGHTS, type UserWeights } from '../lib/rerank'

interface Props {
  open: boolean
  onClose: () => void
  weights: UserWeights
  onChange: (w: UserWeights) => void
}

interface SliderSpec {
  key: keyof UserWeights
  label: string
  hint: string
  min: number
  max: number
  step: number
}

const SLIDERS: SliderSpec[] = [
  {
    key: 'must_have',
    label: 'Must-haves',
    hint: 'How much you weight the JD\'s explicit must-have probes.',
    min: 0, max: 2.0, step: 0.1,
  },
  {
    key: 'substance',
    label: 'Substance',
    hint: 'How much you trust description-text evidence over claimed skills.',
    min: 0, max: 1.5, step: 0.05,
  },
  {
    key: 'retrieval',
    label: 'Retrieval',
    hint: 'BM25 keyword overlap with the JD.',
    min: 0, max: 1.0, step: 0.05,
  },
  {
    key: 'location',
    label: 'Location',
    hint: 'Geography and willingness to relocate.',
    min: 0, max: 0.5, step: 0.025,
  },
  {
    key: 'behavioural_sensitivity',
    label: 'Availability sensitivity',
    hint: '1.0 = default. >1 punishes dormant candidates harder. <1 forgives them.',
    min: 0.3, max: 2.5, step: 0.1,
  },
]

export default function TuningPanel({ open, onClose, weights, onChange }: Props) {
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  const setOne = (key: keyof UserWeights, v: number) =>
    onChange({ ...weights, [key]: v })

  const resetAll = () => onChange({ ...DEFAULT_WEIGHTS })

  const isModified = (SLIDERS as SliderSpec[]).some(
    s => Math.abs(weights[s.key] - DEFAULT_WEIGHTS[s.key]) > 1e-6
  )

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-ink/10 backdrop-blur-[2px] z-40"
            onClick={onClose}
          />

          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 32, stiffness: 280 }}
            className="fixed top-0 right-0 bottom-0 w-full max-w-[28rem] bg-canvas z-50 overflow-y-auto shadow-xl"
          >
            <div className="px-8 py-10">
              <div className="flex items-center justify-between">
                <button
                  onClick={onClose}
                  className="font-sans text-small text-ink-tertiary hover:text-ink transition-colors"
                >
                  Close <kbd className="font-mono text-[11px] ml-1">esc</kbd>
                </button>
                {isModified && (
                  <button
                    onClick={resetAll}
                    className="font-sans text-small text-accent hover:text-action transition-colors"
                  >
                    Reset to defaults
                  </button>
                )}
              </div>

              <h2 className="mt-6 font-serif text-display leading-[1.04]">
                Tune.
              </h2>
              <p className="mt-2 font-sans text-small text-ink-tertiary leading-relaxed">
                Adjust how much each signal carries. The deck reranks live.
                Your choices save to this browser.
              </p>

              <div className="mt-10 space-y-7">
                {SLIDERS.map(s => (
                  <div key={s.key}>
                    <div className="flex items-baseline justify-between mb-1">
                      <label className="font-sans text-body text-ink font-medium">
                        {s.label}
                      </label>
                      <span className={`font-mono text-small ${
                        Math.abs(weights[s.key] - DEFAULT_WEIGHTS[s.key]) > 1e-6
                          ? 'text-accent' : 'text-ink-tertiary'
                      }`}>
                        {weights[s.key].toFixed(2)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={s.min}
                      max={s.max}
                      step={s.step}
                      value={weights[s.key]}
                      onChange={e => setOne(s.key, parseFloat(e.target.value))}
                      className="w-full accent-action"
                    />
                    <p className="font-sans text-small text-ink-tertiary mt-1.5 leading-snug">
                      {s.hint}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-12 p-4 bg-card border border-hairline rounded-lg">
                <p className="font-sans text-micro uppercase text-ink-tertiary mb-2">
                  How this works
                </p>
                <p className="font-serif text-small text-ink-secondary leading-relaxed">
                  Each slider reweights one category of the composite score.
                  We recompute every candidate's score in your browser and
                  re-sort, then we surface the new ranking immediately. The
                  submission CSV stays calibrated; only your live exploration
                  changes.
                </p>
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
