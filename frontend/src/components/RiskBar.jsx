import { LEVELS } from '../constants'

export default function RiskBar({ milesByLevel }) {
  const total = Object.values(milesByLevel).reduce((a, b) => a + b, 0) || 1
  return (
    <div className="riskbar" role="img" aria-label="Miles by risk level">
      {LEVELS.map((l) => {
        const mi = milesByLevel[l.key]
        return mi > 0 ? (
          <span key={l.key} style={{ width: `${(mi / total) * 100}%`, background: l.color }} title={`${l.label}: ${Math.round(mi)} mi`} />
        ) : null
      })}
    </div>
  )
}
