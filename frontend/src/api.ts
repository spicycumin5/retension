export type Difficulty = 'Easy' | 'Medium' | 'Hard'

export interface Problem {
  id: number
  slug: string
  lc_number: number | null
  title: string
  difficulty: Difficulty | null
  lc_tags: string[]
  url: string
}

export interface Card {
  id: number
  problem: Problem
  due: string
  last_review: string | null
  reps: number
  lapses: number
  notes: string
  suspended: boolean
  patterns: string[]
  retrievability: number
  quick_eligible: boolean
}

export interface Queue {
  cards: Card[]
  overflow: number
  reviewed_today: number
}

export interface ResolveResult {
  problem: Problem
  default_patterns: string[]
  card_id: number | null
}

export interface Pattern {
  slug: string
  name: string
}

export interface User {
  id: string
  email: string
  is_verified: boolean
  timezone: string
  digest_hour: number
  daily_review_cap: number
  digest_enabled: boolean
  leetcode_username: string | null
  max_interval_days: number
}

/** Ratings shown to users; values match the backend's UserRating. */
export const RATINGS = [
  { value: 1, label: 'Failed', hint: "Couldn't solve it" },
  { value: 2, label: 'Needed a hint', hint: 'Solved with help' },
  { value: 3, label: 'Solved slowly', hint: 'Got there, with effort' },
  { value: 4, label: 'Solved cold', hint: 'Knew it right away' },
] as const

export type RatingValue = (typeof RATINGS)[number]['value']

export interface RatingOption {
  value: RatingValue
  label: string
  hint: string
}

/** Quick reviews test only the approach, so they top out at the equivalent of "Solved slowly". */
export const QUICK_RATINGS: RatingOption[] = [
  { value: 1, label: 'Blank', hint: 'Couldn’t recall the approach' },
  { value: 2, label: 'Fuzzy', hint: 'Got parts, missed some' },
  { value: 3, label: 'Knew the approach', hint: 'Approach and complexity' },
]

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const FRIENDLY_DETAIL: Record<string, string> = {
  LOGIN_BAD_CREDENTIALS: 'That email and password don’t match an account.',
  LOGIN_USER_NOT_VERIFIED: 'Verify your email first. Check your inbox for the link.',
  REGISTER_USER_ALREADY_EXISTS: 'An account with that email already exists. Log in instead.',
  VERIFY_USER_BAD_TOKEN: 'This verification link is invalid or has expired.',
  VERIFY_USER_ALREADY_VERIFIED: 'Your email is already verified.',
  RESET_PASSWORD_BAD_TOKEN: 'This reset link is invalid or has expired.',
}

function describe(detail: unknown): string {
  if (typeof detail === 'string') return FRIENDLY_DETAIL[detail] ?? detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg?.replace(/^Value error, /, '')).join('. ')
  if (detail && typeof detail === 'object' && 'reason' in detail) return String(detail.reason)
  return 'Something went wrong. Try again.'
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, ...rest } = init
  const res = await fetch(`/api${path}`, {
    credentials: 'include',
    ...rest,
    headers: json !== undefined ? { 'Content-Type': 'application/json', ...rest.headers } : rest.headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  })
  if (!res.ok) {
    let detail: unknown
    try {
      detail = (await res.json()).detail
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, describe(detail))
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

export const login = (email: string, password: string) =>
  api<void>('/auth/login', {
    method: 'POST',
    body: new URLSearchParams({ username: email, password }),
  })

export interface PatternStats {
  pattern: string
  name: string
  practice_url: string
  problems: number
  due: number
  lapses: number
  avg_recall: number | null
  holds_days: number | null
  weakest: { card_id: number; problem: Problem; recall: number }[]
  next_problem: BankProblem | null
}

export interface BankProblem {
  slug: string
  title: string
  difficulty: Difficulty
  lc_number: number
  url: string
}

export interface Suggestion {
  pattern: string
  name: string
  reason: string
  problem: BankProblem
}

export interface ImportItem {
  slug: string
  title: string
  url: string
  solved_at: string
}

export interface ImportResult {
  username: string
  items: ImportItem[]
  already_tracked: number
}
