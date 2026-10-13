const timeFmt = new Intl.DateTimeFormat(undefined, {
  weekday: 'short', hour: 'numeric', minute: '2-digit',
})
export const fmtTime = (iso) => timeFmt.format(new Date(iso))
export const fmtDuration = (s) => {
  const m = Math.round(s / 60)
  return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`
}
export const fmtMi = (v) => `${Math.round(v).toLocaleString()} mi`
export const inputValue = (d) => {
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}
