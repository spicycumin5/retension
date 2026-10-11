import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type Card, type ImportItem, type ImportResult, type RatingValue, type ResolveResult } from '../api'
import { DifficultyTag, ErrorText, PatternPicker, RatingButtons } from '../components'
import { inputClass, primaryButton, relativeDay, useMe, usePatterns } from '../lib'

function ImportRow({ item, onLogged }: { item: ImportItem; onLogged: (card: Card) => void }) {
  const qc = useQueryClient()
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['import'] })
    qc.invalidateQueries({ queryKey: ['queue'] })
    qc.invalidateQueries({ queryKey: ['cards'] })
  }
  const log = useMutation({
    mutationFn: async (rating: RatingValue) => {
      const { problem } = await api<ResolveResult>('/problems/resolve', { method: 'POST', json: { query: item.slug } })
      return api<Card>('/cards', {
        method: 'POST',
        json: { problem_id: problem.id, rating, solved_at: item.solved_at },
      })
    },
    onSuccess: (card) => {
      onLogged(card)
      refresh()
    },
  })
  const skip = useMutation({
    mutationFn: () => api<void>('/import/leetcode/dismiss', { method: 'POST', json: { slug: item.slug } }),
    onSuccess: refresh,
  })
  const busy = log.isPending || skip.isPending

  return (
    <li className="space-y-2 py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4">
        <a href={item.url} target="_blank" rel="noreferrer" className="font-bold hover:text-teal hover:underline underline-offset-4">
          {item.title}
        </a>
        <span className="text-[15px] text-muted">Solved {relativeDay(item.solved_at)}</span>
      </div>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="grow">
          <RatingButtons compact onRate={(r) => log.mutate(r)} disabled={busy} />
        </div>
        <button type="button" disabled={busy} onClick={() => skip.mutate()} className="px-2 text-[15px] text-muted underline underline-offset-4 hover:text-ink">
          Don’t track
        </button>
      </div>
      <ErrorText error={log.error ?? skip.error} />
    </li>
  )
}

const SHOWN_AT_FIRST = 5

function RecentSolves({ onLogged }: { onLogged: (card: Card) => void }) {
  const [showAll, setShowAll] = useState(false)
  const me = useMe()
  const username = me.data?.leetcode_username
  const recent = useQuery({
    queryKey: ['import', username],
    queryFn: () => api<ImportResult>('/import/leetcode'),
    enabled: !!username,
    staleTime: 60_000,
  })

  if (!username) {
    return (
      <p className="text-[15px] text-muted">
        Add your LeetCode username in <Link to="/settings" className="text-teal underline underline-offset-4">Settings</Link> to
        pick from your recent solves instead of typing them.
      </p>
    )
  }

  return (
    <section className="rounded-xl border border-rule bg-sheet p-5">
      <h2 className="text-xl font-bold">Recent solves on LeetCode</h2>
      {recent.isPending && <p className="mt-2 text-muted">Checking {username}’s recent solves…</p>}
      <div className="mt-2">
        <ErrorText error={recent.error} />
      </div>
      {recent.data &&
        (recent.data.items.length ? (
          <>
            <p className="mt-1 mb-4 text-[15px] text-muted">
              Rate how each one went to start tracking it. Reviews are scheduled from when you solved it.
            </p>
            <ul className="divide-y divide-rule">
              {(showAll ? recent.data.items : recent.data.items.slice(0, SHOWN_AT_FIRST)).map((item) => (
                <ImportRow key={item.slug} item={item} onLogged={onLogged} />
              ))}
            </ul>
            {!showAll && recent.data.items.length > SHOWN_AT_FIRST && (
              <button type="button" onClick={() => setShowAll(true)} className="mt-4 text-teal underline underline-offset-4">
                Show {recent.data.items.length - SHOWN_AT_FIRST} more
              </button>
            )}
          </>
        ) : (
          <p className="mt-1 text-[15px] text-muted">
            You’re tracking all of {username}’s recent accepted solves. LeetCode only shares the latest 20.
          </p>
        ))}
    </section>
  )
}

