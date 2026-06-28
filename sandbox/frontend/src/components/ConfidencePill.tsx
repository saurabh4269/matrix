interface Props {
  confidence: 'high' | 'medium' | 'low'
}

const STYLE: Record<Props['confidence'], { label: string; bg: string; text: string }> = {
  high:   { label: 'High confidence',   bg: 'bg-[#E8F0E0]', text: 'text-[#3D5A2C]' },
  medium: { label: 'Medium confidence', bg: 'bg-[#F2EAD7]', text: 'text-[#7A5E25]' },
  low:    { label: 'Low confidence',    bg: 'bg-[#F0E6E2]', text: 'text-[#7A4B3C]' },
}

export default function ConfidencePill({ confidence }: Props) {
  const s = STYLE[confidence]
  return (
    <span
      className={`inline-flex items-center font-sans text-small ${s.bg} ${s.text} px-3 py-1 rounded-full`}
    >
      <span className="inline-block w-1.5 h-1.5 rounded-full bg-current mr-2 opacity-70" />
      {s.label}
    </span>
  )
}
