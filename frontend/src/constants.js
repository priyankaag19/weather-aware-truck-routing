// Order matches the backend's risk scores 0..4.
export const LEVELS = [
  { key: 'low', label: 'Low', color: '#2f9e5f' },
  { key: 'moderate', label: 'Moderate', color: '#e2b007' },
  { key: 'high', label: 'High', color: '#f08a00' },
  { key: 'severe', label: 'Severe', color: '#d63b2d' },
  { key: 'no_travel', label: 'No Travel', color: '#6a1fa6' },
]
export const LEVEL_BY_KEY = Object.fromEntries(LEVELS.map((l) => [l.key, l]))
export const ROUTE_COLORS = ['#1b64c8', '#0f8f8a', '#8a4fd1']
export const INTERVALS = [10, 25, 50]
export const EXAMPLE = {
  origin: { label: 'Chicago, Illinois', lat: 41.8781, lng: -87.6298 },
  destination: { label: 'Denver, Colorado', lat: 39.7392, lng: -104.9903 },
}
