import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
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

// Escape a token so it can be safely dropped into a regex character class.
function esc(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// Case-insensitive whole-word markup. Splits `text` into React nodes,
// wrapping any token that appears in `positiveTokens` (green) or
// `concernTokens` (concern-tone). Every wrap is a substring of the input,
// so nothing is invented — a highlighted phrase is guaranteed to be real
// text from the resume.
function highlight(
  text: string,
  positive: Set<string>,
  concern: Set<string>,
): React.ReactNode {
  if (!positive.size && !concern.size) return text
  // Build one big alternation. Longer tokens first so 'Machine Learning'
  // beats 'Learning' when both are matched.
  const all = [...positive, ...concern].sort((a, b) => b.length - a.length)
  if (!all.length) return text
  const pattern = new RegExp(`\\b(${all.map(esc).join('|')})\\b`, 'gi')
  const parts: React.ReactNode[] = []
  let cursor = 0
  let match: RegExpExecArray | null
  let idx = 0
  while ((match = pattern.exec(text)) !== null) {
    const before = text.slice(cursor, match.index)
    if (before) parts.push(before)
    const raw = match[0]
    const lower = raw.toLowerCase()
    // Concern beats positive on collision (e.g. a company name in both lists).
    const isConcern = [...concern].some(t => t.toLowerCase() === lower)
    const cls = isConcern
      ? 'bg-[#F5E6D8] text-signal-concern px-0.5 rounded-sm'
      : 'bg-[#E4EED2] text-[#3F4B2E] px-0.5 rounded-sm'
    parts.push(
      <mark key={`m-${idx++}`} className={cls}>{raw}</mark>
    )
    cursor = match.index + raw.length
  }
  const tail = text.slice(cursor)
  if (tail) parts.push(tail)
  return parts.length ? parts : text
}

export default function ProfileSheet({ cand, onClose }: Props) {
  const [highlightsOn, setHighlightsOn] = useState(true)

  useEffect(() => {
    if (!cand) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [cand, onClose])

  const posSet = useMemo(
    () => new Set((cand?.matched_tokens?.positive ?? []).map(t => t.toLowerCase())),
    [cand],
  )
  const conSet = useMemo(
    () => new Set((cand?.matched_tokens?.concern ?? []).map(t => t.toLowerCase())),
    [cand],
  )

  // Original-case token lookup (for the rendered highlights)
  const posOrig = useMemo(
    () => new Set(cand?.matched_tokens?.positive ?? []),
    [cand],
  )
  const conOrig = useMemo(
    () => new Set(cand?.matched_tokens?.concern ?? []),
    [cand],
  )

  const posCount = posSet.size
  const conCount = conSet.size

  const mark = (text: string) =>
    highlightsOn ? highlight(text, posOrig, conOrig) : text

  return (
    <AnimatePresence>
      {cand && (
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
              {/* Close + highlight toggle */}
              <div className="flex items-center justify-between">
                <button
                  onClick={onClose}
                  className="font-sans text-sm text-ink-tertiary hover:text-ink transition-colors"
                >
                  Close <kbd className="font-mono text-[11px] ml-1">esc</kbd>
                </button>
                {(posCount + conCount > 0) && (
                  <label className="flex items-center gap-2 font-sans text-small text-ink-tertiary cursor-pointer">
                    <input
                      type="checkbox"
                      checked={highlightsOn}
                      onChange={e => setHighlightsOn(e.target.checked)}
                      className="accent-action"
                    />
                    Highlight what we matched
                  </label>
                )}
              </div>

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

              {/* Model findings — Highlights + Concerns. Nothing here is
                  invented: every string comes from a probe evidence field. */}
              {((cand.snr_high?.length ?? 0) > 0 || (cand.concerns?.length ?? 0) > 0) && (
                <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
                  {(cand.snr_high?.length ?? 0) > 0 && (
                    <section className="p-4 bg-[#F1F6E5] border border-[#D6E1BF] rounded-lg">
                      <p className="font-sans text-[11px] uppercase tracking-[0.18em] text-[#3F4B2E] mb-2.5">
                        Highlights
                      </p>
                      <ul className="space-y-2">
                        {cand.snr_high!.slice(0, 5).map((h, i) => (
                          <li key={i} className="font-serif text-small text-ink leading-snug">
                            {h.evidence}
                            <span className="ml-1 font-mono text-[10px] text-ink-tertiary uppercase">
                              {h.name}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </section>
                  )}
                  {(cand.concerns?.length ?? 0) > 0 && (
                    <section className="p-4 bg-[#FAECDD] border border-[#EFD7BB] rounded-lg">
                      <p className="font-sans text-[11px] uppercase tracking-[0.18em] text-signal-concern mb-2.5">
                        Concerns
                      </p>
                      <ul className="space-y-2">
                        {cand.concerns!.slice(0, 4).map((c, i) => (
                          <li key={i} className="font-serif text-small text-ink leading-snug">
                            {c.evidence}
                            <span className="ml-1 font-mono text-[10px] text-ink-tertiary uppercase">
                              {c.name}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </section>
                  )}
                </div>
              )}

              {highlightsOn && (posCount + conCount > 0) && (
                <p className="mt-3 font-sans text-micro text-ink-tertiary italic">
                  Green = terms from the JD vocabulary we found verbatim in this profile.
                  Orange = flagged terms. Nothing highlighted is invented — toggle off to
                  read the raw resume.
                </p>
              )}

              {/* Headline (the candidate's own one-liner) */}
              {cand.headline && (
                <p className="mt-8 font-serif text-lg italic text-ink-secondary leading-snug max-w-[58ch]">
                  “{mark(cand.headline)}”
                </p>
              )}

              {/* Summary */}
              {cand.summary && (
                <section className="mt-10">
                  <p className="font-sans text-[11px] uppercase tracking-[0.18em] text-ink-tertiary mb-3">
                    Summary
                  </p>
                  <p className="font-serif text-lg leading-[1.7] text-ink max-w-[62ch]">
                    {mark(cand.summary)}
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
                          {mark(r.title)} <span className="text-ink-tertiary">at</span> {mark(r.company)}
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
                            {mark(r.description)}
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
                    {cand.snr_low.map((s, i) => {
                      const isMatched = highlightsOn && posSet.has(s.name.toLowerCase())
                      return (
                        <li
                          key={i}
                          className={`font-sans text-sm ${
                            isMatched ? 'text-[#3F4B2E]' : 'text-ink-secondary'
                          }`}
                        >
                          {isMatched ? (
                            <mark className="bg-[#E4EED2] px-0.5 rounded-sm">{s.name}</mark>
                          ) : s.name}
                          <span className="text-ink-tertiary text-xs">
                            {' '}· {s.proficiency} · {s.duration_months}mo
                          </span>
                          {s.verified && (
                            <span className="ml-1.5 text-signal-verified text-xs">✓</span>
                          )}
                        </li>
                      )
                    })}
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
