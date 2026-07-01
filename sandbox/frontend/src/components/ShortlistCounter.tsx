interface Props {
  count: number
  position: number
  total: number
  tuned?: boolean
}

export default function ShortlistCounter({ count, position, total, tuned }: Props) {
  return (
    <div className="reading flex items-center justify-between text-xs font-mono text-ink-tertiary">
      <span className="flex items-center gap-3">
        <span>{position} of {total}</span>
        {tuned && (
          <span className="text-accent uppercase tracking-wider">
            ranking tuned
          </span>
        )}
      </span>
      {count > 0 && (
        <span>
          Shortlist of {count}.
        </span>
      )}
    </div>
  )
}
