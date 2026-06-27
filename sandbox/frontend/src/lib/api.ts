// Tiny typed wrapper around the FastAPI backend.

export interface JDDigest {
  role: string
  location: string
  experience: string
  style: string
  avoid: string[]
}

export interface SNRItem {
  name: string
  score: number
  evidence: string
}

export interface SkillItem {
  name: string
  proficiency: string
  endorsements: number
  duration_months: number
  verified: boolean
}

export interface BehaviouralSnapshot {
  open_to_work: boolean
  response_rate: number
  last_active: string | null
  notice_days: number
  verified: boolean
}

export interface RankedCandidate {
  rank: number
  candidate_id: string
  name: string
  current_title: string
  current_company: string
  years_of_experience: number
  location: string
  headline: string
  reasoning: string
  whispered: boolean
  snr_high: SNRItem[]
  snr_low: SkillItem[]
  concerns: SNRItem[]
  behavioural: BehaviouralSnapshot
}

export interface RankResponse {
  jd_digest: JDDigest
  ranked: RankedCandidate[]
  total_evaluated: number
}

export async function fetchDemo(): Promise<RankResponse> {
  const r = await fetch('/api/demo')
  if (!r.ok) throw new Error(`API error ${r.status}`)
  return r.json()
}
