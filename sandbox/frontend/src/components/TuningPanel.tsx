import { motion, AnimatePresence } from 'framer-motion'
import { useEffect } from 'react'
import { DEFAULT_WEIGHTS, type UserWeights } from '../lib/rerank'

interface Props {
  open: boolean
  onClose: () => void
  weights: UserWeights
  onChange: (w: UserWeights) => void
  jdDisplayName?: string
}

interface Tier {
  max: number       // upper bound of this tier (inclusive)
  label: string     // short name, shown in the slider's value chip
  description: string  // one-liner that appears under the slider
}

interface SliderSpec {
  key: keyof UserWeights
  label: string             // slider title
  question: string          // the *question this slider answers* (JD framing)
  min: number
  max: number
  step: number
  leftAnchor: string        // shown under the slider on the left
  rightAnchor: string       // shown under the slider on the right
  tiers: Tier[]             // ordered ascending by `max`
}

// Each slider maps to a JD-facing question, not a math coefficient.
const SLIDERS: SliderSpec[] = [
  {
    key: 'must_have',
    label: 'Must-haves',
    question: 'How strictly should the JD\'s must-haves count?',
    min: 0, max: 2.0, step: 0.1,
    leftAnchor: 'flexible',
    rightAnchor: 'hard-line',
    tiers: [
      { max: 0.4, label: 'loose',     description: 'Adjacent-skill candidates can rank high. Good for scarce roles.' },
      { max: 0.9, label: 'flexible',  description: 'Some must-haves optional. Broader top of funnel.' },
      { max: 1.2, label: 'balanced',  description: 'Default. Must-haves matter but don\'t dominate.' },
      { max: 1.6, label: 'strict',    description: 'Missing a must-have costs you real rank.' },
      { max: 2.0, label: 'hard-line', description: 'Every must-have has to fire clearly.' },
    ],
  },
  {
    key: 'substance',
    label: 'Substance over claims',
    question: 'Do you trust claimed skills, or want proof in the descriptions?',
    min: 0, max: 1.5, step: 0.05,
    leftAnchor: 'trust the claims',
    rightAnchor: 'prove it',
    tiers: [
      { max: 0.2, label: 'trust claims',    description: 'Take the profile at face value. Fast, but fooled by AI-tailored resumes.' },
      { max: 0.5, label: 'some evidence',   description: 'Skills carry, but a bare description hurts.' },
      { max: 0.8, label: 'prefer evidence', description: 'Default. Descriptions should back up the skill list.' },
      { max: 1.2, label: 'demand evidence', description: 'Sparse descriptions push the candidate down.' },
      { max: 1.5, label: 'prove it',        description: 'Claimed-only skills are worth almost nothing.' },
    ],
  },
  {
    key: 'retrieval',
    label: 'Keyword match',
    question: 'How much should JD-keyword overlap count?',
    min: 0, max: 1.0, step: 0.05,
    leftAnchor: 'ignore keywords',
    rightAnchor: 'lean on keywords',
    tiers: [
      { max: 0.1, label: 'off',         description: 'Keywords ignored entirely.' },
      { max: 0.3, label: 'light',       description: 'Default. Keywords are a small tie-breaker.' },
      { max: 0.6, label: 'moderate',    description: 'JD terminology matters.' },
      { max: 1.0, label: 'heavy',       description: 'Big keyword-overlap candidates surface fast.' },
    ],
  },
  {
    key: 'location',
    label: 'Location fit',
    question: 'How important is geographic match?',
    min: 0, max: 0.5, step: 0.025,
    leftAnchor: 'anywhere',
    rightAnchor: 'must be local',
    tiers: [
      { max: 0.05, label: 'anywhere',           description: 'Location doesn\'t affect rank.' },
      { max: 0.15, label: 'slight preference',  description: 'Default. Local candidates get a small bump.' },
      { max: 0.3,  label: 'strong preference',  description: 'Remote candidates lose ground.' },
      { max: 0.5,  label: 'location-critical',  description: 'Non-local = big penalty.' },
    ],
  },
  {
    key: 'behavioural_sensitivity',
    label: 'Availability sensitivity',
    question: 'How harshly should dormant / slow-notice candidates be penalised?',
    min: 0.3, max: 2.5, step: 0.1,
    leftAnchor: 'forgive dormancy',
    rightAnchor: 'active only',
    tiers: [
      { max: 0.6,  label: 'very forgiving',    description: 'Dormant, unresponsive candidates still surface.' },
      { max: 0.9,  label: 'forgiving',         description: 'Give the sleeper picks a chance.' },
      { max: 1.15, label: 'balanced',          description: 'Default. Availability nudges, doesn\'t dominate.' },
      { max: 1.6,  label: 'prefer active',     description: 'Currently-active candidates rank noticeably higher.' },
      { max: 2.5,  label: 'active only',       description: 'Anyone dormant is effectively out.' },
    ],
  },
]

