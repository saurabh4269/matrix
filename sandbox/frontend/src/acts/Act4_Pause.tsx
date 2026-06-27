import { motion } from 'framer-motion'

interface Props {
  shortlistCount: number
  onContinue: () => void
  onReview: () => void
}

export default function Act4Pause({ shortlistCount, onContinue, onReview }: Props) {
  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen flex items-center justify-center px-6"
    >
      <div className="reading text-center">
        <motion.h2
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
          className="font-serif text-display text-ink leading-tight"
        >
          Take a breath.
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.35, duration: 0.5 }}
          className="mt-4 font-serif text-2xl text-ink-secondary"
        >
          Shortlist of {shortlistCount}.
        </motion.p>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.5 }}
          className="mt-10 flex items-center justify-center gap-8"
        >
          <button
            onClick={onContinue}
            className="font-sans text-base text-ink-secondary hover:text-ink transition-colors"
          >
            Keep going
          </button>
          <button
            onClick={onReview}
            className="font-sans text-base bg-action text-canvas px-6 py-3 rounded-full hover:bg-ink transition-colors"
          >
            See shortlist →
          </button>
        </motion.div>
      </div>
    </motion.section>
  )
}
