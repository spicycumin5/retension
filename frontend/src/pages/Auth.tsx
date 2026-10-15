import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { api, login } from '../api'
import { ErrorText } from '../components'
import { inputClass, primaryButton } from '../lib'

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block font-bold">{label}</span>
      {children}
    </label>
  )
}

function useAfterLogin() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const location = useLocation()
  return async () => {
    await qc.invalidateQueries({ queryKey: ['me'] })
    navigate((location.state as { from?: string } | null)?.from ?? '/', { replace: true })
  }
}

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const afterLogin = useAfterLogin()
  const m = useMutation({ mutationFn: () => login(email, password), onSuccess: afterLogin })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    m.mutate()
  }

  return (
    <>
      <h1 className="text-4xl font-bold">Log in</h1>
      <p className="mt-2 text-muted">Pick up today’s re-solves where you left off.</p>
      <form onSubmit={submit} className="mt-8 space-y-4">
        <Field label="Email">
          <input className={inputClass} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password">
          <input className={inputClass} type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <ErrorText error={m.error} />
        <button className={`${primaryButton} w-full`} disabled={m.isPending}>
          {m.isPending ? 'Logging in…' : 'Log in'}
        </button>
      </form>
      <p className="mt-6 flex justify-between text-muted">
        <Link to="/signup" className="text-teal underline underline-offset-4">Create an account</Link>
        <Link to="/forgot-password" className="underline underline-offset-4">Forgot password?</Link>
      </p>
    </>
  )
}

export function SignupPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const afterLogin = useAfterLogin()
  const m = useMutation({
    mutationFn: async () => {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
      await api('/auth/register', { method: 'POST', json: { email, password, timezone } })
      await login(email, password)
    },
    onSuccess: afterLogin,
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    m.mutate()
  }

  return (
    <>
      <h1 className="text-4xl font-bold">Stop re-learning problems you already solved</h1>
      <p className="mt-3 text-muted">
        Log each LeetCode problem after you solve it. Retension works out when you’re about to forget it and
        puts it back in front of you.
      </p>
      <form onSubmit={submit} className="mt-8 space-y-4">
        <Field label="Email">
          <input className={inputClass} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password">
          <input
            className={inputClass}
            type="password"
            autoComplete="new-password"
            minLength={8}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <span className="mt-1 block text-sm text-muted">At least 8 characters.</span>
        </Field>
        <ErrorText error={m.error} />
        <button className={`${primaryButton} w-full`} disabled={m.isPending}>
          {m.isPending ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="mt-6 text-muted">
        Already have an account? <Link to="/login" className="text-teal underline underline-offset-4">Log in</Link>
      </p>
    </>
  )
}

export function VerifyPage() {
  const [params] = useSearchParams()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const token = params.get('token') ?? ''
  const m = useMutation({
    mutationFn: () => api('/auth/verify', { method: 'POST', json: { token } }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['me'] })
      navigate('/', { replace: true })
    },
  })
  const started = useRef(false)
  useEffect(() => {
    if (!started.current && token) {
      started.current = true
      m.mutate()
    }
  }, [m, token])

  return (
    <>
      <h1 className="text-3xl font-bold">Verifying your email</h1>
      {!token && <p className="mt-3 text-hard">This link is missing its token. Open the link from your email again.</p>}
      {m.isPending && <p className="mt-3 text-muted">One moment…</p>}
      {m.isError && (
        <div className="mt-3 space-y-3">
          <ErrorText error={m.error} />
          <Link to="/" className="text-teal underline underline-offset-4">Go to Retension</Link>
        </div>
      )}
    </>
  )
}

export function ForgotPage() {
  const [email, setEmail] = useState('')
  const m = useMutation({ mutationFn: () => api('/auth/forgot-password', { method: 'POST', json: { email } }) })
  const submit = (e: FormEvent) => {
    e.preventDefault()
    m.mutate()
  }
  return (
    <>
      <h1 className="text-3xl font-bold">Reset your password</h1>
      {m.isSuccess ? (
        <p className="mt-3 text-muted">If an account exists for {email}, a reset link is on its way.</p>
      ) : (
        <form onSubmit={submit} className="mt-6 space-y-4">
          <Field label="Email">
            <input className={inputClass} type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <ErrorText error={m.error} />
          <button className={`${primaryButton} w-full`} disabled={m.isPending}>Send reset link</button>
        </form>
      )}
      <p className="mt-6">
        <Link to="/login" className="text-teal underline underline-offset-4">Back to log in</Link>
      </p>
    </>
  )
}

export function ResetPage() {
  const [params] = useSearchParams()
  const [password, setPassword] = useState('')
  const m = useMutation({
    mutationFn: () => api('/auth/reset-password', { method: 'POST', json: { token: params.get('token'), password } }),
  })
  const submit = (e: FormEvent) => {
    e.preventDefault()
    m.mutate()
  }
  return (
    <>
      <h1 className="text-3xl font-bold">Choose a new password</h1>
      {m.isSuccess ? (
        <p className="mt-3">
          Password changed. <Link to="/login" className="text-teal underline underline-offset-4">Log in</Link>
        </p>
      ) : (
        <form onSubmit={submit} className="mt-6 space-y-4">
          <Field label="New password">
            <input className={inputClass} type="password" autoComplete="new-password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <ErrorText error={m.error} />
          <button className={`${primaryButton} w-full`} disabled={m.isPending}>Change password</button>
        </form>
      )}
    </>
  )
}

export function UnsubscribePage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  // Requires a click so email link scanners that pre-fetch URLs can't unsubscribe people.
  const m = useMutation({
    mutationFn: () => api(`/email/unsubscribe?${new URLSearchParams({ token })}`, { method: 'POST' }),
  })
  return (
    <>
      <h1 className="text-3xl font-bold">Daily reminder emails</h1>
      {m.isSuccess ? (
        <p className="mt-3">
          Done. You won’t get daily reminders anymore. You can turn them back on in{' '}
          <Link to="/settings" className="text-teal underline underline-offset-4">Settings</Link>.
        </p>
      ) : (
        <>
          <p className="mt-3 text-muted">
            Stop the daily email that lists problems due for review. Your problems and schedule stay as they are.
          </p>
          <button className={`${primaryButton} mt-6`} disabled={!token || m.isPending} onClick={() => m.mutate()}>
            Stop daily emails
          </button>
          <div className="mt-3">
            {!token && <p className="text-hard">This link is missing its token. Open the link from your email again.</p>}
            <ErrorText error={m.error} />
          </div>
        </>
      )}
    </>
  )
}
