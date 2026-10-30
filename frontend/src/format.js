export function runtime(min) {
  if (!min) return ''
  const h = Math.floor(min / 60)
  const m = min % 60
  return h ? `${h}h ${m}m` : `${m}m`
}

export function initials(title = '') {
  return title.split(/\s+/).filter((w) => /^[A-Za-z0-9]/.test(w)).slice(0, 2).map((w) => w[0].toUpperCase()).join('')
}

// A stable colour for movies without a poster.
export function colourFor(text = '') {
  let h = 0
  for (const c of text) h = (h * 31 + c.charCodeAt(0)) % 360
  return `hsl(${h} 45% 28%)`
}

export function money(musd) {
  if (musd === null || musd === undefined) return null
  return musd >= 1000 ? `$${(musd / 1000).toFixed(2)} B` : `$${Math.round(musd)} M`
}
