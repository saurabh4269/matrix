import type { SNRItem } from '../lib/api'

interface Props {
  concerns: SNRItem[]
}

const friendlyConcern = (name: string): string => {
  const map: Record<string, string> = {
    consulting_only: 'Consulting-only career',
    bigcorp_only: 'Bigcorp-only career',
    pure_research_career: 'Research-only background',
    no_production_code_18mo: 'No recent production code',
    framework_enthusiast: 'Framework-heavy, low production',
    title_chaser: 'Short tenures',
    cv_speech_robo_only: 'CV/speech focus, no NLP/IR',
    manager_drift: 'Manager-heavy recent roles',
    keyword_dense_junior: 'Keyword-dense for YoE',
    remote_only_vs_hybrid_jd: 'Remote-only mismatch',
    dilution: 'Mostly non-ML tenure',
  }
  return map[name] ?? name.replace(/_/g, ' ')
}

export default function ConcernCallout({ concerns }: Props) {
  const top = concerns[0]
  if (!top) return null
  return (
    <p className="mt-4 font-serif text-base text-signal-concern italic">
      {friendlyConcern(top.name)}, {top.evidence}.
    </p>
  )
}
