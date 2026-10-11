import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, QUICK_RATINGS, type Card, type Queue, type RatingValue } from '../api'
import { DifficultyTag, ErrorText, ForgettingCurve, PatternChips, RatingButtons } from '../components'
import { formatClock, primaryButton, relativeDay, secondaryButton, usePatterns, useStopwatch } from '../lib'

const QUICK_SECONDS = 120

type Phase = 'idle' | 'solving' | 'rating' | 'quick' | 'quick-check'

function Notes({ text }: { text: string }) {
  return <p className="border-l-2 border-rule pl-3 text-[15px] text-muted whitespace-pre-line">{text}</p>
}

function ReviewRow({ card, onDone }: { card: Card; onDone: (title: string, nextDue: string) => void }) {
  const qc = useQueryClient()
  const patterns = usePatterns()
  const [phase, setPhase] = useState<Phase>('idle')
  const [peek, setPeek] = useState(false)
  const [seconds] = useStopwatch(phase === 'solving' || phase === 'quick')
  const quick = phase === 'quick' || phase === 'quick-check'
  const review = useMutation({
    mutationFn: (rating: RatingValue) =>
      api<Card>(`/cards/${card.id}/reviews`, {
        method: 'POST',
        json: { rating, duration_sec: seconds > 0 ? seconds : null, mode: quick ? 'quick' : 'full' },
      }),
    onSuccess: (updated) => {
      onDone(card.problem.title, updated.due)
      qc.invalidateQueries({ queryKey: ['queue'] })
      qc.invalidateQueries({ queryKey: ['cards'] })
    },
  })

  const { problem } = card
  const pct = Math.round(card.retrievability * 100)
  const remaining = Math.max(QUICK_SECONDS - seconds, 0)

  return (
    <li className="rounded-xl border border-rule bg-sheet p-5">
      <div className="flex items-start justify-between gap-4">
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
        <figure className="hidden shrink-0 text-right sm:block">
          <ForgettingCurve card={card} />
          <figcaption className="mt-1 text-sm text-muted">{pct}% likely to recall</figcaption>
        </figure>
      </div>

      <div className="mt-4 space-y-3">
        {phase === 'idle' && (
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

        {(phase === 'rating' || phase === 'quick-check') && (
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
              : 'Nothing is due. Solved something new? Log it so Recall can schedule a review.'}
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
        <ul className="space-y-4">
          {cards.map((c) => (
            <ReviewRow key={c.id} card={c} onDone={(title, due) => setDone((d) => [...d, { title, due }])} />
          ))}
        </ul>
      ) : (
        <Link to="/add" className={`${primaryButton} inline-block`}>
          Log a problem
        </Link>
      )}
    </div>
  )
}
