import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { fetchDemo, RankResponse, RankedCandidate } from './lib/api'
import Act1JDDigest from './acts/Act1_JDDigest'
import Act2Deck from './acts/Act2_Deck'
import Act4Pause from './acts/Act4_Pause'
import Act5Shortlist from './acts/Act5_Shortlist'
import Act6Reflection from './acts/Act6_Reflection'
import LoaderSequence from './components/LoaderSequence'

type Phase =
  | 'arrival'
  | 'loading'
  | 'deck'
  | 'pause'
  | 'shortlist'
  | 'reflection'

export default function App() {
  const [phase, setPhase] = useState<Phase>('arrival')
  const [data, setData] = useState<RankResponse | null>(null)
  const [shortlist, setShortlist] = useState<RankedCandidate[]>([])
  const [deckIndex, setDeckIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)

  // Lazy-fetch on first move
  const beginJourney = async () => {
    if (data) {
      setPhase('deck')
      return
    }
    setPhase('loading')
    try {
      const r = await fetchDemo()
      setData(r)
      setPhase('deck')
    } catch (e) {
      setError(String(e))
      setPhase('arrival')
    }
  }

  const candidates = data?.ranked ?? []
  const current = candidates[deckIndex]

  const handleInterview = () => {
    if (!current) return
    if (!shortlist.find(c => c.candidate_id === current.candidate_id)) {
      setShortlist(s => [...s, current])
    }
    advance()
  }

  const handleNext = () => advance()

  const advance = () => {
    const next = deckIndex + 1
    if (next >= candidates.length) {
      setPhase('reflection')
      return
    }
    setDeckIndex(next)
    // Soft pauses every 7 candidates (when shortlist has at least 2)
    if ((next + 1) % 7 === 0 && shortlist.length >= 2) {
      setPhase('pause')
    }
  }

  const goBack = () => {
    if (deckIndex > 0) {
      setDeckIndex(i => i - 1)
    }
  }

  const finishedSavings = useMemo(() => ({
    shortlisted: shortlist.length,
    fromTotal: data?.total_evaluated ?? 0,
    hoursSaved: Math.max(1, Math.round((data?.total_evaluated ?? 0) / 150)),
  }), [shortlist.length, data?.total_evaluated])

  return (
    <main className="min-h-screen w-full bg-canvas text-ink overflow-x-hidden">
      <AnimatePresence mode="wait">
        {phase === 'arrival' && data === null && (
          <Act1JDDigest
            key="arrival"
            jd={null}
            onBegin={beginJourney}
            error={error}
          />
        )}
        {phase === 'arrival' && data !== null && (
          <Act1JDDigest
            key="arrival-data"
            jd={data.jd_digest}
            onBegin={beginJourney}
            error={null}
          />
        )}
        {phase === 'loading' && (
          <LoaderSequence key="loading" />
        )}
        {phase === 'deck' && current && (
          <Act2Deck
            key={`deck-${current.candidate_id}`}
            cand={current}
            onInterview={handleInterview}
            onNext={handleNext}
            onBack={goBack}
            shortlistCount={shortlist.length}
            position={deckIndex + 1}
            total={candidates.length}
          />
        )}
        {phase === 'pause' && (
          <Act4Pause
            key="pause"
            shortlistCount={shortlist.length}
            onContinue={() => setPhase('deck')}
            onReview={() => setPhase('shortlist')}
          />
        )}
        {phase === 'shortlist' && (
          <Act5Shortlist
            key="shortlist"
            shortlist={shortlist}
            setShortlist={setShortlist}
            onBack={() => setPhase('deck')}
            onSend={() => setPhase('reflection')}
          />
        )}
        {phase === 'reflection' && (
          <Act6Reflection
            key="reflection"
            shortlistCount={finishedSavings.shortlisted}
            fromTotal={finishedSavings.fromTotal}
            hoursSaved={finishedSavings.hoursSaved}
            onRestart={() => {
              setDeckIndex(0)
              setShortlist([])
              setPhase('arrival')
            }}
          />
        )}
      </AnimatePresence>
    </main>
  )
}
