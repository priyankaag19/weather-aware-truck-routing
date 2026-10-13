import { useEffect, useState } from 'react'
import { LEVELS } from '../constants'

const fmt = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric' })

export default function HeatSlider({ start, hours, hour, onHour, visible, onVisible }) {
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    if (!playing) return
    const t = setInterval(() => onHour((h) => (h >= hours ? 0 : h + 1)), 450)
    return () => clearInterval(t)
  }, [playing, hours, onHour])

  const when = new Date(new Date(start).getTime() + hour * 3600 * 1000)
  return (
    <div className="heat-panel">
      <div className="heat-top">
        <label className="toggle">
          <input type="checkbox" checked={visible} onChange={(e) => onVisible(e.target.checked)} /> Weather heatmap
        </label>
        <button type="button" className="ghost small" onClick={() => setPlaying((p) => !p)} disabled={!visible}>
          {playing ? 'Pause' : 'Play'}
        </button>
        <span className="when">+{hour} h · {fmt.format(when)}</span>
      </div>
      <input type="range" min="0" max={hours} value={hour} disabled={!visible}
        onChange={(e) => onHour(Number(e.target.value))} aria-label="Hours after departure" />
      <div className="legend">
        {LEVELS.map((l) => (<span key={l.key}><i style={{ background: l.color }} />{l.label}</span>))}
      </div>
    </div>
  )
}
