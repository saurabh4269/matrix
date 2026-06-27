import { motion } from 'framer-motion'
import type { JDDigest } from '../lib/api'

interface Props {
  jd: JDDigest | null
  onBegin: () => void
  error: string | null
}

const FALLBACK: JDDigest = {
  role: 'Senior AI Engineer.',
  location: 'Pune or Noida. Hybrid.',
  experience: 'Five to nine years.',
  style: 'Hands-on, not architect-only.',
  avoid: [
    'Consulting-only careers.',
    'Framework enthusiasts.',
    'Pure researchers without production.',
  ],
}

export default function Act1JDDigest({ jd, onBegin, error }: Props) {
  const digest = jd ?? FALLBACK

  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen flex flex-col justify-center px-6 sm:px-12"
    >
      <div className="reading">
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="font-serif text-display tracking-tight"
        >
          {digest.role}
        </motion.h1>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-10 space-y-3 font-serif text-2xl sm:text-3xl text-ink-secondary leading-snug"
        >
          <p>{digest.location}</p>
          <p>{digest.experience}</p>
          <p>{digest.style}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.55 }}
          className="mt-10 pt-6 border-t border-hairline"
        >
          <p className="font-sans text-sm uppercase tracking-widest text-ink-tertiary mb-3">
            Avoid
          </p>
          <ul className="font-serif text-xl text-ink-secondary space-y-1">
            {digest.avoid.map((a, i) => (
              <li key={i}>— {a}</li>
            ))}
          </ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.85 }}
          className="mt-16"
        >
          <button
            onClick={onBegin}
            className="font-sans text-base bg-action text-canvas px-6 py-3 rounded-full
                       hover:bg-ink transition-colors duration-200
                       focus:outline-none focus:ring-2 focus:ring-action focus:ring-offset-2 focus:ring-offset-canvas"
          >
            Show me who fits.
          </button>
          <p className="mt-4 font-sans text-sm text-ink-tertiary">
            <kbd className="font-mono text-xs">Enter</kbd> to begin
          </p>
        </motion.div>

        {error && (
          <p className="mt-6 text-sm text-signal-concern">{error}</p>
        )}
      </div>
    </motion.section>
  )
}
