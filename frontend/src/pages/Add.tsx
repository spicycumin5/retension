import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type Card, type RatingValue, type ResolveResult } from '../api'
import { DifficultyTag, ErrorText, PatternPicker, RatingButtons } from '../components'
import { inputClass, primaryButton, relativeDay, usePatterns } from '../lib'

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

      <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row">
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

      {logged && (
        <p role="status" className="rounded-xl border border-teal bg-teal-soft p-4">
          <strong>{logged.problem.title}</strong> logged. First review {relativeDay(logged.due)}.{' '}
          <Link to="/" className="text-teal underline underline-offset-4">See today’s queue</Link>
        </p>
      )}

      {result && !logged && (
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
