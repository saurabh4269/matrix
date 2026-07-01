// Single-screen overview, complementary to the deck flow.
// Trust header · ranked list sidebar · hero detail for the selected
// candidate (KPI cards, score breakdown, spider radar) · whitespace scatter
// of top 20 · graveyard link.

import { motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import type { JDDigest, RankedCandidate } from '../lib/api'
import ConfidencePill from '../components/ConfidencePill'
import GraveyardSheet from '../components/GraveyardSheet'
import KPICard from '../components/KPICard'
import ScoreBreakdownBar from '../components/ScoreBreakdownBar'
import SpiderRadar from '../components/SpiderRadar'
import WhitespaceScatter from '../components/WhitespaceScatter'

interface Props {
  jd: JDDigest
  candidates: RankedCandidate[]
  totalEvaluated: number
  onBackToDeck: () => void
}

function noticeBadge(days: number): string {
  if (days <= 30) return `${days}d notice`
  if (days <= 90) return `${days}d notice`
  return `${days}d (slow)`
}

export default function Dashboard({ jd, candidates, totalEvaluated, onBackToDeck }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(
    candidates[0]?.candidate_id ?? null
  )
  const [showGraveyard, setShowGraveyard] = useState(false)

  // Reset selection if the candidates list changes (e.g. user retuned weights).
  useEffect(() => {
    if (!selectedId && candidates[0]) setSelectedId(candidates[0].candidate_id)
    else if (selectedId && !candidates.find(c => c.candidate_id === selectedId)) {
      setSelectedId(candidates[0]?.candidate_id ?? null)
    }
  }, [candidates, selectedId])

  const selected = useMemo(
    () => candidates.find(c => c.candidate_id === selectedId) ?? candidates[0],
    [candidates, selectedId]
  )

  // Always render the header. Body falls back to a clear message if no data.
  const renderHeader = () => (
    <header className="flex items-center justify-between flex-wrap gap-y-3">
      <div className="flex items-center gap-3">
        <span className="font-serif text-title font-medium">matrix</span>
        <span className="font-sans text-micro uppercase text-signal-verified bg-[#E8F0E0] px-2 py-0.5 rounded">
          Live
        </span>
        <span className="font-sans text-small text-ink-tertiary">
          {jd?.role ? `· ${jd.role}` : ''}
        </span>
        <span className="font-sans text-small text-ink-tertiary">
          {jd?.location ? `· ${jd.location.split('.')[0]}` : ''}
        </span>
      </div>
      <div className="flex items-center gap-5 font-sans text-small text-ink-tertiary">
        <span>{(totalEvaluated || 0).toLocaleString()} candidates evaluated</span>
        <button
          onClick={onBackToDeck}
          className="text-action hover:text-ink transition-colors underline decoration-1 underline-offset-4"
        >
          Back to deck
        </button>
      </div>
    </header>
  )

  if (!selected) {
    return (
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        className="min-h-screen w-full px-6 sm:px-10 py-6"
      >
        {renderHeader()}
        <hr className="my-5 border-hairline" />
        <p className="mt-12 font-serif text-title text-ink-tertiary">
          No ranked candidates available yet. Press O or click Back to deck to return.
        </p>
      </motion.section>
    )
  }

  // Build spider radar from the candidate's structured signals.
  // Defensive against missing fields if the backend is stale.
  const bd = selected.breakdown ?? { must_have: 0, substance: 0, retrieval: 0, location: 0 }
  const radarAxes = [
    { label: 'Must-haves', value: bd.must_have ?? 0 },
    { label: 'Substance',  value: bd.substance ?? 0 },
    { label: 'Retrieval',  value: bd.retrieval ?? 0 },
    { label: 'Location',   value: bd.location  ?? 0 },
    { label: 'Available',  value: selected.behavioural?.behav_modifier_total ?? 0 },
  ]

  const verified = !!(selected.behavioural?.verified_email
    && selected.behavioural?.verified_phone
    && selected.behavioural?.linkedin_connected)

  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen w-full px-6 sm:px-10 py-6"
    >
      {/* Header */}
      {renderHeader()}

      <hr className="my-5 border-hairline" />

      {/* Two-column body: ranked list (left) + detail (right) */}
      <div className="grid grid-cols-1 lg:grid-cols-[18rem_1fr] gap-8">
        {/* Left: ranked list */}
        <aside>
          <p className="font-sans text-micro uppercase text-ink-tertiary mb-3">
            Ranked candidates
          </p>
          <ol className="space-y-0.5">
            {candidates.slice(0, 20).map(c => {
              const isSel = c.candidate_id === selected.candidate_id
              return (
                <li key={c.candidate_id}>
                  <button
                    onClick={() => setSelectedId(c.candidate_id)}
                    className={`w-full text-left flex items-center gap-3 px-2 py-1.5 rounded transition-colors ${
                      isSel ? 'bg-card border border-hairline' : 'hover:bg-card/60'
                    }`}
                  >
                    <span className="font-mono text-small text-ink-tertiary w-6 text-right">
                      {c.rank}
                    </span>
                    <span className="font-serif text-body text-ink truncate flex-1">
                      {c.name}
                    </span>
                    <span className="font-mono text-small text-ink-tertiary">
                      {(c.score ?? 0).toFixed(2)}
                    </span>
                  </button>
                </li>
              )
            })}
          </ol>
          <button
            onClick={() => setShowGraveyard(true)}
            className="mt-6 font-sans text-small text-ink-tertiary hover:text-ink transition-colors underline decoration-1 underline-offset-4 decoration-hairline"
          >
            See what we filtered out
          </button>
        </aside>

        {/* Right: hero detail panel */}
        <section>
          {/* Identity + confidence */}
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <h2 className="font-serif text-display leading-[1.04]">{selected.name}</h2>
              <p className="mt-1 font-serif text-title text-ink-secondary">
                {selected.current_title} <span className="text-ink-tertiary">at</span> {selected.current_company}
              </p>
              <p className="mt-0.5 font-sans text-small text-ink-tertiary">
                {selected.location} · {(selected.years_of_experience ?? 0).toFixed(1)}y total
              </p>
            </div>
            <ConfidencePill confidence={selected.confidence} />
          </div>

          {/* KPI cards row */}
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-3">
            <KPICard
              label="Rank"
              value={`#${selected.rank}`}
              tone={selected.rank <= 5 ? 'accent' : 'default'}
            />
            <KPICard
              label="Match score"
              value={(selected.score ?? 0).toFixed(2)}
            />
            <KPICard
              label="Notice"
              value={noticeBadge(selected.behavioural?.notice_days ?? 30)}
              tone={(selected.behavioural?.notice_days ?? 30) > 60 ? 'concern' : 'default'}
            />
            <KPICard
              label="Trust"
              value={verified ? 'verified' : 'partial'}
              sublabel={selected.behavioural?.open_to_work ? 'open to work' : undefined}
              tone={verified ? 'accent' : 'default'}
            />
          </div>

          {/* Reasoning */}
          <p className="mt-7 font-serif text-title text-ink leading-relaxed max-w-[62ch]">
            {selected.reasoning}
          </p>

          {/* Next action + main risk side by side */}
          {(selected.next_action || selected.main_risk) && (
            <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-3">
              {selected.next_action && (
                <div className="p-4 bg-card border-l-2 border-accent rounded-r">
                  <p className="font-sans text-micro uppercase text-accent mb-1.5">
                    Next action
                  </p>
                  <p className="font-serif text-body text-ink leading-snug">
                    {selected.next_action}
                  </p>
                </div>
              )}
              {selected.main_risk && (
                <div className="p-4 bg-card border-l-2 border-signal-concern rounded-r">
                  <p className="font-sans text-micro uppercase text-signal-concern mb-1.5">
                    Main risk
                  </p>
                  <p className="font-serif text-body text-ink leading-snug">
                    {selected.main_risk}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Why not ranked higher — honest ceiling notes */}
          {(selected.why_not_higher?.length ?? 0) > 0 && (
            <div className="mt-3 p-4 bg-card border-l-2 border-hairline rounded-r">
              <p className="font-sans text-micro uppercase text-ink-tertiary mb-1.5">
                Why not ranked higher
              </p>
              <ul className="font-serif text-body text-ink-secondary leading-snug space-y-1">
                {selected.why_not_higher!.map((line, i) => (
                  <li key={i} className="pl-3 border-l border-hairline">{line}</li>
                ))}
              </ul>
            </div>
          )}

          {/* HRMS routing chip — small production-readiness signal */}
          {selected.hrms_routing_action && (
            <div className="mt-3 flex flex-wrap items-center gap-2 font-sans text-micro text-ink-tertiary">
              <span className="uppercase">HRMS route</span>
              <span className="text-hairline">·</span>
              <code className="font-mono text-[11px] bg-card px-2 py-0.5 rounded border border-hairline">
                {selected.hrms_routing_action.next_step}
              </code>
              {selected.hrms_routing_action.assessment_id && (
                <>
                  <span className="text-hairline">·</span>
                  <code className="font-mono text-[11px]">
                    {selected.hrms_routing_action.assessment_id}
                  </code>
                </>
              )}
              <span className="text-hairline">·</span>
              <span>SLA {selected.hrms_routing_action.sla_hours}h</span>
            </div>
          )}

          {/* Score breakdown bar */}
          <ScoreBreakdownBar
            breakdown={bd}
            behaviouralModifier={selected.behavioural?.behav_modifier_total ?? 1.0}
          />

          {/* Spider radar + concerns */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            <div>
              <p className="font-sans text-micro uppercase text-ink-tertiary mb-3">
                Fit dimensions
              </p>
              <SpiderRadar axes={radarAxes} size={260} />
            </div>
            <div>
              <p className="font-sans text-micro uppercase text-ink-tertiary mb-3">
                {(selected.concerns?.length ?? 0) > 0 ? 'Concerns' : 'Strengths'}
              </p>
              {(selected.concerns?.length ?? 0) > 0 ? (
                <ul className="space-y-2.5">
                  {selected.concerns.map((c, i) => (
                    <li key={i} className="font-serif text-body text-signal-concern leading-snug">
                      {c.evidence}
                    </li>
                  ))}
                </ul>
              ) : (
                <ul className="space-y-2.5">
                  {(selected.snr_high ?? []).slice(0, 4).map((h, i) => (
                    <li key={i} className="font-serif text-body text-ink-secondary leading-snug">
                      {h.evidence}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Whitespace scatter */}
          <div className="mt-10">
            <p className="font-sans text-micro uppercase text-ink-tertiary mb-3">
              Top 20 · must-haves × availability
            </p>
            <WhitespaceScatter
              candidates={candidates}
              selectedId={selected.candidate_id}
              onSelect={setSelectedId}
              size={520}
            />
          </div>
        </section>
      </div>

      <GraveyardSheet open={showGraveyard} onClose={() => setShowGraveyard(false)} />
    </motion.section>
  )
}
