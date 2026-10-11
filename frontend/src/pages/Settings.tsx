import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState, type FormEvent } from 'react'
import { api, type User } from '../api'
import { ErrorText } from '../components'
import { inputClass, primaryButton } from '../lib'

const MAX_INTERVALS = [
  { days: 30, label: '1 month' },
  { days: 60, label: '2 months' },
  { days: 90, label: '3 months' },
  { days: 180, label: '6 months' },
  { days: 365, label: '1 year' },
  { days: 36500, label: 'No limit' },
]

const HOURS = Array.from({ length: 24 }, (_, h) => h)
const formatHour = (h: number) =>
  new Date(2000, 0, 1, h).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })

export default function SettingsPage({ user }: { user: User }) {
  const qc = useQueryClient()
  const [timezone, setTimezone] = useState(user.timezone)
  const [cap, setCap] = useState(String(user.daily_review_cap))
  const [digestEnabled, setDigestEnabled] = useState(user.digest_enabled)
  const [digestHour, setDigestHour] = useState(user.digest_hour)
  const [maxInterval, setMaxInterval] = useState(user.max_interval_days)
  const [lcUsername, setLcUsername] = useState(user.leetcode_username ?? '')
  const zones = useMemo(() => {
    const all = Intl.supportedValuesOf('timeZone')
    return all.includes(user.timezone) ? all : [user.timezone, ...all]
  }, [user.timezone])
  const detected = Intl.DateTimeFormat().resolvedOptions().timeZone

  const save = useMutation({
    mutationFn: () =>
      api<User>('/users/me', {
        method: 'PATCH',
        json: {
          timezone,
          daily_review_cap: Number(cap),
          max_interval_days: maxInterval,
          digest_enabled: digestEnabled,
          digest_hour: digestHour,
          leetcode_username: lcUsername.trim() || null,
        },
      }),
    onSuccess: (u) => {
      qc.setQueryData(['me'], u)
      qc.invalidateQueries({ queryKey: ['queue'] })
      qc.invalidateQueries({ queryKey: ['import'] })
      qc.invalidateQueries({ queryKey: ['cards'] })
    },
  })
  const submit = (e: FormEvent) => {
    e.preventDefault()
    save.mutate()
  }

  return (
    <div className="space-y-8 pt-4">
      <section>
        <h1 className="text-4xl font-bold">Settings</h1>
        <p className="mt-2 text-lg text-muted">Signed in as {user.email}.</p>
      </section>

      <form onSubmit={submit} className="max-w-md space-y-6">
        <label className="block">
          <span className="mb-1.5 block font-bold">Re-solves per day</span>
          <input
            className={inputClass}
            type="number"
            min={1}
            max={50}
            required
            value={cap}
            onChange={(e) => setCap(e.target.value)}
          />
          <span className="mt-1.5 block text-[15px] text-muted">
            A full re-solve takes 20–40 minutes, so a small number you’ll actually do beats a big one you’ll skip.
            Recall spreads reviews out so no day goes over this.
          </span>
        </label>

        <label className="block">
          <span className="mb-1.5 block font-bold">Longest gap between reviews</span>
          <select className={inputClass} value={maxInterval} onChange={(e) => setMaxInterval(Number(e.target.value))}>
            {!MAX_INTERVALS.some((o) => o.days === maxInterval) && <option value={maxInterval}>{maxInterval} days</option>}
            {MAX_INTERVALS.map((o) => (
              <option key={o.days} value={o.days}>{o.label}</option>
            ))}
          </select>
          <span className="mt-1.5 block text-[15px] text-muted">
            Problems you know well get spaced further and further apart. Set this to how far away your interviews are, so
            nothing drifts past them. Lowering it also pulls in reviews already scheduled further out.
          </span>
        </label>

        <label className="block">
          <span className="mb-1.5 block font-bold">Time zone</span>
          <select className={inputClass} value={timezone} onChange={(e) => setTimezone(e.target.value)}>
            {zones.map((z) => (
              <option key={z} value={z}>{z.replaceAll('_', ' ')}</option>
            ))}
          </select>
          <span className="mt-1.5 block text-[15px] text-muted">
            Decides when your day starts.
            {detected && detected !== timezone && (
              <>
                {' '}This device is set to {detected.replaceAll('_', ' ')}.{' '}
                <button type="button" className="text-teal underline underline-offset-4" onClick={() => setTimezone(detected)}>
                  Use that
                </button>
              </>
            )}
          </span>
        </label>

        <label className="block">
          <span className="mb-1.5 block font-bold">LeetCode username</span>
          <input
            className={inputClass}
            autoComplete="off"
            spellCheck={false}
            placeholder="Optional"
            value={lcUsername}
            onChange={(e) => setLcUsername(e.target.value)}
          />
          <span className="mt-1.5 block text-[15px] text-muted">
            Lets Log a problem list your recent accepted solves, so you can rate them instead of typing each one.
            Only your public profile is read.
          </span>
        </label>

        <fieldset className="space-y-3">
          <legend className="mb-1.5 font-bold">Daily reminder email</legend>
          <label className="flex items-center gap-2.5">
            <input
              type="checkbox"
              className="size-4 accent-[var(--teal)]"
              checked={digestEnabled}
              onChange={(e) => setDigestEnabled(e.target.checked)}
            />
            <span>Email me when problems are due</span>
          </label>
          <label className="block">
            <span className="flex items-center gap-2">
              <span className={`shrink-0 ${digestEnabled ? '' : 'text-muted'}`}>Send it at</span>
              <select
                className={inputClass.replace('w-full', 'w-auto')}
                disabled={!digestEnabled}
                value={digestHour}
                onChange={(e) => setDigestHour(Number(e.target.value))}
              >
                {HOURS.map((h) => (
                  <option key={h} value={h}>{formatHour(h)}</option>
                ))}
              </select>
            </span>
          </label>
          <span className="block text-[15px] text-muted">
            Only sent on days something is due, in your time zone. Every email has a link to turn this off.
          </span>
        </fieldset>

        <div className="flex items-center gap-3">
          <button className={primaryButton} disabled={save.isPending}>Save changes</button>
          {save.isSuccess && !save.isPending && <span role="status" className="text-muted">Saved</span>}
        </div>
        <ErrorText error={save.error} />
      </form>
    </div>
  )
}
