// Persistent header: wordmark left, meta-actions right. Renders across
// every phase where those actions make sense, so the recruiter always knows
// where to find them and each candidate card can stay focused on the
// candidate.

interface Props {
  onOpenTuning?: () => void
  onOpenDashboard?: () => void
  onOpenJdPicker?: () => void
  jdLabel?: string
  tuned?: boolean
  extraRight?: React.ReactNode
}

export default function TopBar({
  onOpenTuning,
  onOpenDashboard,
  onOpenJdPicker,
  jdLabel,
  tuned,
  extraRight,
}: Props) {
  return (
    <header className="w-full px-6 sm:px-10 py-3 flex items-center justify-between border-b border-hairline bg-canvas/95 backdrop-blur-sm sticky top-0 z-30">
      <div className="flex items-baseline gap-3">
        <span className="font-serif text-title font-medium tracking-tight">matrix</span>
        {jdLabel && (
          <button
            onClick={onOpenJdPicker}
            className="font-sans text-small text-ink-tertiary hover:text-ink transition-colors"
            title="Change JD"
          >
            {jdLabel}
          </button>
        )}
        {tuned && (
          <span className="font-sans text-micro uppercase text-accent tracking-wider">
            ranking tuned
          </span>
        )}
      </div>

      <div className="flex items-center gap-5 font-sans text-small text-ink-tertiary">
        {extraRight}
        {onOpenTuning && (
          <button
            onClick={onOpenTuning}
            className="hover:text-ink transition-colors"
            title="Tune ranking (T)"
          >
            Tune <kbd className="font-mono text-[11px]">T</kbd>
          </button>
        )}
        {onOpenDashboard && (
          <button
            onClick={onOpenDashboard}
            className="hover:text-ink transition-colors"
            title="Overview (O)"
          >
            Overview <kbd className="font-mono text-[11px]">O</kbd>
          </button>
        )}
      </div>
    </header>
  )
}
