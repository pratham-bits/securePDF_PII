import { useCallback, useEffect, useMemo, useState } from 'react'

import { api } from '../api/client.js'
import { AuthContext } from './AuthContext.js'

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Ask the server who we are. The session lives in an httpOnly cookie,
  // so JavaScript never sees the token itself.
  useEffect(() => {
    let cancelled = false
    api
      .get('/auth/me')
      .then((me) => {
        if (!cancelled) setUser(me)
      })
      .catch(() => {
        if (!cancelled) setUser(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email, password) => {
    const me = await api.post('/auth/login', { email, password })
    setUser(me)
    return me
  }, [])

  const register = useCallback(
    async (email, password) => {
      await api.post('/auth/register', { email, password })
      return login(email, password)
    },
    [login],
  )

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } finally {
      setUser(null)
    }
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}