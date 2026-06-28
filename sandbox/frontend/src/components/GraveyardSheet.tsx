import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'
import { fetchDiscarded, type DiscardedItem } from '../lib/api'

interface Props {
  open: boolean
  onClose: () => void
}

const PRETTY_RULE: Record<string, string> = {
  chronological_paradox: 'Chronological paradox',
  duration_exceeds_yoe: 'Career duration exceeds claimed years',
  single_role_exceeds_yoe: 'Single role exceeds claimed years',
  expert_with_zero_months: 'Expert at skills with 0 months experience',
  tenure_exceeds_company_age: 'Started at company before it existed',
  orphan_skill_assessments: 'Assessment scores for unclaimed skills',
  consulting_only: 'Consulting-only career',
  bigcorp_only: 'Bigcorp-only career',
  pure_research_career: 'Research-only background',
  no_production_code_18mo: 'No recent production code',
  framework_enthusiast: 'Framework-heavy, low production',
  title_chaser: 'Short tenures',
  cv_speech_robo_only: 'CV/speech focus, no NLP/IR',
  manager_drift: 'Manager-heavy recent roles',
  keyword_dense_junior: 'Keyword-dense for years of experience',
  remote_only_vs_hybrid_jd: 'Remote-only against hybrid JD',
  dilution: 'Mostly non-relevant tenure',
}

export default function GraveyardSheet({ open, onClose }: Props) {
  const [items, setItems] = useState<DiscardedItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    fetchDiscarded()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [open])

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  const honeypots = items.filter(i => i.discard_kind === 'honeypot')
  const heavyAnti = items.filter(i => i.discard_kind === 'heavy_anti_snr')

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
            className="fixed top-0 right-0 bottom-0 w-full max-w-[44rem] bg-canvas z-50 overflow-y-auto shadow-xl"
          >
            <div className="px-8 sm:px-12 py-10">
              <button
                onClick={onClose}
                className="font-sans text-small text-ink-tertiary hover:text-ink transition-colors"
              >
                Close <kbd className="font-mono text-[11px] ml-1">esc</kbd>
              </button>

              <h2 className="mt-8 font-serif text-display leading-[1.04]">
                Graveyard
              </h2>
              <p className="mt-2 font-sans text-small text-ink-tertiary">
                Candidates we filtered out, with the rule that fired. Kept visible for transparency.
              </p>

              {loading && (
                <p className="mt-12 font-serif text-title text-ink-tertiary">
                  Loading...
                </p>
              )}

              {!loading && items.length === 0 && (
                <p className="mt-12 font-serif text-title italic text-ink-tertiary">
                  Nothing filtered out in the demo set.
                </p>
              )}

              {honeypots.length > 0 && (
                <section className="mt-10">
                  <p className="font-sans text-micro uppercase text-ink-tertiary mb-4">
                    Honeypots quarantined ({honeypots.length})
                  </p>
                  <ul className="space-y-5">
                    {honeypots.map(item => (
                      <li key={item.candidate_id} className="border-l-2 border-signal-concern pl-5">
                        <p className="font-serif text-title text-ink">{item.name}</p>
                        <p className="font-sans text-small text-ink-secondary">
                          {item.current_title} <span className="text-ink-tertiary">at</span> {item.current_company}
                        </p>
                        <ul className="mt-2.5 space-y-1.5">
                          {item.rules_fired.map((r, i) => (
                            <li key={i} className="font-sans text-small text-ink-secondary">
                              <span className="text-signal-concern">●</span> {PRETTY_RULE[r.name] ?? r.name}
                              <span className="text-ink-tertiary"> — {r.evidence}</span>
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {heavyAnti.length > 0 && (
                <section className="mt-12 mb-16">
                  <p className="font-sans text-micro uppercase text-ink-tertiary mb-4">
                    Heavy anti-signal penalties ({heavyAnti.length})
                  </p>
                  <ul className="space-y-5">
                    {heavyAnti.map(item => (
                      <li key={item.candidate_id} className="border-l-2 border-hairline pl-5">
                        <p className="font-serif text-title text-ink">{item.name}</p>
                        <p className="font-sans text-small text-ink-secondary">
                          {item.current_title} <span className="text-ink-tertiary">at</span> {item.current_company}
                        </p>
                        <ul className="mt-2.5 space-y-1.5">
                          {item.rules_fired.map((r, i) => (
                            <li key={i} className="font-sans text-small text-ink-secondary">
                              <span className="text-signal-concern">●</span> {PRETTY_RULE[r.name] ?? r.name}
                              <span className="text-ink-tertiary"> — {r.evidence}</span>
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
