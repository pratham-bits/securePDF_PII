import { useEffect, useState } from 'react'

import { DEFAULT_CONFIG, fetchConfig } from '../api/config.js'

export function useConfig() {
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  useEffect(() => {
    let cancelled = false
    fetchConfig().then((value) => {
      if (!cancelled) setConfig(value)
    })
    return () => {
      cancelled = true
    }
  }, [])
  return config
}

// "1 hour", "2 hours", or a neutral phrase while the real value is unknown.
export function describeRetention(hours) {
  if (!hours) return 'a short time'
  return hours === 1 ? '1 hour' : `${hours} hours`
}
