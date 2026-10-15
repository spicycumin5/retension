import { useEffect, useRef, useState } from 'react'
import { RATINGS, type Difficulty, type Pattern, type RatingOption, type RatingValue } from './api'

const FIBERS = 5
const W = 160
const H = 48
const PEG_Y = 12
const PEGS = [8, W - 8] as const

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

// Overshoots past 1 and settles, so a thread pulled taut bows up and twangs back.
const easeOutElastic = (x: number) => (x >= 1 ? 1 : 1 - 2 ** (-7 * x) * Math.cos(x * Math.PI * 4))

/** Animates toward `target`, so a review visibly pulls the thread taut. */
function useAnimatedTension(target: number) {
  const [value, setValue] = useState(target)
  const from = useRef(target)
  useEffect(() => {
    const start = from.current
    if (start === target || prefersReducedMotion()) {
      from.current = target
      setValue(target)
      return
    }
    const began = performance.now()
    let frame = 0
    const step = (now: number) => {
      const x = Math.min((now - began) / 900, 1)
      const v = start + (target - start) * easeOutElastic(x)
      from.current = v
      setValue(v)
      if (x < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [target])
  return value
}

/**
 * A problem's memory as a thread between two pegs. Taut and tightly wound when fresh; as recall
 * fades it sags, its strands spread apart and break one by one, and the last strand reddens and
 * trembles. Each time the problem was forgotten leaves a knot. `snapped` draws the two broken halves.
 */
export function Thread({
  tension: target,
  knots = 0,
  snapped = false,
  label,
  className = '',
}: {
  tension: number
  knots?: number
  snapped?: boolean
  label: string
  className?: string
}) {
  const t = useAnimatedTension(target)
  const slack = Math.max(1 - t, 0)
  // Negative while overshooting, so the thread briefly bows upward.
  const sag = Math.sign(1 - t) * Math.abs(1 - t) ** 1.5 * 24
  const fray = slack * 4
  const intact = Math.max(1, Math.round((Math.min(t, 0.8) / 0.8) * FIBERS))
  const color = t >= 0.7 ? 'var(--teal)' : t >= 0.3 ? 'var(--medium)' : 'var(--hard)'
  const [x0, x1] = PEGS
  const mid = (x0 + x1) / 2

  // Quadratic curve whose midpoint sits `drop` below the pegs.
  const curve = (offset: number, drop: number) =>
    `M${x0},${PEG_Y + offset * 0.6} Q${mid},${PEG_Y + 2 * drop + offset * 2 * fray} ${x1},${PEG_Y + offset * 0.6}`
  const pointAt = (u: number, offset = 0, drop = sag) => ({
    x: x0 + (x1 - x0) * u,
    y: PEG_Y + offset * 0.6 + 2 * u * (1 - u) * (2 * drop + offset * 2 * fray),
  })
  // A broken strand: slack, so it hangs a little lower, with a gap where it parted.
  const brokenHalves = (offset: number) => {
    const breakAt = 0.44 + offset * 0.035
    const half = (from: number, to: number) =>
      Array.from({ length: 9 }, (_, i) => pointAt(from + ((to - from) * i) / 8, offset, sag + 3))
        .map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
        .join(' ')
    return [half(0, breakAt), half(1, breakAt + 0.12)]
  }

  // Break the outer strands first, alternating sides, so the core strand is the last to go.
  const order = [2, 1, 3, 0, 4]
  const fibers = order.map((i, rank) => ({ offset: i - 2, broken: rank >= intact }))
  const knotSpots = [0.32, 0.68, 0.5].slice(0, Math.min(knots, 3))

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} className={`overflow-visible ${className}`}>
      {snapped ? (
        <g stroke="var(--hard)" strokeWidth={1.4} fill="none" strokeLinecap="round">
          <path d={`M${x0},${PEG_Y} C${x0 + 24},${PEG_Y + 6} ${x0 + 34},${H - 10} ${x0 + 30},${H - 2}`} />
          <path d={`M${x1},${PEG_Y} C${x1 - 24},${PEG_Y + 6} ${x1 - 34},${H - 10} ${x1 - 30},${H - 2}`} />
        </g>
      ) : (
        <g className={t < 0.3 && target < 0.3 ? 'thread-strain' : undefined} fill="none" strokeLinecap="round">
          {fibers.map(({ offset, broken }) =>
            broken ? (
              <g key={offset} stroke="var(--muted)" strokeOpacity={0.6} strokeWidth={0.9} strokeLinejoin="round">
                {brokenHalves(offset).map((d) => (
                  <path key={d} d={d} />
                ))}
              </g>
            ) : (
              <path key={offset} d={curve(offset, sag)} stroke={color} strokeWidth={intact === 1 ? 1.1 : 1.3} />
            ),
          )}
          {knotSpots.map((u) => {
            const p = pointAt(u)
            return <ellipse key={u} cx={p.x} cy={p.y} rx={3.2} ry={2.6} fill={color} stroke="var(--sheet)" strokeWidth={1} />
          })}
        </g>
      )}
      {PEGS.map((x) => (
        <circle key={x} cx={x} cy={PEG_Y} r={3.5} fill="var(--ink)" />
      ))}
    </svg>
  )
}

const DIFFICULTY_COLOR: Record<Difficulty, string> = {
  Easy: 'text-easy',
  Medium: 'text-medium',
  Hard: 'text-hard',
}

export function DifficultyTag({ difficulty }: { difficulty: Difficulty | null }) {
  if (!difficulty) return null
  return <span className={`font-bold ${DIFFICULTY_COLOR[difficulty]}`}>{difficulty}</span>
}

export function PatternChips({ slugs, patterns }: { slugs: string[]; patterns: Pattern[] | undefined }) {
  const name = (s: string) => patterns?.find((p) => p.slug === s)?.name ?? s
  if (!slugs.length) return <span className="text-muted">No pattern</span>
  return (
    <ul className="flex flex-wrap gap-1.5">
      {slugs.map((s) => (
        <li key={s} className="rounded-full bg-teal-soft px-2.5 py-0.5 text-sm text-teal">
          {name(s)}
        </li>
      ))}
    </ul>
  )
}

export function PatternPicker({
  patterns,
  value,
  onChange,
}: {
  patterns: Pattern[]
  value: string[]
  onChange: (next: string[]) => void
}) {
  const toggle = (slug: string) =>
    onChange(value.includes(slug) ? value.filter((s) => s !== slug) : [...value, slug].sort())
  return (
    <div className="flex flex-wrap gap-2">
      {patterns.map((p) => {
        const on = value.includes(p.slug)
        return (
          <button
            key={p.slug}
            type="button"
            aria-pressed={on}
            onClick={() => toggle(p.slug)}
            className={`rounded-full border px-3 py-1 text-sm transition-colors ${
              on ? 'border-teal bg-teal text-sheet' : 'border-rule bg-sheet text-ink hover:border-teal'
            }`}
          >
            {p.name}
          </button>
        )
      })}
    </div>
  )
}

const RATING_STYLE: Record<RatingValue, string> = {
  1: 'hover:border-hard hover:text-hard',
  2: 'hover:border-medium hover:text-medium',
  3: 'hover:border-teal hover:text-teal',
  4: 'hover:border-easy hover:text-easy',
}

export function RatingButtons({
  onRate,
  disabled,
  compact = false,
  options = RATINGS,
}: {
  onRate: (r: RatingValue) => void
  disabled?: boolean
  compact?: boolean
  options?: readonly RatingOption[]
}) {
  return (
    <div className={`grid gap-2 ${options.length === 3 ? 'sm:grid-cols-3' : 'grid-cols-2 sm:grid-cols-4'}`}>
      {options.map((r) => (
        <button
          key={r.value}
          type="button"
          disabled={disabled}
          onClick={() => onRate(r.value)}
          title={compact ? r.hint : undefined}
          className={`rounded-lg border border-rule bg-sheet text-left transition-colors disabled:opacity-50 ${
            compact ? 'px-2.5 py-1.5 text-[15px]' : 'px-3 py-2.5'
          } ${RATING_STYLE[r.value]}`}
        >
          <span className="block font-bold">{r.label}</span>
          {!compact && <span className="block text-sm text-muted">{r.hint}</span>}
        </button>
      ))}
    </div>
  )
}

export function ErrorText({ error }: { error: unknown }) {
  if (!error) return null
  return (
    <p role="alert" className="text-hard">
      {error instanceof Error ? error.message : String(error)}
    </p>
  )
}
