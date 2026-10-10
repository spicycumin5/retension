import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState, type FormEvent } from 'react'
import { api, type User } from '../api'
import { ErrorText } from '../components'
import { inputClass, primaryButton } from '../lib'

export default function SettingsPage({ user }: { user: User }) {
  const qc = useQueryClient()
  const [timezone, setTimezone] = useState(user.timezone)
  const [cap, setCap] = useState(String(user.daily_review_cap))
  const zones = useMemo(() => {
    const all = Intl.supportedValuesOf('timeZone')
    return all.includes(user.timezone) ? all : [user.timezone, ...all]
  }, [user.timezone])
  const detected = Intl.DateTimeFormat().resolvedOptions().timeZone

  const save = useMutation({
    mutationFn: () =>
      api<User>('/users/me', { method: 'PATCH', json: { timezone, daily_review_cap: Number(cap) } }),
    onSuccess: (u) => {
      qc.setQueryData(['me'], u)
      qc.invalidateQueries({ queryKey: ['queue'] })
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

        <div className="flex items-center gap-3">
          <button className={primaryButton} disabled={save.isPending}>Save changes</button>
          {save.isSuccess && !save.isPending && <span role="status" className="text-muted">Saved</span>}
        </div>
        <ErrorText error={save.error} />
      </form>
    </div>
  )
}
