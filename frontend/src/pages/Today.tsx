import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, QUICK_RATINGS, type Card, type Queue, type RatingValue, type Suggestion } from '../api'
import { DifficultyTag, ErrorText, PatternChips, RatingButtons, Thread } from '../components'
import { formatClock, primaryButton, relativeDay, secondaryButton, tensionLabel, tensionOf, usePatterns, useStopwatch } from '../lib'

const QUICK_SECONDS = 120

type Phase = 'idle' | 'solving' | 'rating' | 'quick' | 'quick-check'

function Notes({ text }: { text: string }) {
  return <p className="border-l-2 border-rule pl-3 text-[15px] text-muted whitespace-pre-line">{text}</p>
}

// How long the thread animation plays after a rating before the row leaves the list.
const SNAP_MS = 450
const SETTLE_MS = 1000

function ReviewRow({ card, onDone }: { card: Card; onDone: (title: string, nextDue: string) => void }) {
  const qc = useQueryClient()
  const patterns = usePatterns()
  const [phase, setPhase] = useState<Phase>('idle')
  const [peek, setPeek] = useState(false)
  const [seconds] = useStopwatch(phase === 'solving' || phase === 'quick')
  const [outcome, setOutcome] = useState<{ updated: Card; failed: boolean; snapped: boolean } | null>(null)
  const quick = phase === 'quick' || phase === 'quick-check'
  const review = useMutation({
    mutationFn: (rating: RatingValue) =>
      api<Card>(`/cards/${card.id}/reviews`, {
        method: 'POST',
        json: { rating, duration_sec: seconds > 0 ? seconds : null, mode: quick ? 'quick' : 'full' },
      }),
    onSuccess: (updated, rating) => {
      // A failed review snaps the thread before it's retied; any other rating pulls it taut.
      const failed = rating === 1
      setOutcome({ updated, failed, snapped: failed })
      if (failed) setTimeout(() => setOutcome((o) => o && { ...o, snapped: false }), SNAP_MS)
      setTimeout(
        () => {
          onDone(card.problem.title, updated.due)
          qc.invalidateQueries({ queryKey: ['queue'] })
          qc.invalidateQueries({ queryKey: ['cards'] })
        },
        (failed ? SNAP_MS : 0) + SETTLE_MS,
      )
    },
  })

  const { problem } = card
  const shown = outcome?.updated ?? card
  const tension = outcome?.snapped ? 0 : tensionOf(shown.retrievability)
  const pct = Math.round(shown.retrievability * 100)
  const remaining = Math.max(QUICK_SECONDS - seconds, 0)

  return (
    <li className="rounded-xl border border-rule bg-sheet p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-2">
          <h2 className="text-xl font-bold leading-tight">
            <a href={problem.url} target="_blank" rel="noreferrer" className="hover:text-teal hover:underline underline-offset-4">
              {problem.lc_number && <span className="text-muted">{problem.lc_number}. </span>}
              {problem.title}
            </a>
          </h2>
          <p className="flex flex-wrap gap-x-4 gap-y-1 text-[15px] text-muted">
            <DifficultyTag difficulty={problem.difficulty} />
            {card.last_review && <span>Last solved {relativeDay(card.last_review)}</span>}
            {card.lapses > 0 && <span>Forgotten {card.lapses}×</span>}
          </p>
          <PatternChips slugs={card.patterns} patterns={patterns.data} />
        </div>
        <figure className="shrink-0 sm:text-right">
          <Thread
            tension={tension}
            knots={shown.lapses}
            snapped={outcome?.snapped}
            label={`${tensionLabel(tension)}: about ${pct}% likely you still remember this`}
            className="h-12 w-40"
          />
          <figcaption className="mt-1 text-sm text-muted" aria-hidden="true">
            {outcome?.snapped ? 'Snapped' : `${tensionLabel(tension)} · ${pct}% likely to recall`}
          </figcaption>
        </figure>
      </div>

      <div className="mt-4 space-y-3">
        {outcome && (
          <p className="font-bold" aria-live="polite">
            {outcome.failed ? 'Snapped, then retied with a knot.' : 'Pulled taut.'}{' '}
            <span className="font-normal text-muted">Next review {relativeDay(outcome.updated.due)}.</span>
          </p>
        )}

        {!outcome && phase === 'idle' && (
          <>
            <div className="flex flex-wrap gap-2">
              <a
                href={problem.url}
                target="_blank"
                rel="noreferrer"
                onClick={() => setPhase('solving')}
                className={primaryButton}
              >
                Open and start timer
              </a>
              {card.quick_eligible && (
                <button type="button" className={secondaryButton} onClick={() => setPhase('quick')}>
                  Quick review, 2 min
                </button>
              )}
              <button type="button" className="px-2 text-muted underline underline-offset-4 hover:text-ink" onClick={() => setPhase('rating')}>
                I already solved it
              </button>
            </div>
            {card.notes &&
              (peek ? (
                <Notes text={card.notes} />
              ) : (
                <button type="button" className="text-[15px] text-muted underline underline-offset-4" onClick={() => setPeek(true)}>
                  Show my notes
                </button>
              ))}
          </>
        )}

        {phase === 'solving' && (
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-display text-3xl font-bold tabular-nums" aria-live="off">
              {formatClock(seconds)}
            </span>
            <button type="button" className={primaryButton} onClick={() => setPhase('rating')}>
              Done, rate it
            </button>
          </div>
        )}

        {phase === 'quick' && (
          <div className="space-y-3 rounded-lg bg-paper p-4">
            <p>
              Without opening the problem, write down or say out loud: the approach, the key data structure, and the time
              and space complexity.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <span className={`font-display text-3xl font-bold tabular-nums ${remaining === 0 ? 'text-hard' : ''}`} aria-live="off">
                {formatClock(remaining)}
              </span>
              <button type="button" className={primaryButton} onClick={() => setPhase('quick-check')}>
                {remaining === 0 ? 'Time’s up, check it' : 'Check my answer'}
              </button>
            </div>
          </div>
        )}

        {!outcome && (phase === 'rating' || phase === 'quick-check') && (
          <div className="space-y-3">
            {phase === 'quick-check' && (
              <p className="text-[15px]">
                Compare with{card.notes ? ' your notes below, or' : ''}{' '}
                <a href={`${problem.url}solutions/`} target="_blank" rel="noreferrer" className="text-teal underline underline-offset-4">
                  the solutions on LeetCode
                </a>
                .
              </p>
            )}
            {card.notes && <Notes text={card.notes} />}
            <p className="font-bold">
              How did it go?
              {phase === 'rating' && seconds > 0 && <span className="font-normal text-muted"> You took {formatClock(seconds)}.</span>}
            </p>
            <RatingButtons
              onRate={(r) => review.mutate(r)}
              disabled={review.isPending}
              options={phase === 'quick-check' ? QUICK_RATINGS : undefined}
            />
            <ErrorText error={review.error} />
          </div>
        )}
      </div>
    </li>
  )
}

