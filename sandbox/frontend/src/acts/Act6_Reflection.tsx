import { motion } from 'framer-motion'

interface Props {
  shortlistCount: number
  fromTotal: number
  hoursSaved: number
  onRestart: () => void
}

export default function Act6Reflection({ shortlistCount, fromTotal, hoursSaved, onRestart }: Props) {
  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen flex items-center justify-center px-6"
    >
      <div className="reading">
        <motion.h2
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
          className="font-serif text-display leading-tight"
        >
          Done.
        </motion.h2>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.5 }}
          className="mt-6 font-serif text-2xl text-ink-secondary space-y-2"
        >
          <p>{shortlistCount} {shortlistCount === 1 ? 'candidate' : 'candidates'} from {fromTotal.toLocaleString()}.</p>
          <p>About {hoursSaved} {hoursSaved === 1 ? 'hour' : 'hours'} saved.</p>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.0, duration: 0.6 }}
          className="mt-10 font-serif italic text-lg text-accent border-l-2 border-accent pl-4"
        >
          You favoured production retrieval over framework familiarity.
          We'll remember.
        </motion.p>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.4, duration: 0.4 }}
          className="mt-12"
        >
          <button
            onClick={onRestart}
            className="font-sans text-base text-ink-secondary hover:text-ink transition-colors"
          >
            Start over
          </button>
        </motion.div>
      </div>
    </motion.section>
  )
}
