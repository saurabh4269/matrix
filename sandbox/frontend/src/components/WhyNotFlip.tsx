import { motion, AnimatePresence } from 'framer-motion'
import type { RankedCandidate } from '../lib/api'

interface Props {
  flipped: boolean
  onToggle: () => void
  cand: RankedCandidate
}

export default function WhyNotFlip({ flipped, onToggle, cand }: Props) {
  const whyNotText = cand.concerns.length > 0
    ? cand.concerns[0].evidence
    : cand.behavioural.notice_days > 60
    ? `${cand.behavioural.notice_days}-day notice, slow start.`
    : 'Few clear concerns. Strong choice.'

  return (
    <div className="mt-6">
      <button
        onClick={onToggle}
        className="font-sans text-sm text-accent hover:text-action transition-colors duration-200 underline decoration-1 underline-offset-4"
      >
        Tell me more.
      </button>
      <AnimatePresence>
        {flipped && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="mt-4 p-5 bg-card border-l-2 border-accent rounded-r">
              <p className="font-serif text-base text-ink-secondary italic leading-relaxed">
                {whyNotText}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
