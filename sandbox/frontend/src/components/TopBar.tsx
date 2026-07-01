// Persistent header: wordmark left, meta-actions right. Renders across
// every phase where those actions make sense, so the recruiter always knows
// where to find them and each candidate card can stay focused on the
// candidate.

import { motion } from 'framer-motion'

interface Props {
  onOpenTuning?: () => void
  onOpenDashboard?: () => void
  onOpenJdPicker?: () => void
  onOpenShortlist?: () => void
  shortlistCount?: number
  jdLabel?: string
  extraRight?: React.ReactNode
  // Increments whenever weights change. Triggers a subtle pulse on the Tune
  // button so the recruiter sees a tuning tweak actually landed.
  tunePulseKey?: number
}

// A pill-style ghost button. Shortcut appears in a fast custom tooltip
// below the button on hover — 75ms fade instead of the ~500ms Windows
// title-tooltip delay.
function TopBarButton({
  onClick,
  label,
  shortcut,
  ariaLabel,
  pulseKey,
}: {
  onClick: () => void
  label: string
  shortcut?: string
  ariaLabel?: string
  // When this key changes, briefly pulses the button. Skipped if undefined.
  pulseKey?: number
}) {
  const tooltip = shortcut ? `${ariaLabel ?? label} (${shortcut})` : (ariaLabel ?? label)
  return (
    <div className="relative group">
      <motion.button
        onClick={onClick}
        aria-label={ariaLabel ?? label}
        animate={pulseKey === undefined ? undefined : { scale: [1, 1.06, 1] }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        key={pulseKey !== undefined ? `pulse-${pulseKey}` : undefined}
        className="font-sans text-small text-ink-secondary hover:text-ink
                   border border-hairline hover:border-ink-secondary
                   bg-canvas hover:bg-card
                   rounded-full px-4 py-1.5 transition-colors"
      >
        {label}
      </motion.button>
      <div
        role="tooltip"
        className="absolute top-full mt-1.5 left-1/2 -translate-x-1/2
                   pointer-events-none
                   opacity-0 group-hover:opacity-100 group-focus-within:opacity-100
                   transition-opacity duration-75
                   font-sans text-micro whitespace-nowrap
                   bg-ink text-canvas rounded px-2 py-1 z-40 shadow-sm"
      >
        {tooltip}
      </div>
    </div>
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
  tunePulseKey,
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
            pulseKey={tunePulseKey}
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
