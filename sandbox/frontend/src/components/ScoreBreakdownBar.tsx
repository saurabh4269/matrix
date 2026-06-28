import { motion } from 'framer-motion'
import type { ScoreBreakdown } from '../lib/api'

interface Props {
  breakdown: ScoreBreakdown
  behaviouralModifier: number
}

const LABELS: Record<keyof ScoreBreakdown, string> = {
  must_have: 'Must-haves',
  substance: 'Substance',
  retrieval: 'Retrieval',
  location:  'Location',
}

const COLORS: Record<keyof ScoreBreakdown, string> = {
  must_have: 'bg-[#1F2933]',   // primary ink — the heaviest signal
  substance: 'bg-[#B8843B]',   // ochre accent — the trust signal
  retrieval: 'bg-[#5A5A5A]',   // mid gray
  location:  'bg-[#C9C2B1]',   // pale beige — the lightest contribution
}

export default function ScoreBreakdownBar({ breakdown, behaviouralModifier }: Props) {
  // Filter out zero contributions for a cleaner bar.
  const entries = (Object.keys(LABELS) as (keyof ScoreBreakdown)[])
    .map(k => ({ key: k, pct: Math.round((breakdown[k] || 0) * 100) }))
    .filter(e => e.pct > 0)

  return (
    <div className="mt-6">
      <div className="flex items-baseline justify-between mb-2">
        <p className="font-sans text-micro uppercase text-ink-tertiary">
          What's driving the score
        </p>
        <p className="font-sans text-small text-ink-tertiary">
          × {behaviouralModifier.toFixed(2)} availability
        </p>
      </div>

      {/* Horizontal stacked bar */}
      <div className="flex h-2.5 rounded-full overflow-hidden bg-hairline">
        {entries.map(({ key, pct }) => (
          <motion.div
            key={key}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.45, ease: 'easeOut' }}
            className={`${COLORS[key]} h-full`}
            title={`${LABELS[key]}: ${pct}%`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1 font-sans text-small text-ink-tertiary">
        {entries.map(({ key, pct }) => (
          <span key={key} className="inline-flex items-center">
            <span className={`inline-block w-2 h-2 rounded-sm ${COLORS[key]} mr-1.5`} />
            {LABELS[key]} · {pct}%
          </span>
        ))}
      </div>
    </div>
  )
}
