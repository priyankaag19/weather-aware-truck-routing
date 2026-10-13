import { useEffect, useRef, useState } from 'react'
import { geocode } from '../api'

export default function PlaceInput({ label, value, onChange }) {
  const [text, setText] = useState(value?.label || '')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const skipNext = useRef(false)

  // Parent can set the place programmatically (example button).
  useEffect(() => {
    if (value && value.label !== text) {
      skipNext.current = true
      setText(value.label)
    }
  }, [value]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (skipNext.current) { skipNext.current = false; return }
    if (text.trim().length < 3) { setResults([]); return }
    const ctrl = new AbortController()
    const timer = setTimeout(async () => {
      setBusy(true)
      try {
        setResults(await geocode(text, ctrl.signal))
        setOpen(true)
      } catch { /* aborted or failed: keep typing */ }
      finally { setBusy(false) }
    }, 500) // Nominatim asks for ≤ 1 request/second
    return () => { clearTimeout(timer); ctrl.abort() }
  }, [text])

  const pick = (p) => {
    skipNext.current = true
    setText(p.label); setResults([]); setOpen(false); onChange(p)
  }

  return (
    <label className="field place">
      <span>{label}</span>
      <input
        value={text}
        placeholder="City, address, or lat,lng"
        onChange={(e) => { setText(e.target.value); if (value) onChange(null) }}
        onFocus={() => results.length && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        aria-invalid={!value && text.length > 2}
      />
      {busy && <em className="hint">Searching…</em>}
      {value && <em className="hint ok">Location set</em>}
      {open && results.length > 0 && (
        <ul className="suggestions">
          {results.map((r, i) => (
  <li key={`${i}-${r.lat},${r.lng}`}><button type="button" onMouseDown={() => pick(r)}>{r.label}</button></li>
))}
        </ul>
      )}
      {open && !busy && results.length === 0 && text.length > 2 && !value && (
        <em className="hint">No matches found</em>
      )}
    </label>
  )
}
