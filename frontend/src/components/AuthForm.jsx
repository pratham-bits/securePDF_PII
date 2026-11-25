import { useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '../auth/useAuth.js'
import { useConfig } from '../lib/useConfig.js'
import './AuthForm.css'

const MIN_PASSWORD = 10

const COPY = {
  login: {
    title: 'Log in',
    submit: 'Log in',
    switchText: "Don't have an account?",
    switchTo: '/register',
    switchLabel: 'Create one',
  },
  register: {
    title: 'Create your account',
    submit: 'Create account',
    switchText: 'Already have an account?',
    switchTo: '/login',
    switchLabel: 'Log in',
  },
}

export default function AuthForm({ mode }) {
  const { user, loading, login, register } = useAuth()
  const location = useLocation()
  const copy = COPY[mode]
  const isRegister = mode === 'register'
  const { invite_required: inviteRequired } = useConfig()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [invite, setInvite] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Once logged in (by this form or an earlier session), go where the user was headed.
  if (!loading && user) {
    return <Navigate to={location.state?.from || '/dashboard'} replace />
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (isRegister && password !== confirm) {
      setError('The two passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      if (isRegister) {
        const code = invite.trim()
        if (code) {
          await register(email.trim(), password, code)
        } else {
          await register(email.trim(), password)
        }
      } else {
        await login(email.trim(), password)
      }
      // On success the provider sets the user and the redirect above takes over.
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  const passwordType = showPassword ? 'text' : 'password'

  return (
    <div className="auth">
      <h1>{copy.title}</h1>
      <form className="auth__form" onSubmit={handleSubmit}>
        {error && (
          <p className="alert alert--error" role="alert">
            {error}
          </p>
        )}

        <label className="field">
          <span className="field__label">Email</span>
          <input
            className="input"
            type="email"
            name="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Password</span>
          <input
            className="input"
            type={passwordType}
            name="password"
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            required
            minLength={isRegister ? MIN_PASSWORD : undefined}
            maxLength={128}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {isRegister && (
            <span className="field__hint">
              At least {MIN_PASSWORD} characters. A few random words work well.
            </span>
          )}
        </label>

        {isRegister && (
          <label className="field">
            <span className="field__label">Confirm password</span>
            <input
              className="input"
              type={passwordType}
              name="confirm"
              autoComplete="new-password"
              required
              maxLength={128}
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
            />
          </label>
        )}

        {isRegister && inviteRequired && (
          <label className="field">
            <span className="field__label">Invite code</span>
            <input
              className="input"
              type="text"
              name="invite"
              autoComplete="off"
              required
              maxLength={128}
              value={invite}
              onChange={(event) => setInvite(event.target.value)}
            />
            <span className="field__hint">
              SecurePDF is in a private beta. Use the code you were given.
            </span>
          </label>
        )}

        <label className="auth__show">
          <input
            type="checkbox"
            checked={showPassword}
            onChange={(event) => setShowPassword(event.target.checked)}
          />
          Show password
        </label>

        <button className="btn btn--primary" type="submit" disabled={submitting}>
          {submitting ? 'Please wait…' : copy.submit}
        </button>
      </form>

      <p className="auth__switch">
        {copy.switchText} <Link to={copy.switchTo}>{copy.switchLabel}</Link>
      </p>
    </div>
  )
}