const BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function request(path, options) {
  let res
  try {
    res = await fetch(`${BASE}${path}`, options)
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new Error('Cannot reach the server. Check that the API is running.')
  }
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const fieldErrors = Object.values(body).flat().filter((v) => typeof v === 'string')
    throw new Error(body.error || fieldErrors[0] || `Request failed (${res.status})`)
  }
  return body
}

export const geocode = (q, signal) =>
  request(`/api/geocode/?q=${encodeURIComponent(q)}`, { signal }).then((b) => b.results)

export const analyze = (payload) =>
  request('/api/analyze/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
