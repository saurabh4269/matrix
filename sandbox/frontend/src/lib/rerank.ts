// Client-side re-rank.
//
// The backend sends every top-N candidate's structured probe scores
// (must_have_sum, substance_sum, retrieval_sum, location_sum,
//  anti_snr_penalty, behavioural_modifier). When the user tunes
// category weights, we recompute the composite right here and re-order
// the deck. No backend roundtrip, no waiting.
//
// This is the architecture's HITL story made real: every probe weight
// is independently adjustable; tuning is a multiplication, not a
// re-train.

import type { RankedCandidate } from './api'

export interface UserWeights {
  must_have: number
  substance: number
  retrieval: number
  location: number
  behavioural_sensitivity: number
}

export const DEFAULT_WEIGHTS: UserWeights = {
  must_have: 1.0,
  substance: 0.6,
  retrieval: 0.2,
  location: 0.1,
  // 1.0 = exactly what the backend computed; >1 = recruiter cares more
  // about reachability; <1 = recruiter willing to wait on dormant talent.
  behavioural_sensitivity: 1.0,
}

/** Recompute every candidate's composite score given the user's weights, then re-sort. */
export function rerank(
  candidates: RankedCandidate[],
  weights: UserWeights,
): RankedCandidate[] {
  const composites = candidates.map(c => {
    const b = c.breakdown
    // Use the *fractions* in `breakdown` to back out each component's raw
    // contribution: contribution_i = score * fraction_i / (anti_snr * behav).
    // But we don't have anti_snr separately; the breakdown's fractions
    // already sum to 1 across the additive part. We approximate by treating
    // the candidate's score as base * anti * behav, where base = sum(contrib).
    // Rebalance: new_base = sum(fraction_i * weights[i] * original_score)
    // since each fraction is contribution_i / original_base.
    const oldWeights = { must_have: 1.0, substance: 0.6, retrieval: 0.2, location: 0.1 }
    let newComposite = 0
    let oldBase = 0
    for (const k of ['must_have', 'substance', 'retrieval', 'location'] as const) {
      const frac = b[k] ?? 0
      // contribution = c.score * (frac / sum(frac)) is correct when frac already sums to 1.
      // We treat frac as the relative contribution to the additive base.
      newComposite += frac * weights[k]
      oldBase += frac * oldWeights[k]
    }
    // Scale: new score = c.score * (newComposite / oldBase)
    // and apply behavioural sensitivity: each unit of behavioural_modifier
    // is raised to the sensitivity exponent — sensitivity=2 means
    // a behav_modifier of 0.5 becomes 0.25; sensitivity=0.5 makes it 0.71.
    const scaleFactor = oldBase > 0 ? newComposite / oldBase : 1.0
    const behavMod = c.behavioural?.behav_modifier_total ?? 1.0
    const behavScale = Math.pow(behavMod, weights.behavioural_sensitivity - 1.0)
    return {
      cand: c,
      newScore: c.score * scaleFactor * behavScale,
    }
  })

  composites.sort((a, b) => b.newScore - a.newScore)
  return composites.map((entry, i) => ({
    ...entry.cand,
    rank: i + 1,
    // Surface the user-recomputed score for debugging; keep original score for the canonical CSV.
  }))
}

const STORAGE_KEY = 'matrix.userWeights'

export function loadStoredWeights(): UserWeights {
  if (typeof window === 'undefined') return { ...DEFAULT_WEIGHTS }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...DEFAULT_WEIGHTS }
    const parsed = JSON.parse(raw)
    return { ...DEFAULT_WEIGHTS, ...parsed }
  } catch {
    return { ...DEFAULT_WEIGHTS }
  }
}

export function saveStoredWeights(w: UserWeights): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(w))
  } catch {
    /* ignore */
  }
}

export function clearStoredWeights(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}
