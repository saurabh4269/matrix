import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'
import type { RankedCandidate } from '../lib/api'
import SNRSplit from '../components/SNRSplit'
import ShortlistCounter from '../components/ShortlistCounter'
import WhisperedHint from '../components/WhisperedHint'
import ProfileSheet from '../components/ProfileSheet'
import ConfidencePill from '../components/ConfidencePill'
import ScoreBreakdownBar from '../components/ScoreBreakdownBar'

interface Props {
  cand: RankedCandidate
  onInterview: () => void
  onNext: () => void
  onBack: () => void
  onOpenTuning?: () => void
  onOpenDashboard?: () => void
  shortlistCount: number
  position: number
  total: number
}

const REF_DATE = new Date('2026-06-01')

function daysSince(iso: string | null): number {
  if (!iso) return 9999
  const d = new Date(iso)
  if (isNaN(d.getTime())) return 9999
  return Math.round((REF_DATE.getTime() - d.getTime()) / 86_400_000)
}

function activeText(days: number): string {
  if (days <= 1) return 'active today'
  if (days <= 7) return 'active this week'
  if (days <= 30) return `active ${days}d ago`
  if (days <= 90) return `inactive ${Math.round(days / 30)}mo`
  return `dormant ${Math.round(days / 30)}mo`
}

function noticeText(days: number): string {
  if (days <= 30) return `${days}d notice`
  if (days <= 60) return `${days}d notice`
  if (days <= 90) return `${days}d notice`
  return `${days}d notice (slow)`
}

