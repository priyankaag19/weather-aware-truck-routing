import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import { LEVELS } from '../constants'

// Canvas risk heatmap. Each sample paints a soft disc in its risk colour; discs are painted
// from lowest to highest risk, so the worst nearby condition always wins (additive heat
// libraries blend overlapping low risks into false reds). Redraws are rAF-throttled and
// cost ~O(samples), so dragging the 0–48 h slider stays smooth.
const RADIUS_MI = 14
const ALPHA = [0.42, 0.5, 0.58, 0.64, 0.7]
const RGB = LEVELS.map((l) => {
  const n = parseInt(l.color.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
})

export default function HeatLayer({ points, hour, visible }) {
  const map = useMap()
  const props = useRef({ points, hour, visible })
  const schedule = useRef(() => {})
  props.current = { points, hour, visible }

  useEffect(() => {
    const pane = map.getPane('riskHeat') || map.createPane('riskHeat')
    pane.style.zIndex = 350
    pane.style.pointerEvents = 'none'
    const canvas = L.DomUtil.create('canvas', 'risk-heat', pane)
    let raf = 0

    const draw = () => {
      raf = 0
      const { points: pts, hour: h, visible: show } = props.current
      const size = map.getSize()
      if (canvas.width !== size.x || canvas.height !== size.y) {
        canvas.width = size.x
        canvas.height = size.y
      }
      L.DomUtil.setPosition(canvas, map.containerPointToLayerPoint([0, 0]))
      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, size.x, size.y)
      if (!show || !pts.length) return

      const zoom = map.getZoom()
      const sorted = pts.slice().sort((a, b) => a.levels[h] - b.levels[h])
      for (const p of sorted) {
        const pt = map.latLngToContainerPoint([p.lat, p.lng])
        const metersPerPx = (40075016.686 * Math.cos((p.lat * Math.PI) / 180)) / (256 * 2 ** zoom)
        const r = Math.min(110, Math.max(9, (RADIUS_MI * 1609.344) / metersPerPx))
        if (pt.x < -r || pt.y < -r || pt.x > size.x + r || pt.y > size.y + r) continue
        const lvl = p.levels[h]
        const [rr, gg, bb] = RGB[lvl]
        const g = ctx.createRadialGradient(pt.x, pt.y, 0, pt.x, pt.y, r)
        g.addColorStop(0, `rgba(${rr},${gg},${bb},${ALPHA[lvl]})`)
        g.addColorStop(0.6, `rgba(${rr},${gg},${bb},${ALPHA[lvl] * 0.7})`)
        g.addColorStop(1, `rgba(${rr},${gg},${bb},0)`)
        ctx.fillStyle = g
        ctx.beginPath()
        ctx.arc(pt.x, pt.y, r, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    schedule.current = () => { if (!raf) raf = requestAnimationFrame(draw) }
    const events = 'move zoom moveend zoomend resize viewreset'
    map.on(events, schedule.current)
    schedule.current()
    return () => {
      map.off(events, schedule.current)
      cancelAnimationFrame(raf)
      canvas.remove()
    }
  }, [map])

  useEffect(() => { schedule.current() }, [points, hour, visible])
  return null
}
