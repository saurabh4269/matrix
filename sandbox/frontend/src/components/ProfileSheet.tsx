import { motion, AnimatePresence } from 'framer-motion'
import { useEffect } from 'react'
import type { RankedCandidate } from '../lib/api'

interface Props {
  cand: RankedCandidate | null
  onClose: () => void
}

function fmtDate(iso: string | null, isCurrent: boolean): string {
  if (isCurrent) return 'present'
  if (!iso) return '–'
  return iso.slice(0, 7)
}

function durStr(months: number): string {
  const y = Math.floor(months / 12)
  const m = months % 12
  if (y === 0) return `${m}mo`
  if (m === 0) return `${y}y`
  return `${y}y ${m}mo`
}

export default function ProfileSheet({ cand, onClose }: Props) {
  // Esc to close
  useEffect(() => {
    if (!cand) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [cand, onClose])

  return (
    <AnimatePresence>
      {cand && (
        <>
          {/* Scrim */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-ink/10 backdrop-blur-[2px] z-40"
            onClick={onClose}
          />

          {/* Sheet */}
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 32, stiffness: 280 }}
            className="fixed top-0 right-0 bottom-0 w-full max-w-[44rem] bg-canvas z-50 overflow-y-auto shadow-xl"
          >
            <div className="px-8 sm:px-12 py-10">
              {/* Close */}
              <button
                onClick={onClose}
                className="font-sans text-sm text-ink-tertiary hover:text-ink transition-colors"
              >
                Close <kbd className="font-mono text-[11px] ml-1">esc</kbd>
              </button>

              {/* Identity */}
              <h2 className="mt-8 font-serif text-display leading-[1.04] tracking-tight">
                {cand.name}
              </h2>
              <p className="mt-2 font-serif text-xl text-ink-secondary">
                {cand.current_title} <span className="text-ink-tertiary">at</span>{' '}
                {cand.current_company}
              </p>
              <p className="mt-0.5 font-sans text-sm text-ink-tertiary">
                {cand.location} · {cand.years_of_experience.toFixed(1)} years
              </p>

              {/* Headline (the candidate's own one-liner) */}
              {cand.headline && (
                <p className="mt-8 font-serif text-lg italic text-ink-secondary leading-snug max-w-[58ch]">
                  “{cand.headline}”
                </p>
              )}

              {/* Summary */}
              {cand.summary && (
                <section className="mt-10">
                  <p className="font-sans text-[11px] uppercase tracking-[0.18em] text-ink-tertiary mb-3">
                    Summary
                  </p>
                  <p className="font-serif text-lg leading-[1.7] text-ink max-w-[62ch]">
                    {cand.summary}
                  </p>
                </section>
              )}

              {/* Experience */}
              {cand.career_history.length > 0 && (
                <section className="mt-12">
                  <p className="font-sans text-[11px] uppercase tracking-[0.18em] text-ink-tertiary mb-5">
                    Experience
                  </p>
                  <ol className="space-y-7">
                    {cand.career_history.map((r, i) => (
                      <li key={i} className="border-l-2 border-hairline pl-5">
                        <p className="font-serif text-lg text-ink leading-snug">
                          {r.title} <span className="text-ink-tertiary">at</span> {r.company}
                        </p>
                        <p className="mt-1 font-sans text-xs text-ink-tertiary">
                          {fmtDate(r.start_date, false)} – {fmtDate(r.end_date, r.is_current)}
                          {' · '}
                          {durStr(r.duration_months)}
                          {' · '}
                          {r.company_size}
                          {' · '}
                          {r.industry}
                        </p>
                        {r.description && (
                          <p className="mt-3 font-serif text-base leading-[1.65] text-ink-secondary max-w-[58ch]">
                            {r.description}
                          </p>
                        )}
                      </li>
                    ))}
                  </ol>
                </section>
              )}

              {/* Education */}
              {cand.education.length > 0 && (
                <section className="mt-12">
                  <p className="font-sans text-[11px] uppercase tracking-[0.18em] text-ink-tertiary mb-4">
                    Education
                  </p>
                  <ul className="space-y-3">
                    {cand.education.map((e, i) => (
                      <li key={i}>
                        <p className="font-serif text-base text-ink">
                          {e.degree} in {e.field_of_study}
                          <span className="text-ink-tertiary"> at </span>
                          {e.institution}
                        </p>
                        <p className="font-sans text-xs text-ink-tertiary mt-0.5">
                          {e.start_year}–{e.end_year}
                          {e.grade ? ` · ${e.grade}` : ''}
                        </p>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Certifications */}
              {cand.certifications.length > 0 && (
                <section className="mt-12">
                  <p className="font-sans text-[11px] uppercase tracking-[0.18em] text-ink-tertiary mb-4">
                    Certifications
                  </p>
                  <ul className="space-y-2">
                    {cand.certifications.map((c, i) => (
                      <li key={i} className="font-sans text-sm text-ink-secondary">
                        {c.name}
                        <span className="text-ink-tertiary"> · {c.issuer}</span>
                        {c.year && <span className="text-ink-tertiary"> · {c.year}</span>}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Skills - the full skills list for completeness */}
              {cand.snr_low.length > 0 && (
                <section className="mt-12 mb-16">
                  <p className="font-sans text-[11px] uppercase tracking-[0.18em] text-ink-tertiary mb-4">
                    Skills
                  </p>
                  <ul className="flex flex-wrap gap-x-5 gap-y-1.5">
                    {cand.snr_low.map((s, i) => (
                      <li key={i} className="font-sans text-sm text-ink-secondary">
                        {s.name}
                        <span className="text-ink-tertiary text-xs">
                          {' '}· {s.proficiency} · {s.duration_months}mo
                        </span>
                        {s.verified && (
                          <span className="ml-1.5 text-signal-verified text-xs">✓</span>
                        )}
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
