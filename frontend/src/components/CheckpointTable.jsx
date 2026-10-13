import { LEVEL_BY_KEY } from '../constants'
import { fmtTime } from '../format'

export default function CheckpointTable({ route, onFocus }) {
  return (
    <div className="cp-wrap">
      <h3>{route.label} checkpoints</h3>
      <div className="cp-scroll">
        <table>
          <thead>
            <tr><th>Mile</th><th>ETA</th><th>Wind</th><th>Rain</th><th>Snow</th><th>Risk</th></tr>
          </thead>
          <tbody>
            {route.checkpoints.map((c) => (
              <tr key={c.mile} onClick={() => onFocus(c)} title={c.reasons.join('\n') || 'Clear'}>
                <td>{Math.round(c.mile)}</td>
                <td>{fmtTime(c.eta)}</td>
                <td>{c.wind_mph.toFixed(0)} mph</td>
                <td>{c.rain_in_hr.toFixed(2)}</td>
                <td>{c.snow_in_hr.toFixed(2)}</td>
                <td><span className="chip" style={{ background: LEVEL_BY_KEY[c.level].color }}>{LEVEL_BY_KEY[c.level].label}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note">Rain and snow in inches per hour. Click a row to find it on the map.</p>
    </div>
  )
}
