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

export interface ScoreBreakdown {
  must_have: number
  substance: number
  retrieval: number
  location: number
}

export interface HrmsRoutingAction {
  next_step: string
  assessment_id: string
  priority: 'high' | 'medium' | 'low'
  sla_hours: string
  reason_code: string
}

export interface RankedCandidate {
  rank: number
  score: number
  confidence: 'high' | 'medium' | 'low'
  rank_ci_95?: [number, number]
  breakdown: ScoreBreakdown
  next_action?: string
  main_risk?: string
  why_not_higher?: string[]
  hrms_routing_action?: HrmsRoutingAction
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

export interface DiscardedItem {
  candidate_id: string
  name: string
  current_title: string
  current_company: string
  discard_kind: 'honeypot' | 'heavy_anti_snr'
  rules_fired: { name: string; evidence: string; score?: number }[]
}

export async function fetchDiscarded(): Promise<DiscardedItem[]> {
  const r = await fetch('/api/discarded')
  if (!r.ok) throw new Error(`API error ${r.status}`)
  const d = await r.json()
  return d.discarded as DiscardedItem[]
}

// ---- JD selection -----------------------------------------------------------

export interface JdListItem {
  name: string
  display_name: string
  digest: JDDigest
  is_active: boolean
}

export async function listJds(): Promise<{ jds: JdListItem[]; active: string }> {
  const r = await fetch('/api/jds')
  if (!r.ok) throw new Error(`API error ${r.status}`)
  return r.json()
}

export async function selectJd(name: string): Promise<{ active: string; digest: JDDigest }> {
  const r = await fetch('/api/jd/select', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!r.ok) throw new Error((await r.json()).detail ?? `API error ${r.status}`)
  return r.json()
}

export async function bootstrapJd(text: string, name?: string): Promise<{ active: string; yaml_path: string; digest: JDDigest }> {
  const r = await fetch('/api/jd/bootstrap', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, name }),
  })
  if (!r.ok) throw new Error((await r.json()).detail ?? `API error ${r.status}`)
  return r.json()
}
