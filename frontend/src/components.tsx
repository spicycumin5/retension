import { RATINGS, type Card, type Difficulty, type Pattern, type RatingValue } from './api'
import { DAY } from './lib'

// FSRS-6 forgetting curve: R(t) = (1 + F·t/S)^D, where R(S) = 0.9.
const DECAY = -0.1542
const FACTOR = 0.9 ** (1 / DECAY) - 1

/**
 * Where this problem sits on its forgetting curve. The curve starts at the last solve,
 * crosses 90% on the due date, and the dot marks today.
 */
export function ForgettingCurve({ card, width = 132, height = 40 }: { card: Card; width?: number; height?: number }) {
  if (!card.last_review) return null
  const last = new Date(card.last_review).getTime()
  const stability = Math.max((new Date(card.due).getTime() - last) / DAY, 0.5)
  // Invert the curve at the server's retrievability so the dot agrees with the server clock.
  const elapsed = (stability / FACTOR) * (Math.max(card.retrievability, 0.01) ** (1 / DECAY) - 1)
  const span = Math.max(stability, elapsed) * 1.35
  const r = (t: number) => (1 + (FACTOR * t) / stability) ** DECAY
  const floor = Math.min(r(span), 0.6)
  const pad = 4
  const x = (t: number) => pad + (t / span) * (width - pad * 2)
  const y = (v: number) => pad + ((1 - v) / (1 - floor)) * (height - pad * 2)

  const points = Array.from({ length: 33 }, (_, i) => (span * i) / 32)
  const path = points.map((t, i) => `${i ? 'L' : 'M'}${x(t).toFixed(1)},${y(r(t)).toFixed(1)}`).join(' ')
  const pct = Math.round(card.retrievability * 100)

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`About ${pct}% likely you still remember this`}
      className="shrink-0 overflow-visible"
    >
      <line x1={x(stability)} x2={x(stability)} y1={pad} y2={height - pad} stroke="var(--rule)" strokeDasharray="2 3" />
      <path d={`${path} L${x(span)},${height - pad} L${x(0)},${height - pad} Z`} fill="var(--teal-soft)" />
      <path d={path} fill="none" stroke="var(--teal)" strokeWidth={1.75} />
      <circle
        cx={x(elapsed)}
        cy={y(card.retrievability)}
        r={4}
        fill={elapsed >= stability ? 'var(--mark)' : 'var(--sheet)'}
        stroke="var(--ink)"
        strokeWidth={1.5}
      />
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
}: {
  onRate: (r: RatingValue) => void
  disabled?: boolean
  compact?: boolean
}) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {RATINGS.map((r) => (
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
