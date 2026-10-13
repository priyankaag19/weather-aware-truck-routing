import { useState } from 'react'
import PlaceInput from './PlaceInput'
import { EXAMPLE, INTERVALS } from '../constants'
import { inputValue } from '../format'

function defaultDeparture() {
  const d = new Date(Date.now() + 60 * 60 * 1000)
  d.setMinutes(0, 0, 0)
  return inputValue(d)
}

export default function TripForm({ onSubmit, loading }) {
  const [origin, setOrigin] = useState(null)
  const [destination, setDestination] = useState(null)
  const [departure, setDeparture] = useState(defaultDeparture)
  const [load, setLoad] = useState(42000)
  const [interval, setIntervalMi] = useState(25)
  const [error, setError] = useState('')

  const submit = (e) => {
    e.preventDefault()
    if (!origin || !destination) return setError('Pick the origin and destination from the suggestions.')
    if (!departure) return setError('Choose a departure date and time.')
    setError('')
    onSubmit({
      origin, destination,
      departure: new Date(departure).toISOString(),
      load_lb: Number(load),
      interval_mi: interval,
    })
  }

  return (
    <form className="trip-form" onSubmit={submit}>
      <PlaceInput label="Origin" value={origin} onChange={setOrigin} />
      <PlaceInput label="Destination" value={destination} onChange={setDestination} />
      <div className="row">
        <label className="field">
          <span>Departure</span>
          <input type="datetime-local" value={departure} onChange={(e) => setDeparture(e.target.value)} required />
        </label>
        <label className="field">
          <span>Load weight (lb)</span>
          <input type="number" min="0" max="200000" step="500" value={load} onChange={(e) => setLoad(e.target.value)} required />
        </label>
      </div>
      <fieldset className="field">
        <span>Weather checkpoint spacing</span>
        <div className="segmented">
          {INTERVALS.map((v) => (
            <button key={v} type="button" className={v === interval ? 'on' : ''} onClick={() => setIntervalMi(v)}>
              {v} mi
            </button>
          ))}
        </div>
      </fieldset>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="row actions">
        <button className="primary" disabled={loading}>{loading ? 'Analyzing routes…' : 'Find safest route'}</button>
        <button type="button" className="ghost" onClick={() => { setOrigin(EXAMPLE.origin); setDestination(EXAMPLE.destination) }}>
          Use example trip
        </button>
      </div>
    </form>
  )
}
