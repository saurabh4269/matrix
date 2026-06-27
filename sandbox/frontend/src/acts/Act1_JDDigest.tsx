import { motion } from 'framer-motion'
import { useEffect } from 'react'
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

  // Enter starts the journey
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return
      if (e.key === 'Enter') {
        e.preventDefault()
        onBegin()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onBegin])

  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen flex flex-col justify-center px-6 sm:px-12"
    >
      <div className="reading">
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
          className="font-sans text-micro uppercase text-ink-tertiary mb-5"
        >
          The job, as we heard it
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.1 }}
          className="font-serif text-display"
        >
          {digest.role}
        </motion.h1>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.32 }}
          className="mt-8 space-y-2 font-serif text-title text-ink-secondary max-w-[58ch]"
        >
          <p>{digest.location}</p>
          <p>{digest.experience}</p>
          <p>{digest.style}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.55 }}
          className="mt-10"
        >
          <p className="font-sans text-micro uppercase text-ink-tertiary mb-2">
            We will not move forward on
          </p>
          <ul className="font-serif text-title text-ink-secondary">
            {digest.avoid.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.85 }}
          className="mt-14 flex items-center gap-4"
        >
          <button
            onClick={onBegin}
            className="font-sans text-body bg-action text-canvas px-8 py-3.5 rounded-full
                       hover:bg-ink transition-all duration-200
                       focus:outline-none focus:ring-2 focus:ring-action focus:ring-offset-2 focus:ring-offset-canvas"
          >
            Show me who fits
          </button>
          <p className="font-sans text-small text-ink-tertiary">
            or press <kbd>Enter</kbd>
          </p>
        </motion.div>

        {error && (
          <p className="mt-5 font-sans text-small text-signal-concern">{error}</p>
        )}
      </div>
    </motion.section>
  )
}
