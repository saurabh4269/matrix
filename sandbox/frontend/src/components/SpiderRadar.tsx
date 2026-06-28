// Pure-SVG spider/radar chart for a candidate's five "fit dimensions".
// No charting library; ~150 lines of SVG keeps the bundle small and the
// styling consistent with our token system.

interface Axis {
  label: string
  value: number  // 0..1
}

interface Props {
  axes: Axis[]
  size?: number
}

export default function SpiderRadar({ axes, size = 240 }: Props) {
  const n = axes.length
  const cx = size / 2
  const cy = size / 2
  const R = size / 2 - 36  // leave room for labels

  if (n < 3) return null

  // Polygon vertex i at angle (270° - i*(360°/n)) so axis 0 points up.
  const angleFor = (i: number) =>
    (-Math.PI / 2) + (i * (2 * Math.PI / n))

  const pointAt = (i: number, r: number) => {
    const a = angleFor(i)
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r] as const
  }

  // Grid: 4 concentric polygons at 25%, 50%, 75%, 100% of R.
  const gridLevels = [0.25, 0.5, 0.75, 1.0]
  const gridPolygons = gridLevels.map(t => {
    const pts = Array.from({ length: n }, (_, i) => pointAt(i, R * t))
    return pts.map(p => p.join(',')).join(' ')
  })

  // Axes lines from centre to each outer vertex
  const axisLines = Array.from({ length: n }, (_, i) => pointAt(i, R))

  // Data polygon
  const dataPts = axes.map((a, i) => pointAt(i, R * Math.max(0, Math.min(1, a.value))))
  const dataPath = dataPts.map(p => p.join(',')).join(' ')

  // Label positions (slightly outside the outer ring)
  const labelPts = axes.map((_, i) => pointAt(i, R + 18))

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="overflow-visible"
      aria-label="Candidate fit radar"
    >
      {/* Grid polygons */}
      {gridPolygons.map((points, i) => (
        <polygon
          key={`grid-${i}`}
          points={points}
          fill="none"
          stroke="#EAE6DC"
          strokeWidth={i === gridLevels.length - 1 ? 1.2 : 1}
        />
      ))}

      {/* Axis spokes */}
      {axisLines.map(([x, y], i) => (
        <line
          key={`axis-${i}`}
          x1={cx} y1={cy} x2={x} y2={y}
          stroke="#EAE6DC" strokeWidth={1}
        />
      ))}

      {/* Data polygon */}
      <polygon
        points={dataPath}
        fill="rgba(184, 132, 59, 0.18)"
        stroke="#B8843B"
        strokeWidth={1.5}
      />
      {dataPts.map(([x, y], i) => (
        <circle key={`pt-${i}`} cx={x} cy={y} r={3} fill="#B8843B" />
      ))}

      {/* Labels */}
      {labelPts.map(([x, y], i) => {
        // text-anchor: middle if near top/bottom, otherwise based on x
        const a = angleFor(i)
        const cos = Math.cos(a)
        let anchor: 'start' | 'middle' | 'end' = 'middle'
        if (cos > 0.2) anchor = 'start'
        else if (cos < -0.2) anchor = 'end'
        return (
          <text
            key={`lab-${i}`}
            x={x}
            y={y}
            textAnchor={anchor}
            dominantBaseline="middle"
            className="font-sans"
            style={{ fontSize: 11, fill: '#5A5A5A' }}
          >
            {axes[i].label}
          </text>
        )
      })}
    </svg>
  )
}
