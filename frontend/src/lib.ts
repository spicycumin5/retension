import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api, ApiError, type Pattern, type User } from './api'

export const DAY = 86_400_000

export function relativeDay(iso: string) {
  const startOfToday = new Date().setHours(0, 0, 0, 0)
  const startOfThat = new Date(iso).setHours(0, 0, 0, 0)
  const d = Math.round((startOfThat - startOfToday) / DAY)
  if (d === 0) return 'today'
  if (d === 1) return 'tomorrow'
  if (d === -1) return 'yesterday'
  if (d > 0) return d < 60 ? `in ${d} days` : `in ${Math.round(d / 30)} months`
  return -d < 60 ? `${-d} days ago` : `${Math.round(-d / 30)} months ago`
}

export function useStopwatch(running: boolean) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (!running) return
    const id = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [running])
  return [seconds, setSeconds] as const
}

export function formatClock(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      try {
        return await api<User>('/users/me')
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null
        throw e
      }
    },
  })
}

export function usePatterns() {
  return useQuery({ queryKey: ['patterns'], queryFn: () => api<Pattern[]>('/patterns'), staleTime: Infinity })
}

export const inputClass =
  'w-full rounded-lg border border-rule bg-sheet px-3 py-2.5 text-ink placeholder:text-muted focus:border-teal focus:outline-none'

export const primaryButton =
  'rounded-lg bg-teal px-4 py-2.5 font-bold text-sheet transition-opacity hover:opacity-90 disabled:opacity-50'

export const secondaryButton =
  'rounded-lg border border-rule bg-sheet px-4 py-2.5 font-bold text-ink hover:border-teal disabled:opacity-50'

/**
 * How taut a problem's thread is, from 1 (just reviewed) to 0 (about to snap).
 * Reviews come due at 90% recall, which lands in "fraying"; overdue problems sink toward 0.
 */
export function tensionOf(retrievability: number) {
  return Math.min(Math.max((retrievability - 0.75) / (0.98 - 0.75), 0), 1)
}

export function tensionLabel(tension: number) {
  return tension >= 0.7 ? 'Taut' : tension >= 0.3 ? 'Fraying' : 'About to snap'
}
