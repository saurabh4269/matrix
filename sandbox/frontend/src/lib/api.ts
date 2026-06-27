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

export interface BehaviouralBreakdownItem {
  name: string
  score: number
  evidence: string
}

export interface BehaviouralSnapshot {
  open_to_work: boolean
  response_rate: number
  response_time_hours: number
  last_active: string | null
  notice_days: number
  applications_30d: number
  saved_by_recruiters_30d: number
  profile_views_30d: number
  interview_completion_rate: number
  github_activity: number
  verified_email: boolean
  verified_phone: boolean
  linkedin_connected: boolean
  behav_modifier_total: number
  behav_breakdown: BehaviouralBreakdownItem[]
}

export interface CareerRole {
  title: string
  company: string
  company_size: string
  industry: string
  start_date: string | null
  end_date: string | null
  duration_months: number
  is_current: boolean
  description: string
}

export interface Education {
  institution: string
  degree: string
  field_of_study: string
  start_year: number | null
  end_year: number | null
  tier: string
  grade: string | null
}

export interface Certification {
  name: string
  issuer: string
  year: number | null
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
  summary: string
  career_history: CareerRole[]
  education: Education[]
  certifications: Certification[]
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
