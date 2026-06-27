interface Props {
  count: number
  position: number
  total: number
}

export default function ShortlistCounter({ count, position, total }: Props) {
  return (
    <div className="reading flex items-center justify-between text-xs font-mono text-ink-tertiary">
      <span>
        {position} of {total}
      </span>
      {count > 0 && (
        <span>
          Shortlist of {count}.
        </span>
      )}
    </div>
  )
}
