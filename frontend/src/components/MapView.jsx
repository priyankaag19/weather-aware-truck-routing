import { useEffect, useMemo } from 'react'
import { CircleMarker, MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import HeatLayer from './HeatLayer'
import { LEVEL_BY_KEY, ROUTE_COLORS } from '../constants'
import { fmtTime } from '../format'

const pin = (text) => L.divIcon({ className: 'pin', html: text, iconSize: [28, 28], iconAnchor: [14, 14] })

function Fit({ routes }) {
  const map = useMap()
  useEffect(() => {
    if (!routes.length) return
    const bounds = L.latLngBounds(routes.flatMap((r) => r.geometry))
    map.fitBounds(bounds, { padding: [48, 48] })
  }, [routes, map])
  return null
}

function Focus({ focus }) {
  const map = useMap()
  useEffect(() => {
    if (focus) map.flyTo([focus.lat, focus.lng], Math.max(map.getZoom(), 8), { duration: 0.6 })
  }, [focus, map])
  return null
}

export default function MapView({ data, selectedId, onSelect, showAllCheckpoints, heat, focus }) {
  const routes = data?.routes || []
  const ordered = useMemo(
    () => [...routes].sort((a, b) => (a.id === selectedId) - (b.id === selectedId)),
    [routes, selectedId],
  )
  const colorOf = (id) => ROUTE_COLORS[routes.findIndex((r) => r.id === id) % ROUTE_COLORS.length]

  return (
    <MapContainer center={[39.5, -98.35]} zoom={4} preferCanvas className="map" zoomControl>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {data && <HeatLayer points={data.heatmap.points} hour={heat.hour} visible={heat.visible} />}
      {data && <Fit routes={routes} />}
      <Focus focus={focus} />

      {ordered.map((r) => {
        const active = r.id === selectedId
        return (
          <Polyline key={r.id} positions={r.geometry}
            pathOptions={{ color: colorOf(r.id), weight: active ? 7 : 4, opacity: active ? 0.95 : 0.55,
              dashArray: r.recommended && !active ? '1 9' : undefined, lineCap: 'round' }}
            eventHandlers={{ click: () => onSelect(r.id) }}
          />
        )
      })}

      {routes
        .filter((r) => showAllCheckpoints || r.id === selectedId)
        .flatMap((r) =>
          r.checkpoints.map((c) => (
            <CircleMarker key={`${r.id}-${c.mile}`} center={[c.lat, c.lng]} radius={r.id === selectedId ? 6.5 : 4.5}
              pathOptions={{ color: '#fff', weight: 2, fillColor: LEVEL_BY_KEY[c.level].color, fillOpacity: 1 }}>
              <Popup>
                <strong>{r.label} · mile {Math.round(c.mile)}</strong><br />
                ETA {fmtTime(c.eta)}<br />
                Wind {c.wind_mph.toFixed(0)} mph · Rain {c.rain_in_hr.toFixed(2)} in/hr · Snow {c.snow_in_hr.toFixed(2)} in/hr<br />
                <strong style={{ color: LEVEL_BY_KEY[c.level].color }}>{LEVEL_BY_KEY[c.level].label}</strong>
                {c.reasons.length > 0 && <div className="popup-reasons">{c.reasons.join('; ')}</div>}
              </Popup>
            </CircleMarker>
          )),
        )}

      {data && routes[0] && (
        <>
          <Marker position={routes[0].geometry[0]} icon={pin('A')} />
          <Marker position={routes[0].geometry[routes[0].geometry.length - 1]} icon={pin('B')} />
        </>
      )}
    </MapContainer>
  )
}