function tierAt(spec: SliderSpec, value: number): Tier {
  for (const t of spec.tiers) {
    if (value <= t.max) return t
  }
  return spec.tiers[spec.tiers.length - 1]
}

export default function TuningPanel({ open, onClose, weights, onChange, jdDisplayName }: Props) {
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

  const isModified = SLIDERS.some(
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
            className="fixed top-0 right-0 bottom-0 w-full max-w-[30rem] bg-canvas z-50 overflow-y-auto shadow-xl"
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

              <p className="mt-6 font-sans text-micro uppercase text-ink-tertiary">
                Tuning for {jdDisplayName ?? 'this JD'}
              </p>
              <h2 className="mt-1 font-serif text-display leading-[1.04]">
                What matters here?
              </h2>
              <p className="mt-2 font-sans text-small text-ink-tertiary leading-relaxed max-w-[38ch]">
                Each choice reweights the ranking for this role. The deck reranks live,
                and your settings stick per-JD.
              </p>

              <div className="mt-10 space-y-10">
                {SLIDERS.map(s => {
                  const val = weights[s.key]
                  const tier = tierAt(s, val)
                  const isDefault = Math.abs(val - DEFAULT_WEIGHTS[s.key]) < 1e-6
                  return (
                    <div key={s.key}>
                      <p className="font-sans text-micro uppercase text-ink-tertiary">
                        {s.label}
                      </p>
                      <p className="mt-1 font-serif text-body text-ink leading-snug max-w-[36ch]">
                        {s.question}
                      </p>
                      <div className="mt-3 flex items-baseline gap-3">
                        <span className={`font-serif text-title font-medium ${
                          isDefault ? 'text-ink' : 'text-accent'
                        }`}>
                          {tier.label}
                        </span>
                        {!isDefault && (
                          <span className="font-sans text-micro uppercase text-accent">
                            adjusted
                          </span>
                        )}
                      </div>
                      <input
                        type="range"
                        min={s.min}
                        max={s.max}
                        step={s.step}
                        value={val}
                        onChange={e => setOne(s.key, parseFloat(e.target.value))}
                        className="w-full accent-action mt-3"
                        aria-label={s.label}
                      />
                      <div className="flex justify-between font-sans text-micro text-ink-tertiary mt-1">
                        <span>{s.leftAnchor}</span>
                        <span>{s.rightAnchor}</span>
                      </div>
                      <p className="mt-3 font-sans text-small text-ink-secondary leading-snug">
                        {tier.description}
                      </p>
                    </div>
                  )
                })}
              </div>

              <div className="mt-14 p-4 bg-card border border-hairline rounded-lg">
                <p className="font-sans text-micro uppercase text-ink-tertiary mb-2">
                  How this works
                </p>
                <p className="font-serif text-small text-ink-secondary leading-relaxed">
                  Each choice reweights one category of the composite score.
                  We recompute every candidate's score in your browser and
                  re-sort, then we surface the new ranking immediately. The
                  submission CSV stays calibrated to the JD defaults; your
                  exploration doesn't touch it.
                </p>
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
