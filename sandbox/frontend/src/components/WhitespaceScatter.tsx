// Pure-SVG scatter plot of candidates in 2D feature space.
// X: must-have score contribution. Y: behavioural availability.
// Dot size scales with the candidate's overall score; selected candidate
// gets the accent color.

import type { RankedCandidate } from '../lib/api'

interface Props {
  candidates: RankedCandidate[]
  selectedId?: string
  onSelect?: (id: string) => void
  size?: number
}

export default function WhitespaceScatter({
  candidates, selectedId, onSelect, size = 320,
}: Props) {
  const w = size
  const h = size * 0.7
  const pad = 32
  const innerW = w - pad * 2
  const innerH = h - pad * 2

  if (candidates.length === 0) return null

  // Plot top 20 only — beyond that the chart gets cluttered.
  const points = candidates.slice(0, 20).map(c => {
    const mh = c.breakdown?.must_have ?? 0  // fraction of additive score
    const behav = c.behavioural?.behav_modifier_total ?? 0.5
    return { c, x: mh, y: behav }
  })

  // Axes: 0..1 on both
  const sx = (x: number) => pad + x * innerW
  const sy = (y: number) => pad + (1 - y) * innerH  // invert so high = top

  return (
    <svg
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      className="overflow-visible"
      aria-label="Top-20 candidates by must-have vs availability"
    >
      {/* Axes */}
      <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} stroke="#EAE6DC" strokeWidth={1} />
      <line x1={pad} y1={pad} x2={pad} y2={h - pad} stroke="#EAE6DC" strokeWidth={1} />

      {/* Grid lines */}
      {[0.25, 0.5, 0.75].map(t => (
        <g key={t}>
          <line
            x1={pad} y1={sy(t)} x2={w - pad} y2={sy(t)}
            stroke="#EAE6DC" strokeWidth={0.5} strokeDasharray="2,3"
          />
          <line
            x1={sx(t)} y1={pad} x2={sx(t)} y2={h - pad}
            stroke="#EAE6DC" strokeWidth={0.5} strokeDasharray="2,3"
          />
        </g>
      ))}

      {/* Axis labels */}
      <text
        x={w / 2} y={h - 4}
        textAnchor="middle"
        style={{ fontSize: 11, fill: '#9A9A9A' }}
        className="font-sans"
      >
        must-have score →
      </text>
      <text
        x={8} y={h / 2}
        textAnchor="middle"
        transform={`rotate(-90, 8, ${h / 2})`}
        style={{ fontSize: 11, fill: '#9A9A9A' }}
        className="font-sans"
      >
        ← availability
      </text>

      {/* Points */}
      {points.map(({ c, x, y }) => {
        const selected = selectedId === c.candidate_id
        const r = 5 + (c.confidence === 'high' ? 4 : c.confidence === 'medium' ? 2 : 0)
        const fill = selected
          ? '#B8843B'  // accent
          : c.confidence === 'high'
            ? '#1F2933'  // graphite
            : c.confidence === 'medium'
              ? '#5A5A5A'  // mid gray
              : '#9A9A9A'  // light gray
        return (
          <g
            key={c.candidate_id}
            style={{ cursor: onSelect ? 'pointer' : 'default' }}
            onClick={() => onSelect?.(c.candidate_id)}
          >
            <circle
              cx={sx(x)} cy={sy(y)} r={r}
              fill={fill}
              fillOpacity={selected ? 1 : 0.7}
              stroke={selected ? '#1F2933' : 'none'}
              strokeWidth={selected ? 1.5 : 0}
            />
            {selected && (
              <text
                x={sx(x) + r + 4}
                y={sy(y) + 4}
                style={{ fontSize: 11, fill: '#1A1A1A', fontWeight: 500 }}
                className="font-sans"
              >
                {c.name}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}