function LogForm({ result, onLogged }: { result: ResolveResult; onLogged: (card: Card) => void }) {
  const qc = useQueryClient()
  const patterns = usePatterns()
  const [chosen, setChosen] = useState(result.default_patterns)
  const [minutes, setMinutes] = useState('')
  const [notes, setNotes] = useState('')
  const save = useMutation({
    mutationFn: (rating: RatingValue) =>
      api<Card>('/cards', {
        method: 'POST',
        json: {
          problem_id: result.problem.id,
          rating,
          patterns: chosen,
          notes,
          duration_sec: minutes ? Math.round(Number(minutes) * 60) : null,
        },
      }),
    onSuccess: (card) => {
      qc.invalidateQueries({ queryKey: ['queue'] })
      qc.invalidateQueries({ queryKey: ['cards'] })
      onLogged(card)
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="mb-2 font-bold">Patterns</h2>
        <p className="mb-3 text-[15px] text-muted">Pre-selected from LeetCode’s tags. Change them to match how you solved it.</p>
        {patterns.data && <PatternPicker patterns={patterns.data} value={chosen} onChange={setChosen} />}
      </div>
      <div className="grid gap-4 sm:grid-cols-[10rem_1fr]">
        <label className="block">
          <span className="mb-1.5 block font-bold">Time taken</span>
          <span className="flex items-center gap-2">
            <input
              className={inputClass}
              type="number"
              inputMode="numeric"
              min={0}
              max={360}
              placeholder="25"
              value={minutes}
              onChange={(e) => setMinutes(e.target.value)}
            />
            <span className="text-muted">min</span>
          </span>
        </label>
        <label className="block">
          <span className="mb-1.5 block font-bold">Notes</span>
          <input
            className={inputClass}
            placeholder="Key insight, e.g. “stack of indices, pop while warmer”"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </label>
      </div>
      <div>
        <h2 className="mb-1 font-bold">How did it go?</h2>
        <p className="mb-3 text-[15px] text-muted">Picking an answer saves the problem and schedules its first review.</p>
        <RatingButtons onRate={(r) => save.mutate(r)} disabled={save.isPending} />
        <div className="mt-2">
          <ErrorText error={save.error} />
        </div>
      </div>
    </div>
  )
}

export default function AddPage() {
  const [query, setQuery] = useState('')
  const [logged, setLogged] = useState<Card | null>(null)
  const resolve = useMutation({
    mutationFn: (q: string) => api<ResolveResult>('/problems/resolve', { method: 'POST', json: { query: q } }),
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    setLogged(null)
    if (query.trim()) resolve.mutate(query.trim())
  }

  const result = resolve.data
  return (
    <div className="space-y-8 pt-4">
      <section>
        <h1 className="text-4xl font-bold">Log a problem</h1>
        <p className="mt-2 max-w-prose text-lg text-muted">
          Just solved something? Add it here and Recall will bring it back before you forget it.
        </p>
      </section>

      {logged && (
        <p role="status" className="rounded-xl border border-teal bg-teal-soft p-4">
          <strong>{logged.problem.title}</strong> logged.{' '}
          {new Date(logged.due) <= new Date() ? (
            <>
              It’s already due for review.{' '}
              <Link to="/" className="text-teal underline underline-offset-4">Find it in today’s queue</Link>
            </>
          ) : (
            <>
              First review {relativeDay(logged.due)}.{' '}
              <Link to="/" className="text-teal underline underline-offset-4">See today’s queue</Link>
            </>
          )}
        </p>
      )}

      <RecentSolves onLogged={setLogged} />

      <h2 className="text-xl font-bold">Look up a problem</h2>
      <form onSubmit={submit} className="-mt-5 flex flex-col gap-2 sm:flex-row">
        <label htmlFor="query" className="sr-only">LeetCode URL, number or title</label>
        <input
          id="query"
          className={inputClass}
          autoFocus
          placeholder="Paste a LeetCode URL, or type 739 or Daily Temperatures"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button className={`${primaryButton} shrink-0`} disabled={resolve.isPending || !query.trim()}>
          {resolve.isPending ? 'Looking up…' : 'Look up'}
        </button>
      </form>
      <ErrorText error={resolve.error} />

      {result && (
        <section className="space-y-6 rounded-xl border border-rule bg-sheet p-5">
          <div>
            <h2 className="text-2xl font-bold">
              {result.problem.lc_number && <span className="text-muted">{result.problem.lc_number}. </span>}
              {result.problem.title}
            </h2>
            <p className="mt-1 flex gap-4 text-[15px]">
              <DifficultyTag difficulty={result.problem.difficulty} />
              <a href={result.problem.url} target="_blank" rel="noreferrer" className="text-teal underline underline-offset-4">
                View on LeetCode
              </a>
            </p>
          </div>
          {result.card_id ? (
            <p>
              You already track this problem.{' '}
              <Link to="/library" className="text-teal underline underline-offset-4">Find it in your library</Link>
            </p>
          ) : (
            <LogForm
              key={result.problem.id}
              result={result}
              onLogged={(card) => {
                setLogged(card)
                setQuery('')
                resolve.reset()
              }}
            />
          )}
        </section>
      )}
    </div>
  )
}
