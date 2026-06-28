import { motion } from 'framer-motion'
import { useMemo, useState } from 'react'
import type { RankedCandidate } from '../lib/api'
import GraveyardSheet from '../components/GraveyardSheet'

interface Props {
  shortlistCount: number
  fromTotal: number
  hoursSaved: number
  shortlist: RankedCandidate[]
  skipped: RankedCandidate[]
  onRestart: () => void
}

// Derive a single "what you implicitly favoured" sentence from the user's
// shortlist vs skipped composition. We compare the average breakdown of
// shortlisted candidates to the average breakdown of skipped candidates and
// surface the dimension with the biggest delta.
function reflectionFromBehaviour(
  shortlist: RankedCandidate[],
  skipped: RankedCandidate[],
): string | null {
  if (shortlist.length < 2 || skipped.length < 2) return null

  const avg = (cs: RankedCandidate[]) => {
    const acc = { must_have: 0, substance: 0, retrieval: 0, location: 0 }
    for (const c of cs) {
      acc.must_have += c.breakdown.must_have ?? 0
      acc.substance += c.breakdown.substance ?? 0
      acc.retrieval += c.breakdown.retrieval ?? 0
      acc.location += c.breakdown.location ?? 0
    }
    const n = cs.length
    return {
      must_have: acc.must_have / n,
      substance: acc.substance / n,
      retrieval: acc.retrieval / n,
      location: acc.location / n,
    }
  }

  const aS = avg(shortlist)
  const aK = avg(skipped)
  const delta = {
    must_have: aS.must_have - aK.must_have,
    substance: aS.substance - aK.substance,
    retrieval: aS.retrieval - aK.retrieval,
    location: aS.location - aK.location,
  } as const

  // Pick the dimension with the largest absolute delta
  const ranked = (Object.entries(delta) as Array<[keyof typeof delta, number]>)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
  const [topKey, topDelta] = ranked[0]
  if (Math.abs(topDelta) < 0.03) return null

  const PHRASING: Record<keyof typeof delta, [string, string]> = {
    must_have: [
      'You favoured candidates who clearly cleared the must-have signals.',
      'You overlooked must-have coverage in favour of softer evidence.',
    ],
    substance: [
      'You favoured candidates with real substance in their role descriptions over those who only had the skills listed.',
      'You favoured candidates with the surface signals over those with deeper description-text substance.',
    ],
    retrieval: [
      'You favoured candidates whose profile language overlapped strongly with the JD.',
      'You favoured candidates whose actual work resembled the JD over those with surface keyword overlap.',
    ],
    location: [
      'Location and logistics mattered more to you than the model assumed.',
      'You ignored location preference and prioritised pure-fit signals.',
    ],
  }
  return PHRASING[topKey][topDelta > 0 ? 0 : 1]
}

export default function Act6Reflection({
  shortlistCount, fromTotal, hoursSaved, shortlist, skipped, onRestart,
}: Props) {
  const [showGraveyard, setShowGraveyard] = useState(false)
  const reflection = useMemo(
    () => reflectionFromBehaviour(shortlist, skipped),
    [shortlist, skipped],
  )

  // Also surface a small diversity snapshot: how many distinct companies?
  const distinctCompanies = useMemo(() => {
    const set = new Set(shortlist.map(c => c.current_company.toLowerCase()))
    return set.size
  }, [shortlist])

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
          className="mt-6 font-serif text-title text-ink-secondary space-y-2"
        >
          <p>{shortlistCount} {shortlistCount === 1 ? 'candidate' : 'candidates'} from {fromTotal.toLocaleString()}.</p>
          <p>About {hoursSaved} {hoursSaved === 1 ? 'hour' : 'hours'} saved.</p>
          {distinctCompanies >= 2 && (
            <p className="font-sans text-body text-ink-tertiary">
              From {distinctCompanies} distinct {distinctCompanies === 1 ? 'company' : 'companies'}.
            </p>
          )}
        </motion.div>

        {reflection && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.0, duration: 0.6 }}
            className="mt-10 font-serif italic text-title text-accent border-l-2 border-accent pl-4 leading-snug"
          >
            {reflection} We'll remember.
          </motion.p>
        )}

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.4, duration: 0.4 }}
          className="mt-12 flex flex-wrap items-center gap-6 font-sans text-body text-ink-tertiary"
        >
          <button
            onClick={() => setShowGraveyard(true)}
            className="hover:text-ink transition-colors underline decoration-1 underline-offset-4 decoration-hairline"
          >
            See what we filtered out
          </button>
          <button
            onClick={onRestart}
            className="hover:text-ink transition-colors"
          >
            Start over
          </button>
        </motion.div>
      </div>

      <GraveyardSheet open={showGraveyard} onClose={() => setShowGraveyard(false)} />
    </motion.section>
  )
}
