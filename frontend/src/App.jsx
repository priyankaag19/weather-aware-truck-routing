import { useCallback, useState } from 'react'
import TripForm from './components/TripForm'
import RouteCard from './components/RouteCard'
import CheckpointTable from './components/CheckpointTable'
import MapView from './components/MapView'
import HeatSlider from './components/HeatSlider'
import { analyze } from './api'

export default function App() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [hour, setHour] = useState(0)
  const [heatVisible, setHeatVisible] = useState(true)
  const [showAll, setShowAll] = useState(false)
  const [focus, setFocus] = useState(null)

  const run = useCallback(async (payload) => {
    setLoading(true); setError('')
    try {
      const result = await analyze(payload)
      setData(result)
      setSelectedId(result.recommendation.route_id)
      setHour(0)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const selected = data?.routes.find((r) => r.id === selectedId)
  const rec = data?.recommendation

  return (
    <div className="app">
      <aside className="sidebar">
        <header>
          <h1>Weather-aware truck routing</h1>
          <p>Compares three routes by the weather your truck will actually meet, at the hour it gets there.</p>
        </header>
        <TripForm onSubmit={run} loading={loading} />
        {error && <p className="error banner" role="alert">{error}</p>}
        {loading && <p className="status">Fetching routes and forecasts. Long trips can take 10–20 seconds.</p>}

        {data && (
          <>
            <section className={`recommendation ${rec.blocked ? 'blocked' : ''}`}>
              <h2>{rec.blocked ? 'No safe route right now' : 'Recommendation'}</h2>
              <p>{rec.headline}</p>
              <ul>{rec.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
            </section>
            <section className="routes">
              {data.routes.map((r, i) => (
                <RouteCard key={r.id} route={r} index={i} selected={r.id === selectedId} onSelect={() => setSelectedId(r.id)} />
              ))}
              <label className="toggle">
                <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} /> Show checkpoints for all routes
              </label>
            </section>
            {selected && <CheckpointTable route={selected} onFocus={(c) => setFocus({ ...c, t: Date.now() })} />}
          </>
        )}
      </aside>

      <main className="map-wrap">
        <MapView data={data} selectedId={selectedId} onSelect={setSelectedId} showAllCheckpoints={showAll}
          heat={{ hour, visible: heatVisible }} focus={focus} />
        {!data && !loading && <div className="empty">Enter a trip to see routes, checkpoints and the weather heatmap here.</div>}
        {data && (
          <HeatSlider start={data.heatmap.start} hours={data.heatmap.hours} hour={hour} onHour={setHour}
            visible={heatVisible} onVisible={setHeatVisible} />
        )}
      </main>
    </div>
  )
}
