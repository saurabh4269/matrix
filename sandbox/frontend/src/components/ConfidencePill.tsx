interface Props {
  confidence: 'high' | 'medium' | 'low'
  currentRank?: number
  rankCi95?: [number, number]
}

const STYLE: Record<Props['confidence'], { label: string; bg: string; text: string }> = {
  high:   { label: 'High confidence',   bg: 'bg-[#E8F0E0]', text: 'text-[#3D5A2C]' },
  medium: { label: 'Medium confidence', bg: 'bg-[#F2EAD7]', text: 'text-[#7A5E25]' },
  low:    { label: 'Low confidence',    bg: 'bg-[#F0E6E2]', text: 'text-[#7A4B3C]' },
}

export default function ConfidencePill({ confidence, currentRank, rankCi95 }: Props) {
  const s = STYLE[confidence]
  // Only show the CI when it's wide enough to be informative
  const showCi = currentRank !== undefined && rankCi95 !== undefined
    && (rankCi95[1] - rankCi95[0]) >= 3

  return (
    <div className="inline-flex items-center gap-3 flex-wrap">
      <span
        className={`inline-flex items-center font-sans text-small ${s.bg} ${s.text} px-3 py-1 rounded-full`}
      >
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-current mr-2 opacity-70" />
        {s.label}
      </span>
      {showCi && (
        <span className="font-sans text-small text-ink-tertiary">
          Stable in rank {rankCi95[0]}–{rankCi95[1]}
        </span>
      )}
    </div>
  )
}
