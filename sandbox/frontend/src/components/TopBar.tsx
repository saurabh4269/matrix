// Persistent header: wordmark left, meta-actions right. Renders across
// every phase where those actions make sense, so the recruiter always knows
// where to find them and each candidate card can stay focused on the
// candidate.

interface Props {
  onOpenTuning?: () => void
  onOpenDashboard?: () => void
  onOpenJdPicker?: () => void
  jdLabel?: string
  extraRight?: React.ReactNode
}

// A pill-style ghost button. Native title attribute reveals the shortcut on
// hover — recruiter learns it over time, like PowerPoint tooltips. No
// inline kbd chip, no shouty affordance.
function TopBarButton({
  onClick,
  label,
  shortcut,
  ariaLabel,
}: {
  onClick: () => void
  label: string
  shortcut?: string
  ariaLabel?: string
}) {
  const title = shortcut ? `${ariaLabel ?? label} (${shortcut})` : (ariaLabel ?? label)
  return (
    <button
      onClick={onClick}
      title={title}
      aria-label={title}
      className="font-sans text-small text-ink-secondary hover:text-ink
                 border border-hairline hover:border-ink-secondary
                 bg-canvas hover:bg-card
                 rounded-full px-4 py-1.5 transition-colors"
    >
      {label}
    </button>
  )
}

export default function TopBar({
  onOpenTuning,
  onOpenDashboard,
  onOpenJdPicker,
  jdLabel,
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
      </div>

      <div className="flex items-center gap-3">
        {extraRight}
        {onOpenTuning && (
          <TopBarButton
            onClick={onOpenTuning}
            label="Tune"
            shortcut="T"
            ariaLabel="Tune ranking"
          />
        )}
        {onOpenDashboard && (
          <TopBarButton
            onClick={onOpenDashboard}
            label="Overview"
            shortcut="O"
            ariaLabel="Open overview"
          />
        )}
      </div>
    </header>
  )
}
