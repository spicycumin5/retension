import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Card, type Pattern } from '../api'
import { DifficultyTag, ErrorText, PatternChips, PatternPicker, Thread } from '../components'
import { inputClass, primaryButton, relativeDay, secondaryButton, tensionLabel, tensionOf, usePatterns } from '../lib'

type Status = 'all' | 'due' | 'suspended'

function CardEditor({ card, patterns, onClose }: { card: Card; patterns: Pattern[]; onClose: () => void }) {
  const qc = useQueryClient()
  const [chosen, setChosen] = useState(card.patterns)
  const [notes, setNotes] = useState(card.notes)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['cards'] })
    qc.invalidateQueries({ queryKey: ['queue'] })
  }
  const save = useMutation({
    mutationFn: (body: Partial<Pick<Card, 'patterns' | 'notes' | 'suspended'>>) =>
      api<Card>(`/cards/${card.id}`, { method: 'PATCH', json: body }),
    onSuccess: refresh,
  })
  const remove = useMutation({
    mutationFn: () => api<void>(`/cards/${card.id}`, { method: 'DELETE' }),
    onSuccess: () => {
      refresh()
      onClose()
    },
  })

  return (
    <div className="mt-4 space-y-4 border-t border-rule pt-4">
      <div>
        <h3 className="mb-2 font-bold">Patterns</h3>
        <PatternPicker patterns={patterns} value={chosen} onChange={setChosen} />
      </div>
      <label className="block">
        <span className="mb-1.5 block font-bold">Notes</span>
        <textarea className={`${inputClass} min-h-20`} value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className={primaryButton}
          disabled={save.isPending}
          onClick={() => save.mutate({ patterns: chosen, notes }, { onSuccess: onClose })}
        >
          Save changes
        </button>
        <button
          type="button"
          className={secondaryButton}
          disabled={save.isPending}
          onClick={() => save.mutate({ suspended: !card.suspended })}
        >
          {card.suspended ? 'Resume reviews' : 'Pause reviews'}
        </button>
        {confirmDelete ? (
          <span className="flex items-center gap-2">
            <span className="text-hard">Delete this problem and its history?</span>
            <button type="button" className="font-bold text-hard underline" onClick={() => remove.mutate()}>
              Delete
            </button>
            <button type="button" className="text-muted underline" onClick={() => setConfirmDelete(false)}>
              Keep
            </button>
          </span>
        ) : (
          <button type="button" className="px-2 text-hard hover:underline" onClick={() => setConfirmDelete(true)}>
            Delete
          </button>
        )}
      </div>
      <ErrorText error={save.error ?? remove.error} />
    </div>
  )
}

function Row({ card, patterns }: { card: Card; patterns: Pattern[] | undefined }) {
  const [open, setOpen] = useState(false)
  const { problem } = card
  const overdue = !card.suspended && new Date(card.due) < new Date(new Date().setHours(24, 0, 0, 0))

  return (
    <li className={`rounded-xl border border-rule bg-sheet p-4 ${card.suspended ? 'opacity-70' : ''}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 space-y-1.5">
          <h2 className="text-lg font-bold leading-snug">
            <a href={problem.url} target="_blank" rel="noreferrer" className="hover:text-teal hover:underline underline-offset-4">
              {problem.lc_number && <span className="text-muted">{problem.lc_number}. </span>}
              {problem.title}
            </a>
          </h2>
          <p className="flex flex-wrap gap-x-4 gap-y-1 text-[15px] text-muted">
            <DifficultyTag difficulty={problem.difficulty} />
            {card.suspended ? (
              <span>Paused</span>
            ) : overdue ? (
              <span className="marked font-bold">Due {relativeDay(card.due)}</span>
            ) : (
              <span>Next review {relativeDay(card.due)}</span>
            )}
            <span>Solved {card.reps}×</span>
            {card.lapses > 0 && <span>Forgotten {card.lapses}×</span>}
          </p>
          <PatternChips slugs={card.patterns} patterns={patterns} />
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <span className="hidden sm:block">
            <Thread
              tension={tensionOf(card.retrievability)}
              knots={card.lapses}
              label={`${tensionLabel(tensionOf(card.retrievability))}: about ${Math.round(card.retrievability * 100)}% likely you still remember this`}
              className="h-9 w-[120px]"
            />
          </span>
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
            className="text-[15px] text-teal underline underline-offset-4"
          >
            {open ? 'Close' : 'Edit'}
          </button>
        </div>
      </div>
      {open && patterns && <CardEditor card={card} patterns={patterns} onClose={() => setOpen(false)} />}
    </li>
  )
}

export default function LibraryPage() {
  const patterns = usePatterns()
  const [pattern, setPattern] = useState('')
  const [status, setStatus] = useState<Status>('all')
  const params = new URLSearchParams({ status, ...(pattern && { pattern }) })
  const cards = useQuery({ queryKey: ['cards', status, pattern], queryFn: () => api<Card[]>(`/cards?${params}`) })

  const selectClass = `${inputClass} sm:w-auto`
  return (
    <div className="space-y-6 pt-4">
      <section>
        <h1 className="text-4xl font-bold">Library</h1>
        <p className="mt-2 text-lg text-muted">Every problem you’re tracking, soonest review first.</p>
      </section>

      <div className="flex flex-col gap-2 sm:flex-row">
        <label className="sr-only" htmlFor="pattern">Pattern</label>
        <select id="pattern" className={selectClass} value={pattern} onChange={(e) => setPattern(e.target.value)}>
          <option value="">All patterns</option>
          {patterns.data?.map((p) => (
            <option key={p.slug} value={p.slug}>{p.name}</option>
          ))}
        </select>
        <label className="sr-only" htmlFor="status">Status</label>
        <select id="status" className={selectClass} value={status} onChange={(e) => setStatus(e.target.value as Status)}>
          <option value="all">All problems</option>
          <option value="due">Due now</option>
          <option value="suspended">Paused</option>
        </select>
      </div>

      {cards.isPending && <p className="text-muted">Loading…</p>}
      <ErrorText error={cards.error} />
      {cards.data &&
        (cards.data.length ? (
          <ul className="space-y-3">
            {cards.data.map((c) => (
              <Row key={c.id} card={c} patterns={patterns.data} />
            ))}
          </ul>
        ) : pattern || status !== 'all' ? (
          <p className="text-muted">No problems match these filters.</p>
        ) : (
          <p className="text-muted">
            Your library is empty. <Link to="/add" className="text-teal underline underline-offset-4">Log your first problem</Link>
          </p>
        ))}
    </div>
  )
}
