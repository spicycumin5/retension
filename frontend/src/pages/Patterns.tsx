import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type PatternStats } from '../api'
import { DifficultyTag, ErrorText } from '../components'

const pct = (r: number) => `${Math.round(r * 100)}%`

function holdsFor(days: number) {
  if (days < 1) return 'less than a day'
  if (days < 1.5) return 'about a day'
  if (days < 60) return `about ${Math.round(days)} days`
  return `about ${Math.round(days / 30)} months`
}

function RecallMeter({ value, label }: { value: number; label: string }) {
  return (
    <div
      role="meter"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(value * 100)}
      aria-label={label}
      title={`${label}: ${pct(value)}`}
      className="h-2 w-full overflow-hidden rounded bg-rule"
    >
      <div className="h-full rounded bg-teal" style={{ width: `${Math.max(value * 100, 2)}%` }} />
    </div>
  )
}

function PatternRow({ s }: { s: PatternStats }) {
  const [open, setOpen] = useState(false)
  const recall = s.avg_recall ?? 0
  return (
    <li className="py-4 first:pt-0 last:pb-0">
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-lg font-bold">{s.name}</h2>
        <span className="font-display text-xl font-bold tabular-nums">{pct(recall)}</span>
      </div>
      <div className="mt-2">
        <RecallMeter value={recall} label={`Average recall for ${s.name}`} />
      </div>
      <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-[15px]">
        <p className="flex flex-wrap gap-x-4 gap-y-1 text-muted">
          <span>
            {s.problems} {s.problems === 1 ? 'problem' : 'problems'}
          </span>
          {s.due > 0 && <span className="marked font-bold">{s.due} due</span>}
          {s.holds_days !== null && <span>Holds {holdsFor(s.holds_days)}</span>}
          {s.lapses > 0 && <span>Forgotten {s.lapses}×</span>}
        </p>
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
          className="text-teal underline underline-offset-4"
        >
          {open ? 'Hide' : s.problems === 1 ? 'Show problem' : 'Show problems'}
        </button>
      </div>
      {open && (
        <div className="mt-3 space-y-2 rounded-lg bg-paper p-3">
          {s.problems > s.weakest.length && (
            <p className="text-[15px] text-muted">The {s.weakest.length} you’re most likely to have forgotten:</p>
          )}
          <ul className="space-y-1.5">
            {s.weakest.map((w) => (
              <li key={w.card_id} className="flex items-baseline justify-between gap-4">
                <a href={w.problem.url} target="_blank" rel="noreferrer" className="hover:text-teal hover:underline">
                  {w.problem.lc_number && <span className="text-muted">{w.problem.lc_number}. </span>}
                  {w.problem.title}
                </a>
                <span className="shrink-0 tabular-nums text-muted">{pct(w.recall)}</span>
              </li>
            ))}
          </ul>
          <div className="border-t border-rule pt-2 text-[15px]">
            {s.next_problem ? (
              <p>
                <span className="text-muted">Try next: </span>
                <a href={s.next_problem.url} target="_blank" rel="noreferrer" className="font-bold text-teal underline underline-offset-4">
                  {s.next_problem.lc_number}. {s.next_problem.title}
                </a>{' '}
                <DifficultyTag difficulty={s.next_problem.difficulty} />
              </p>
            ) : (
              <p className="text-muted">You track every problem Retension knows for this pattern.</p>
            )}
            <a href={s.practice_url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-muted underline underline-offset-4">
              Browse all {s.name} problems on LeetCode
            </a>
          </div>
        </div>
      )}
    </li>
  )
}

export default function PatternsPage() {
  const stats = useQuery({ queryKey: ['cards', 'pattern-stats'], queryFn: () => api<PatternStats[]>('/stats/patterns') })

  if (stats.isPending) return <p className="pt-4 text-muted">Loading…</p>
  if (stats.isError) return <ErrorText error={stats.error} />

  const tracked = stats.data.filter((s) => s.problems > 0)
  const untracked = stats.data.filter((s) => s.problems === 0)

  return (
    <div className="space-y-8 pt-4">
      <section>
        <h1 className="text-4xl font-bold">Patterns</h1>
        <p className="mt-2 max-w-prose text-lg text-muted">
          How likely you are to recall each pattern right now, averaged over its problems. Weakest first.
        </p>
      </section>

      {tracked.length ? (
        <ul className="divide-y divide-rule rounded-xl border border-rule bg-sheet p-5">
          {tracked.map((s) => (
            <PatternRow key={s.pattern} s={s} />
          ))}
        </ul>
      ) : (
        <p className="text-muted">
          Log a few problems and your patterns will show up here.{' '}
          <Link to="/add" className="text-teal underline underline-offset-4">Log a problem</Link>
        </p>
      )}

      {untracked.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold">Not started</h2>
          <p className="mt-1 text-muted">Patterns you haven’t logged a problem for. Each links to matching LeetCode problems.</p>
          <ul className="mt-4 flex flex-wrap gap-2">
            {untracked.map((s) => (
              <li key={s.pattern}>
                <a
                  href={s.practice_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block rounded-full border border-rule bg-sheet px-3 py-1 text-[15px] hover:border-teal hover:text-teal"
                >
                  {s.name}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
