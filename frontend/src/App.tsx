import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { api, type User } from './api'
import { secondaryButton, useMe } from './lib'
import AddPage from './pages/Add'
import { ForgotPage, LoginPage, ResetPage, SignupPage, VerifyPage } from './pages/Auth'
import LibraryPage from './pages/Library'
import SettingsPage from './pages/Settings'
import TodayPage from './pages/Today'

function Wordmark() {
  return (
    <span className="font-display text-2xl font-extrabold tracking-tight text-teal">
      recall<span className="text-mark">.</span>
    </span>
  )
}

function Shell({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const logout = useMutation({
    mutationFn: () => api<void>('/auth/logout', { method: 'POST' }),
    onSettled: () => {
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'me' })
      qc.setQueryData(['me'], null)
    },
  })
  const link = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-2.5 py-1.5 ${isActive ? 'bg-sheet font-bold text-ink shadow-[0_0_0_1px_var(--rule)]' : 'text-muted hover:text-ink'}`

  return (
    <div className="mx-auto min-h-screen max-w-3xl px-4 pb-24 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-3 py-5">
        <NavLink to="/" aria-label="Recall home">
          <Wordmark />
        </NavLink>
        <nav className="flex flex-wrap items-center gap-1 text-[15px]">
          <NavLink to="/" end className={link}>Today</NavLink>
          <NavLink to="/add" className={link}>Log a problem</NavLink>
          <NavLink to="/library" className={link}>Library</NavLink>
          <NavLink to="/settings" className={link}>Settings</NavLink>
          <button
            type="button"
            onClick={() => logout.mutate()}
            className="px-2.5 py-1.5 text-muted hover:text-ink"
          >
            Log out
          </button>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  )
}

function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col px-4 py-10">
      <Wordmark />
      <main className="mt-10">{children}</main>
    </div>
  )
}

function CheckInbox({ user }: { user: User }) {
  const resend = useMutation({
    mutationFn: () => api<void>('/auth/request-verify-token', { method: 'POST', json: { email: user.email } }),
  })
  return (
    <AuthShell>
      <h1 className="text-3xl font-bold">Check your inbox</h1>
      <p className="mt-3 text-muted">
        We sent a verification link to <strong className="text-ink">{user.email}</strong>. Open it to start
        tracking problems.
      </p>
      <button className={`${secondaryButton} mt-6`} disabled={resend.isPending || resend.isSuccess} onClick={() => resend.mutate()}>
        {resend.isSuccess ? 'Link sent' : 'Resend link'}
      </button>
    </AuthShell>
  )
}

export default function App() {
  const me = useMe()
  const location = useLocation()

  if (me.isPending) return null
  if (me.isError) {
    return (
      <AuthShell>
        <p role="alert" className="text-hard">Can’t reach the server. Check your connection and reload.</p>
      </AuthShell>
    )
  }

  const user = me.data
  const publicRoutes = (
    <>
      <Route path="/verify" element={<AuthShell><VerifyPage /></AuthShell>} />
      <Route path="/reset-password" element={<AuthShell><ResetPage /></AuthShell>} />
    </>
  )

  if (!user) {
    return (
      <Routes>
        {publicRoutes}
        <Route path="/login" element={<AuthShell><LoginPage /></AuthShell>} />
        <Route path="/signup" element={<AuthShell><SignupPage /></AuthShell>} />
        <Route path="/forgot-password" element={<AuthShell><ForgotPage /></AuthShell>} />
        <Route path="*" element={<Navigate to="/login" replace state={{ from: location.pathname }} />} />
      </Routes>
    )
  }

  if (!user.is_verified) {
    return (
      <Routes>
        {publicRoutes}
        <Route path="*" element={<CheckInbox user={user} />} />
      </Routes>
    )
  }

  return (
    <Routes>
      {publicRoutes}
      <Route path="/" element={<Shell><TodayPage /></Shell>} />
      <Route path="/add" element={<Shell><AddPage /></Shell>} />
      <Route path="/library" element={<Shell><LibraryPage /></Shell>} />
      <Route path="/settings" element={<Shell><SettingsPage user={user} /></Shell>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
