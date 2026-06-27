import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'

const PHRASES = [
  'Reading profiles.',
  'Listening for signal.',
  'Ready.',
]

export default function LoaderSequence() {
  const [i, setI] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setI(x => Math.min(x + 1, PHRASES.length - 1)), 600)
    return () => clearInterval(t)
  }, [])

  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen flex items-center justify-center px-6"
    >
      <AnimatePresence mode="wait">
        <motion.p
          key={i}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.3 }}
          className="font-serif text-3xl sm:text-4xl text-ink-secondary"
        >
          {PHRASES[i]}
        </motion.p>
      </AnimatePresence>
    </motion.section>
  )
}
