import { motion } from 'framer-motion'
import type { SNRItem, SkillItem } from '../lib/api'

interface Props {
  high: SNRItem[]
  skills: SkillItem[]
}

// Translate probe names into plain English the user can read.
const NATURAL_SIGNAL: Record<string, string> = {
  production_embeddings_retrieval: 'Embedding & retrieval work',
  production_vector_db: 'Vector database experience',
  ranking_eval_framework: 'Ranking evaluation experience',
  python_proficiency: 'Python depth',
  years_applied_ml_at_product_co: 'ML at product companies',
  description_specificity: 'Substance in role descriptions',
  narrative_arc_density: 'Problem-solving narratives',
  production_emphasis: 'Production / shipping language',
  verification_ratio: 'Verified vs claimed',
  acceleration: 'Career acceleration',
  summary_thoughtfulness: 'Summary thoughtfulness',
  company_stage_alignment: 'Startup-stage fit',
  shipper_vs_researcher_ratio: 'Shipper, not researcher',
  named_employer_micro_boost: 'Recognised employer',
  location_match: 'Location',
  yoe_band_fit: 'Years of experience',
  certifications_micro_boost: 'Relevant certifications',
  bm25_jd_match: 'Keyword overlap with JD',
  dense_cosine_jd_match: 'Semantic similarity to JD',
}

export default function SNRSplit({ high, skills }: Props) {
  const lowSkills = skills.filter(s => !s.verified)
  const verifiedSkills = skills.filter(s => s.verified)

  return (
    <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
      <motion.div
        initial={{ opacity: 0, x: -4 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
        className="p-5 bg-card border border-hairline rounded-lg"
      >
        <p className="font-sans text-micro uppercase text-signal-verified mb-3">
          Verified
        </p>
        {high.length === 0 && verifiedSkills.length === 0 ? (
          <p className="font-sans text-small text-ink-tertiary italic">
            Few corroborated signals.
          </p>
        ) : (
          <ul className="space-y-2.5">
            {high.map((h, i) => {
              const label = NATURAL_SIGNAL[h.name]
              return (
                <li key={i} className="text-ink leading-snug">
                  {label && (
                    <span className="font-sans text-small font-medium block">{label}</span>
                  )}
                  <span className="font-sans text-small text-ink-secondary">{h.evidence}</span>
                </li>
              )
            })}
            {verifiedSkills.slice(0, 3).map((s, i) => (
              <li key={`vs-${i}`} className="text-ink leading-snug">
                <span className="font-sans text-small font-medium block">{s.name}</span>
                <span className="font-sans text-small text-ink-secondary">
                  tested · {s.proficiency} · {s.duration_months}mo
                </span>
              </li>
            ))}
          </ul>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 4 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3, delay: 0.05 }}
        className="p-5 bg-card border border-hairline rounded-lg"
      >
        <p className="font-sans text-micro uppercase text-ink-tertiary mb-3">
          Claimed only
        </p>
        {lowSkills.length === 0 ? (
          <p className="font-sans text-small text-ink-tertiary italic">
            No unverified claims.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {lowSkills.slice(0, 8).map((s, i) => (
              <li key={i} className="font-sans text-small text-ink-secondary leading-snug">
                {s.name}
                <span className="text-ink-tertiary">
                  {' '}· {s.proficiency} · {s.duration_months}mo
                </span>
              </li>
            ))}
          </ul>
        )}
      </motion.div>
    </div>
  )
}
