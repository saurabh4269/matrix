import { motion } from 'framer-motion'
import type { SNRItem, SkillItem } from '../lib/api'

interface Props {
  high: SNRItem[]
  skills: SkillItem[]
}

const friendlyName = (s: string): string => {
  const map: Record<string, string> = {
    production_embeddings_retrieval: 'Production embeddings/retrieval',
    production_vector_db: 'Vector DB / hybrid search',
    ranking_eval_framework: 'Ranking eval framework',
    python_proficiency: 'Python proficiency',
    years_applied_ml_at_product_co: 'Years of ML at product cos',
    description_specificity: 'Specificity in descriptions',
    narrative_arc_density: 'Problem-solving narratives',
    production_emphasis: 'Production / shipping language',
    verification_ratio: 'Verified vs claimed',
    acceleration: 'Career acceleration',
    summary_thoughtfulness: 'Summary thoughtfulness',
    company_stage_alignment: 'Company stage alignment',
    shipper_vs_researcher_ratio: 'Shipper ratio',
    named_employer_micro_boost: 'Recognised employer(s)',
    location_match: 'Location',
    yoe_band_fit: 'Years of experience',
    certifications_micro_boost: 'Certifications',
  }
  return map[s] ?? s
}

export default function SNRSplit({ high, skills }: Props) {
  // Unverified skills (low SNR) — skills the candidate listed without an assessment
  const lowSkills = skills.filter(s => !s.verified)

  return (
    <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 gap-6">
      <motion.div
        initial={{ opacity: 0, x: -8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4 }}
        className="p-5 bg-card border border-hairline rounded-lg"
      >
        <p className="font-sans text-xs uppercase tracking-widest text-signal-verified mb-3">
          We trust this
        </p>
        {high.length === 0 ? (
          <p className="font-serif text-base text-ink-tertiary italic">
            Few corroborated signals.
          </p>
        ) : (
          <ul className="space-y-2.5">
            {high.map((h, i) => (
              <li key={i} className="font-serif text-base text-ink leading-snug">
                <span className="font-medium">{friendlyName(h.name)}</span>
                <span className="text-ink-secondary"> — {h.evidence}</span>
              </li>
            ))}
          </ul>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, delay: 0.05 }}
        className="p-5 bg-card border border-hairline rounded-lg"
      >
        <p className="font-sans text-xs uppercase tracking-widest text-ink-tertiary mb-3">
          They claim this
        </p>
        {lowSkills.length === 0 ? (
          <p className="font-serif text-base text-ink-tertiary italic">
            No unverified claims of note.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {lowSkills.slice(0, 8).map((s, i) => (
              <li key={i} className="font-sans text-sm text-ink-secondary">
                <span className="font-medium">{s.name}</span>
                <span className="text-ink-tertiary">
                  {' '}— {s.proficiency}, {s.duration_months}mo, {s.endorsements}e
                </span>
              </li>
            ))}
          </ul>
        )}
      </motion.div>
    </div>
  )
}
