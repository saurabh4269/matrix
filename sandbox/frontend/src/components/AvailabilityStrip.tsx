import { motion } from 'framer-motion'
import { useState } from 'react'
import type { BehaviouralSnapshot } from '../lib/api'

interface Props {
  b: BehaviouralSnapshot
}

const REF_DATE = new Date('2026-06-01')

function daysSince(iso: string | null): string {
  if (!iso) return '–'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '–'
  const days = Math.round((REF_DATE.getTime() - d.getTime()) / (1000 * 60 * 60 * 24))
  if (days < 0) return 'today'
  if (days === 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 30) return `${days}d ago`
  if (days < 365) return `${Math.round(days / 30)}mo ago`
  return `${Math.round(days / 365)}y ago`
}

function noticeBand(days: number): { text: string; tone: 'good' | 'mid' | 'concern' } {
  if (days <= 30) return { text: `${days}d notice`, tone: 'good' }
  if (days <= 60) return { text: `${days}d notice`, tone: 'mid' }
  if (days <= 90) return { text: `${days}d notice`, tone: 'mid' }
  return { text: `${days}d notice`, tone: 'concern' }
}

function activityBand(days: number): 'good' | 'mid' | 'concern' {
  if (days < 0) return 'mid'
  if (days <= 14) return 'good'
  if (days <= 60) return 'mid'
  return 'concern'
}

const TONE_CLASS = {
  good: 'text-signal-verified',
  mid: 'text-ink-secondary',
  concern: 'text-signal-concern',
} as const

export default function AvailabilityStrip({ b }: Props) {
  const [expanded, setExpanded] = useState(false)

  const days = b.last_active
    ? Math.round((REF_DATE.getTime() - new Date(b.last_active).getTime()) / (1000 * 60 * 60 * 24))
    : 9999
  const activeTone = activityBand(days)
  const notice = noticeBand(b.notice_days)
  const verifyCount =
    Number(b.verified_email) + Number(b.verified_phone) + Number(b.linkedin_connected)
  const verifyGlyph = verifyCount === 3 ? '✓✓✓' : verifyCount === 2 ? '✓✓·' : verifyCount === 1 ? '✓··' : '···'

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35, delay: 0.1 }}
      className="mt-6"
    >
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 font-mono text-xs text-ink-tertiary">
        <span className={TONE_CLASS[activeTone]}>
          {b.open_to_work && '○ '}active {daysSince(b.last_active)}
        </span>
        <span className="text-hairline">·</span>
        <span>
          replies {Math.round(b.response_rate * 100)}% · {Math.round(b.response_time_hours)}h
        </span>
        <span className="text-hairline">·</span>
        <span className={TONE_CLASS[notice.tone]}>{notice.text}</span>
        <span className="text-hairline">·</span>
        <span>{b.applications_30d} apps/mo</span>
        <span className="text-hairline">·</span>
        <span className={verifyCount === 3 ? 'text-signal-verified' : 'text-ink-tertiary'}>
          {verifyGlyph}
        </span>
        <button
          onClick={() => setExpanded(e => !e)}
          className="text-ink-tertiary hover:text-ink underline decoration-1 underline-offset-4 ml-auto"
        >
          {expanded ? 'less' : 'how this affects rank'}
        </button>
      </div>

      {expanded && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-3 p-4 bg-card border border-hairline rounded text-sm font-sans"
        >
          <p className="text-xs uppercase tracking-widest text-ink-tertiary mb-2">
            behavioural modifier × {b.behav_modifier_total.toFixed(2)}
          </p>
          <ul className="space-y-1.5">
            {b.behav_breakdown.map(item => (
              <li key={item.name} className="text-ink-secondary leading-snug">
                <span className="text-ink font-medium">{prettyName(item.name)}</span>{' '}
                <span className="text-ink-tertiary">×{item.score.toFixed(2)}</span>
                <span className="block text-xs text-ink-tertiary mt-0.5">{item.evidence}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-ink-tertiary italic">
            Multiplicative, strong skills × unavailable behaviour ≈ zero.
          </p>
        </motion.div>
      )}
    </motion.div>
  )
}

function prettyName(name: string): string {
  return ({
    effectively_available: 'Effectively available',
    notice_period_curve: 'Notice period',
    trust_modifier: 'Contact verification',
    engagement_quality: 'Engagement',
    closability: 'Closability',
  } as Record<string, string>)[name] ?? name
}
