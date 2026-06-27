import { motion } from 'framer-motion'
import type { RankedCandidate } from '../lib/api'

interface Props {
  shortlist: RankedCandidate[]
  setShortlist: (s: RankedCandidate[]) => void
  onBack: () => void
  onSend: () => void
}

export default function Act5Shortlist({ shortlist, setShortlist, onBack, onSend }: Props) {
  const move = (from: number, to: number) => {
    if (to < 0 || to >= shortlist.length) return
    const next = [...shortlist]
    const [item] = next.splice(from, 1)
    next.splice(to, 0, item)
    setShortlist(next)
  }

  const remove = (idx: number) => {
    setShortlist(shortlist.filter((_, i) => i !== idx))
  }

  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen px-6 sm:px-12 py-12"
    >
      <div className="reading">
        <h2 className="font-serif text-heading">Your shortlist.</h2>
        <p className="mt-2 font-sans text-sm text-ink-tertiary">
          Drag to reorder priority. The people you'd forward.
        </p>

        <ul className="mt-10 space-y-3">
          {shortlist.map((c, i) => (
            <li
              key={c.candidate_id}
              className="p-4 bg-card border border-hairline rounded-lg flex items-center gap-4"
            >
              <div className="flex flex-col gap-0.5">
                <button
                  className="text-xs text-ink-tertiary hover:text-ink"
                  onClick={() => move(i, i - 1)}
                  aria-label="move up"
                >
                  ▲
                </button>
                <button
                  className="text-xs text-ink-tertiary hover:text-ink"
                  onClick={() => move(i, i + 1)}
                  aria-label="move down"
                >
                  ▼
                </button>
              </div>
              <div className="flex-1">
                <p className="font-serif text-lg text-ink">{c.name}</p>
                <p className="font-sans text-sm text-ink-secondary">
                  {c.current_title} · {c.current_company} · {c.location}
                </p>
              </div>
              <button
                onClick={() => remove(i)}
                className="text-xs text-ink-tertiary hover:text-signal-concern"
              >
                Remove
              </button>
            </li>
          ))}
          {shortlist.length === 0 && (
            <p className="font-serif italic text-ink-tertiary">
              No one shortlisted yet.
            </p>
          )}
        </ul>

        <div className="mt-12 flex items-center gap-6">
          <button
            onClick={onBack}
            className="font-sans text-base text-ink-secondary hover:text-ink transition-colors"
          >
            ← Keep going
          </button>
          <button
            onClick={onSend}
            disabled={shortlist.length === 0}
            className="font-sans text-base bg-action text-canvas px-6 py-3 rounded-full
                       hover:bg-ink disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Send shortlist
          </button>
        </div>
      </div>
    </motion.section>
  )
}
