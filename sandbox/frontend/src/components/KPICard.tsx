interface Props {
  label: string
  value: string | number
  sublabel?: string
  tone?: 'default' | 'accent' | 'concern'
}

const TONE_TEXT = {
  default: 'text-ink',
  accent: 'text-accent',
  concern: 'text-signal-concern',
} as const

export default function KPICard({ label, value, sublabel, tone = 'default' }: Props) {
  return (
    <div className="p-4 bg-card border border-hairline rounded-lg min-w-0">
      <p className="font-sans text-micro uppercase text-ink-tertiary mb-2 truncate">
        {label}
      </p>
      <p className={`font-serif text-title font-medium ${TONE_TEXT[tone]} leading-none`}>
        {value}
      </p>
      {sublabel && (
        <p className="mt-1.5 font-sans text-small text-ink-tertiary truncate">
          {sublabel}
        </p>
      )}
    </div>
  )
}