export default function Act2Deck({
  cand, onInterview, onNext, onBack, onOpenTuning, onOpenDashboard, shortlistCount, position, total,
}: Props) {
  const [showDetails, setShowDetails] = useState(false)
  const [showProfile, setShowProfile] = useState(false)

  useEffect(() => {
    setShowDetails(false)
    setShowProfile(false)
  }, [cand.candidate_id])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return
      if (e.key === 'Enter' || e.key.toLowerCase() === 'i') {
        e.preventDefault()
        onInterview()
      } else if (e.key === 'ArrowRight' || e.key === ' ' || e.key.toLowerCase() === 'k') {
        e.preventDefault()
        onNext()
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        onBack()
      } else if (e.key.toLowerCase() === 'd') {
        setShowDetails(s => !s)
      } else if (e.key.toLowerCase() === 'p') {
        setShowProfile(p => !p)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onInterview, onNext, onBack])

  const b = cand.behavioural
  const days = daysSince(b.last_active)
  const verified = b.verified_email && b.verified_phone && b.linkedin_connected
  const topConcern = cand.concerns[0]

  return (
    <motion.section
      key={cand.candidate_id}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="min-h-screen flex flex-col px-6 sm:px-12 py-8"
    >
      <ShortlistCounter count={shortlistCount} position={position} total={total} />

      <div className="reading flex-1 flex flex-col justify-center mt-6">
        {/* Identity */}
        <h2 className="font-serif text-display">
          {cand.name}
        </h2>
        <p className="mt-2 font-serif text-title text-ink-secondary">
          {cand.current_title} <span className="text-ink-tertiary">at</span> {cand.current_company}
        </p>

        {/* Confidence pill + rank CI: the single most glanceable trust signal */}
        <div className="mt-4">
          <ConfidencePill
            confidence={cand.confidence}
            currentRank={cand.rank}
            rankCi95={cand.rank_ci_95}
          />
        </div>

        {cand.whispered && <WhisperedHint />}

        {/* The verdict, calm, generous leading, prose-width */}
        <p className="mt-10 font-serif text-title text-ink max-w-[58ch]">
          {cand.reasoning}
        </p>

        {/* Honest concern, only if real */}
        {topConcern && (
          <p className="mt-4 font-serif text-body italic text-signal-concern">
            {topConcern.evidence}.
          </p>
        )}

        {/* Prescriptive next action — what the recruiter should actually do */}
        {cand.next_action && (
          <div className="mt-5 p-4 bg-card border-l-2 border-accent rounded-r">
            <p className="font-sans text-micro uppercase text-accent mb-1">
              Next action
            </p>
            <p className="font-serif text-body text-ink leading-snug">
              {cand.next_action}
            </p>
          </div>
        )}

        {/* Status row, compact and structured */}
        <div className="mt-8 flex flex-wrap items-center gap-x-4 gap-y-1 font-sans text-small text-ink-tertiary">
          {b.open_to_work && (
            <>
              <span className="text-signal-verified">Open to work</span>
              <span className="text-hairline">·</span>
            </>
          )}
          <span>{activeText(days)}</span>
          <span className="text-hairline">·</span>
          <span>{noticeText(b.notice_days)}</span>
          {verified && (
            <>
              <span className="text-hairline">·</span>
              <span className="text-signal-verified">verified</span>
            </>
          )}
        </div>

        {/* What's driving the score — horizontal stacked bar inspired by TellTale */}
        <ScoreBreakdownBar
          breakdown={cand.breakdown}
          behaviouralModifier={cand.behavioural.behav_modifier_total}
        />

        {/* Disclosure links */}
        <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-2 font-sans text-small text-ink-tertiary">
          <button
            onClick={() => setShowProfile(true)}
            className="hover:text-ink transition-colors duration-200 underline decoration-1 underline-offset-4 decoration-hairline hover:decoration-ink"
          >
            Read full profile
          </button>
          <button
            onClick={() => setShowDetails(s => !s)}
            className="hover:text-ink transition-colors duration-200"
          >
            {showDetails ? 'Hide details' : 'Show how this ranks'}
            <span className="ml-1">{showDetails ? '▴' : '▾'}</span>
          </button>
          {onOpenTuning && (
            <button
              onClick={onOpenTuning}
              className="hover:text-ink transition-colors duration-200"
              title="Adjust how the system weights signals (T)"
            >
              Tune ranking <span className="font-mono text-[11px] ml-0.5">T</span>
            </button>
          )}
          {onOpenDashboard && (
            <button
              onClick={onOpenDashboard}
              className="hover:text-ink transition-colors duration-200"
              title="See the whole ranking at a glance (O)"
            >
              Overview <span className="font-mono text-[11px] ml-0.5">O</span>
            </button>
          )}
        </div>

        <AnimatePresence>
          {showDetails && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="overflow-hidden"
            >
              <SNRSplit high={cand.snr_high} skills={cand.snr_low} />
              <BehaviouralBreakdown b={b} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <ProfileSheet cand={showProfile ? cand : null} onClose={() => setShowProfile(false)} />

      {/* Actions */}
      <div className="reading mt-10 flex items-center gap-6 pb-6">
        <button
          onClick={onInterview}
          className="font-sans text-body bg-action text-canvas px-8 py-3.5 rounded-full
                     hover:bg-ink transition-all duration-200
                     focus:outline-none focus:ring-2 focus:ring-action focus:ring-offset-2 focus:ring-offset-canvas"
        >
          Interview
        </button>
        <button
          onClick={onNext}
          className="font-sans text-body text-ink-secondary hover:text-ink transition-colors duration-200"
        >
          Next  →
        </button>
        <div className="ml-auto font-sans text-small text-ink-tertiary hidden md:flex items-center gap-3">
          <span><kbd>Enter</kbd> interview</span>
          <span className="text-hairline">·</span>
          <span><kbd>→</kbd> next</span>
          <span className="text-hairline">·</span>
          <span><kbd>P</kbd> profile</span>
        </div>
      </div>
    </motion.section>
  )
}

function BehaviouralBreakdown({ b }: { b: RankedCandidate['behavioural'] }) {
  return (
    <div className="mt-5 p-5 bg-card border border-hairline rounded-lg">
      <p className="font-sans text-xs uppercase tracking-widest text-ink-tertiary mb-4">
        Behavioural
      </p>
      <ul>
        {b.behav_breakdown.map(item => (
          <li
            key={item.name}
            className="flex items-baseline justify-between py-2 border-b border-hairline last:border-b-0"
          >
            <span className="font-sans text-sm text-ink">{prettyBehav(item.name)}</span>
            <span className="font-mono text-sm text-ink-secondary">{item.score.toFixed(2)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function prettyBehav(name: string): string {
  return ({
    effectively_available: 'Effectively available',
    notice_period_curve: 'Notice period',
    trust_modifier: 'Contact verification',
    engagement_quality: 'Engagement',
    closability: 'Offer-acceptance history',
  } as Record<string, string>)[name] ?? name
}
