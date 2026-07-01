interface Props {
  position: number
  total: number
}

// Minimal per-candidate position indicator. Shortlist count now lives in
// TopBar (persistent cart-style button); no need to duplicate here.
export default function ShortlistCounter({ position, total }: Props) {
  return (
    <div className="reading text-xs font-mono text-ink-tertiary">
      {position} of {total}
    </div>
  )
}
