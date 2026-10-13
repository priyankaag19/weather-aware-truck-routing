import RiskBar from './RiskBar'
import { LEVEL_BY_KEY, ROUTE_COLORS } from '../constants'
import { fmtDuration, fmtMi, fmtTime } from '../format'

export default function RouteCard({ route, index, selected, onSelect }) {
  const s = route.summary
  const worst = LEVEL_BY_KEY[s.max_level]
  return (
    <button className={`route-card ${selected ? 'selected' : ''}`} onClick={onSelect} aria-pressed={selected}
      style={{ '--route': ROUTE_COLORS[index % ROUTE_COLORS.length] }}>
      <div className="route-head">
        <strong>{route.label}</strong>
        {route.recommended && <span className="badge">Recommended</span>}
        <span className="chip" style={{ background: worst.color }}>Worst: {worst.label}</span>
      </div>
      <p className="roads">{route.roads.length ? `via ${route.roads.join(', ')}` : 'Local roads'}</p>
      <dl className="facts">
        <div><dt>Distance</dt><dd>{fmtMi(route.distance_mi)}</dd></div>
        <div><dt>Drive time</dt><dd>{fmtDuration(route.duration_s)}</dd></div>
        <div><dt>Arrive</dt><dd>{fmtTime(route.arrival)}</dd></div>
        <div><dt>Avg risk</dt><dd>{s.avg_risk.toFixed(2)} / 4</dd></div>
      </dl>
      <RiskBar milesByLevel={s.miles_by_level} />
      <p className="miles">
        Severe {Math.round(s.miles_by_level.severe)} mi · High {Math.round(s.miles_by_level.high)} mi
        {s.miles_by_level.no_travel > 0 && ` · No Travel ${Math.round(s.miles_by_level.no_travel)} mi`}
      </p>
    </button>
  )
}
