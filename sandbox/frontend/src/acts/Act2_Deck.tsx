import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import type { RankedCandidate } from '../lib/api'
import SNRSplit from '../components/SNRSplit'
import WhyNotFlip from '../components/WhyNotFlip'
import ShortlistCounter from '../components/ShortlistCounter'
import WhisperedHint from '../components/WhisperedHint'
import ConcernCallout from '../components/ConcernCallout'

interface Props {
  cand: RankedCandidate
  onInterview: () => void
  onNext: () => void
  onBack: () => void
  shortlistCount: number
  position: number
  total: number
}

export default function Act2Deck({
  cand, onInterview, onNext, onBack, shortlistCount, position, total,
}: Props) {
  const [flipped, setFlipped] = useState(false)

  useEffect(() => setFlipped(false), [cand.candidate_id])

  // Keyboard shortcuts: Enter/I = interview, ArrowRight/Space = next, ArrowLeft = back
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
      } else if (e.key.toLowerCase() === 'w') {
        setFlipped(f => !f)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onInterview, onNext, onBack])

  return (
    <motion.section
      key={cand.candidate_id}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="min-h-screen flex flex-col px-6 sm:px-12 py-10"
    >
      <ShortlistCounter count={shortlistCount} position={position} total={total} />

      <div className="reading flex-1 flex flex-col justify-center mt-8">
        <h2 className="font-serif text-display leading-none tracking-tight">
          {cand.name}
        </h2>
        <p className="mt-4 font-serif text-2xl text-ink-secondary">
          {cand.current_title} <span className="text-ink-tertiary">·</span>{' '}
          <span className="text-ink-tertiary">{cand.years_of_experience.toFixed(1)}y at</span>{' '}
          {cand.current_company}
        </p>
        <p className="mt-1 text-ink-tertiary text-sm">{cand.location}</p>

        {cand.whispered && <WhisperedHint />}

        <SNRSplit
          high={cand.snr_high}
          skills={cand.snr_low}
        />

        <p className="mt-8 font-serif text-xl leading-relaxed text-ink-secondary max-w-reading">
          {cand.reasoning}
        </p>

        {cand.concerns.length > 0 && (
          <ConcernCallout concerns={cand.concerns} />
        )}

        <WhyNotFlip
          flipped={flipped}
          onToggle={() => setFlipped(f => !f)}
          cand={cand}
        />
      </div>

      <div className="reading mt-12 flex items-center gap-6 pb-8">
        <button
          onClick={onInterview}
          className="font-sans text-base bg-action text-canvas px-7 py-3 rounded-full
                     hover:bg-ink transition-colors duration-200"
        >
          Interview
        </button>
        <button
          onClick={onNext}
          className="font-sans text-base text-ink-secondary hover:text-ink transition-colors duration-200"
        >
          Next →
        </button>
        <div className="ml-auto text-xs font-mono text-ink-tertiary hidden sm:block">
          <kbd>Enter</kbd> interview · <kbd>→</kbd> next · <kbd>←</kbd> back · <kbd>W</kbd> why-not
        </div>
      </div>
    </motion.section>
  )
}
