import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { fetchDemo, RankResponse, RankedCandidate } from './lib/api'
import {
  DEFAULT_WEIGHTS,
  loadStoredWeights,
  rerank,
  saveStoredWeights,
  type UserWeights,
} from './lib/rerank'
import Act1JDDigest from './acts/Act1_JDDigest'
import Act2Deck from './acts/Act2_Deck'
import Act4Pause from './acts/Act4_Pause'
import Act5Shortlist from './acts/Act5_Shortlist'
import Act6Reflection from './acts/Act6_Reflection'
import Dashboard from './acts/Dashboard'
import LoaderSequence from './components/LoaderSequence'
import TuningPanel from './components/TuningPanel'
import MicroInterrogation from './components/MicroInterrogation'
import ErrorBoundary from './components/ErrorBoundary'
import TopBar from './components/TopBar'

type Phase =
  | 'arrival'
  | 'loading'
  | 'deck'
  | 'pause'
  | 'shortlist'
  | 'reflection'
  | 'dashboard'

type InterrogationKind = 'shortlist_override' | 'skip_override' | null

export default function App() {
  const [phase, setPhase] = useState<Phase>('arrival')
  const [data, setData] = useState<RankResponse | null>(null)
  const [previewDigest, setPreviewDigest] = useState<import('./lib/api').JDDigest | null>(null)
  const [shortlist, setShortlist] = useState<RankedCandidate[]>([])
  const [skipped, setSkipped] = useState<RankedCandidate[]>([])
  const [deckIndex, setDeckIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)

  // User-tuned weights (persisted in localStorage).
  const [weights, setWeights] = useState<UserWeights>(() => loadStoredWeights())
  const [tuningOpen, setTuningOpen] = useState(false)

  // Micro-interrogation state — fires when user overrides the system's ranking.
  const [interrogation, setInterrogation] = useState<{
    cand: RankedCandidate
    kind: InterrogationKind
  } | null>(null)

  // Persist weights to localStorage whenever they change.
  useEffect(() => { saveStoredWeights(weights) }, [weights])

  // Keyboard shortcuts.
  // T: open tuning panel from the deck.
  // O: toggle overview (dashboard) from anywhere with loaded data.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return
      if (e.target instanceof HTMLTextAreaElement) return
      if (e.key.toLowerCase() === 't' && phase === 'deck') {
        setTuningOpen(t => !t)
      } else if (e.key.toLowerCase() === 'o' && data) {
        setPhase(p => (p === 'dashboard' ? 'deck' : 'dashboard'))
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [phase, data])

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

  // JD switched on arrival screen → drop cached data so beginJourney re-fetches
  // against the new active JD. Hold the digest in previewDigest so the user
  // sees the new role on the arrival screen before clicking Begin.
  const handleJdChanged = (digest: import('./lib/api').JDDigest) => {
    setData(null)
    setPreviewDigest(digest)
    setShortlist([])
    setSkipped([])
    setDeckIndex(0)
    setError(null)
  }

  // Client-side rerank: apply user weights to the backend's structured probes.
  // Wrapped in try-catch so a malformed payload can never blank the UI.
  const candidates = useMemo(() => {
    if (!data) return []
    try {
      return rerank(data.ranked, weights)
    } catch (err) {
      console.error('Rerank failed, falling back to backend order:', err)
      return data.ranked
    }
  }, [data, weights])
  const current = candidates[deckIndex]

  // Detect "override" actions — user takes the opposite of the system's lean.
  // System leans 'interview' if rank ≤ 8 (top of the deck). User skipping a
  // top-8 candidate is an override; user shortlisting a bottom-half candidate
  // is also an override.
  const wantsToInterview = current && current.rank <= 8

  const handleInterview = () => {
    if (!current) return
    if (!shortlist.find(c => c.candidate_id === current.candidate_id)) {
      setShortlist(s => [...s, current])
    }
    // Override: shortlisted someone the system didn't put at the top
    if (!wantsToInterview) {
      setInterrogation({ cand: current, kind: 'shortlist_override' })
      // Don't advance until they close the modal; advance() runs in onClose.
      return
    }
    advance()
  }

  const handleNext = () => {
    if (!current) return
    setSkipped(s => [...s, current])
    // Override: skipped a top-of-deck candidate
    if (wantsToInterview && deckIndex < 8) {
      setInterrogation({ cand: current, kind: 'skip_override' })
      return
    }
    advance()
  }

  const closeInterrogation = () => {
    setInterrogation(null)
    advance()
  }

  const handleAdjustFromInterrogation = (next: UserWeights) => {
    setWeights(next)
  }

  const advance = () => {
    const next = deckIndex + 1
    if (next >= candidates.length) {
      setPhase('reflection')
      return
    }
    setDeckIndex(next)
    if ((next + 1) % 7 === 0 && shortlist.length >= 2) {
      setPhase('pause')
    }
  }

  const goBack = () => {
    if (deckIndex > 0) {
      setDeckIndex(i => i - 1)
    }
  }

  // "Ranking tuned" indicator: any weight ≠ the JD defaults
  const tuned = useMemo(
    () => (Object.keys(DEFAULT_WEIGHTS) as (keyof UserWeights)[])
      .some(k => Math.abs(weights[k] - DEFAULT_WEIGHTS[k]) > 1e-6),
    [weights],
  )

  const finishedSavings = useMemo(() => ({
    shortlisted: shortlist.length,
    fromTotal: data?.total_evaluated ?? 0,
    hoursSaved: Math.max(1, Math.round((data?.total_evaluated ?? 0) / 150)),
  }), [shortlist.length, data?.total_evaluated])

  const jdShortLabel = (data?.jd_digest.role ?? previewDigest?.role ?? '')
    .replace(/\.$/, '')

  const showTopBar = phase !== 'arrival' && phase !== 'loading'

  return (
    <main className="min-h-screen w-full bg-canvas text-ink overflow-x-hidden">
      {showTopBar && (
        <TopBar
          jdLabel={jdShortLabel || undefined}
          onOpenTuning={() => setTuningOpen(true)}
          onOpenDashboard={data ? () => setPhase(p => p === 'dashboard' ? 'deck' : 'dashboard') : undefined}
        />
      )}
      <AnimatePresence mode="wait">
        {phase === 'arrival' && data === null && (
          <Act1JDDigest
            key="arrival"
            jd={previewDigest}
            onBegin={beginJourney}
            onJdChanged={handleJdChanged}
            onOpenTuning={() => setTuningOpen(true)}
            error={error}
          />
        )}
        {phase === 'arrival' && data !== null && (
          <Act1JDDigest
            key="arrival-data"
            jd={data.jd_digest}
            onBegin={beginJourney}
            onJdChanged={handleJdChanged}
            onOpenTuning={() => setTuningOpen(true)}
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
            modalOpen={interrogation !== null || tuningOpen}
            shortlistCount={shortlist.length}
            position={deckIndex + 1}
            total={candidates.length}
            tuned={tuned}
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
        {phase === 'dashboard' && data && (
          <ErrorBoundary key="dashboard-eb" label="Overview" onBack={() => setPhase('deck')}>
            <Dashboard
              key="dashboard"
              jd={data.jd_digest}
              candidates={candidates}
              totalEvaluated={data.total_evaluated}
              onBackToDeck={() => setPhase('deck')}
            />
          </ErrorBoundary>
        )}
        {phase === 'reflection' && (
          <Act6Reflection
            key="reflection"
            shortlistCount={finishedSavings.shortlisted}
            fromTotal={finishedSavings.fromTotal}
            hoursSaved={finishedSavings.hoursSaved}
            shortlist={shortlist}
            skipped={skipped}
            onRestart={() => {
              setDeckIndex(0)
              setShortlist([])
              setSkipped([])
              setPhase('arrival')
            }}
          />
        )}
      </AnimatePresence>

      <TuningPanel
        open={tuningOpen}
        onClose={() => setTuningOpen(false)}
        weights={weights}
        onChange={setWeights}
        jdDisplayName={(data?.jd_digest.role ?? previewDigest?.role ?? '').replace(/\.$/, '')}
      />

      <MicroInterrogation
        cand={interrogation?.cand ?? null}
        kind={interrogation?.kind ?? null}
        onClose={closeInterrogation}
        weights={weights}
        onAdjust={handleAdjustFromInterrogation}
      />
    </main>
  )
}