function TryNext({ cleared }: { cleared: boolean }) {
  const suggestions = useQuery({ queryKey: ['cards', 'suggestions'], queryFn: () => api<Suggestion[]>('/suggestions') })
  if (!suggestions.data?.length) return null
  return (
    <section>
      <h2 className="text-2xl font-bold">Try a new problem</h2>
      <p className="mt-1 text-muted">
        {cleared ? 'Reviews are done, so this is a good time to learn something new.' : 'Once your reviews are done.'}
      </p>
      <ul className="mt-4 divide-y divide-rule rounded-xl border border-rule bg-sheet px-5">
        {suggestions.data.map((s) => (
          <li key={s.problem.slug} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-4">
            <div className="min-w-0">
              <a href={s.problem.url} target="_blank" rel="noreferrer" className="font-bold hover:text-teal hover:underline underline-offset-4">
                <span className="text-muted">{s.problem.lc_number}. </span>
                {s.problem.title}
              </a>
              <p className="flex flex-wrap gap-x-4 text-[15px] text-muted">
                <DifficultyTag difficulty={s.problem.difficulty} />
                <span>{s.name}</span>
                <span>{s.reason}</span>
              </p>
            </div>
            <Link to={`/add?q=${encodeURIComponent(s.problem.slug)}`} className="text-[15px] text-teal underline underline-offset-4">
              Solved it? Log it
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function TodayPage() {
  const queue = useQuery({ queryKey: ['queue'], queryFn: () => api<Queue>('/queue/today') })
  const [done, setDone] = useState<{ title: string; due: string }[]>([])

  if (queue.isPending) return <p className="text-muted">Loading today’s problems…</p>
  if (queue.isError) return <ErrorText error={queue.error} />

  const { cards, overflow, reviewed_today } = queue.data
  const count = cards.length

  return (
    <div className="space-y-8">
      <section className="pt-4">
        {count > 0 ? (
          <h1 className="text-4xl font-bold leading-tight sm:text-5xl">
            <span className="marked">{count}</span> {count === 1 ? 'problem' : 'problems'} to re-solve today
          </h1>
        ) : (
          <h1 className="text-4xl font-bold leading-tight sm:text-5xl">You’re clear for today</h1>
        )}
        <p className="mt-3 max-w-prose text-lg text-muted">
          {count > 0
            ? 'Each one is near the point where you’d start forgetting it. Solve it again from scratch, then rate how it went.'
            : reviewed_today > 0
              ? `You logged ${reviewed_today} ${reviewed_today === 1 ? 'solve' : 'solves'} today. The next reviews are already scheduled.`
              : 'Nothing is due. Solved something new? Log it so Retension can schedule a review.'}
        </p>
        {overflow > 0 && (
          <p className="mt-2 text-muted">
            {overflow} more {overflow === 1 ? 'is' : 'are'} overdue and will show up once you clear these.
          </p>
        )}
      </section>

      {done.length > 0 && (
        <ul className="space-y-1" aria-live="polite">
          {done.map((d) => (
            <li key={d.title + d.due} className="text-[15px]">
              <span className="font-bold">{d.title}</span>
              <span className="text-muted"> rated. Next review {relativeDay(d.due)}.</span>
            </li>
          ))}
        </ul>
      )}

      {count > 0 ? (
        <ul className="space-y-4" aria-label="Problems to re-solve">
          {cards.map((c) => (
            <ReviewRow key={c.id} card={c} onDone={(title, due) => setDone((d) => [...d, { title, due }])} />
          ))}
        </ul>
      ) : (
        <Link to="/add" className={`${primaryButton} inline-block`}>
          Log a problem
        </Link>
      )}

      <TryNext cleared={count === 0} />
    </div>
  )
}
