// Persistent header: wordmark left, meta-actions right. Renders across
// every phase where those actions make sense, so the recruiter always knows
// where to find them and each candidate card can stay focused on the
// candidate.

interface Props {
  onOpenTuning?: () => void
  onOpenDashboard?: () => void
  onOpenJdPicker?: () => void
  onOpenShortlist?: () => void
  shortlistCount?: number
  jdLabel?: string
  extraRight?: React.ReactNode
}

// A pill-style ghost button. The shortcut key sits inside the button but is
// invisible until hover — reveals instantly (no browser-tooltip delay), so a
// recruiter learns it the first time they mouse near the button.
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
  return (
    <button
      onClick={onClick}
      aria-label={ariaLabel ?? label}
      className="group font-sans text-small text-ink-secondary hover:text-ink
                 border border-hairline hover:border-ink-secondary
                 bg-canvas hover:bg-card
                 rounded-full px-4 py-1.5 transition-colors
                 inline-flex items-center gap-1.5"
    >
      <span>{label}</span>
      {shortcut && (
        <kbd
          className="font-mono text-[10px] text-ink-tertiary
                     opacity-0 group-hover:opacity-100 focus-visible:opacity-100
                     transition-opacity duration-75
                     border border-hairline rounded px-1"
        >
          {shortcut}
        </kbd>
      )}
    </button>
  )
}

export default function TopBar({
  onOpenTuning,
  onOpenDashboard,
  onOpenJdPicker,
  onOpenShortlist,
  shortlistCount,
  jdLabel,
  extraRight,
}: Props) {
  const showShortlist = onOpenShortlist && (shortlistCount ?? 0) > 0
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
        {showShortlist && (
          <button
            onClick={onOpenShortlist}
            title="Review shortlist (S)"
            aria-label={`Review shortlist, ${shortlistCount} candidate${shortlistCount === 1 ? '' : 's'}`}
            className="font-sans text-small text-ink hover:text-canvas
                       bg-card hover:bg-action border border-action
                       rounded-full pl-4 pr-3 py-1.5 transition-colors
                       flex items-center gap-2"
          >
            Shortlist
            <span className="inline-flex items-center justify-center min-w-[1.4rem] h-5 px-1.5
                             bg-action text-canvas font-mono text-[11px] font-semibold
                             rounded-full">
              {shortlistCount}
            </span>
          </button>
        )}
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
