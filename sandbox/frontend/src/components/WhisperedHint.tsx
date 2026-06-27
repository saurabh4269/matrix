import { motion } from 'framer-motion'

export default function WhisperedHint() {
  return (
    <motion.p
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="mt-3 font-serif italic text-base text-accent"
    >
      Easy to overlook. Watch this one.
    </motion.p>
  )
}
