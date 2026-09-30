import L from 'leaflet'

// Shared Leaflet helpers for every map in the app (public map, landing
// preview, org hotspot map, location picker).

export const NEPAL_CENTER = [28.3949, 84.124]
// Loose bounding box around Nepal, used to frame the country on first load.
export const NEPAL_BOUNDS = [[26.2, 80.0], [30.6, 88.3]]

const OSM_TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

/** Standard OSM tiles. Dark mode is handled in CSS (see main.css
 * `.dark .leaflet-tile-pane`) so no second tile provider is needed. */
export function addBaseTiles(map) {
  return L.tileLayer(OSM_TILES, { attribution: OSM_ATTRIBUTION, maxZoom: 19 }).addTo(map)
}

/** Everything interpolated into Leaflet HTML (tooltips, popups, divIcons)
 * must go through this — names, titles and excerpts are user-supplied, and
 * Leaflet renders strings as raw HTML (same spirit as the no-v-html rule). */
export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ))
}

/** Teardrop pin. `badge` (a number) renders a small count bubble. */
export function pinIcon({ color = '#E63946', size = 30, badge = null, ring = false } = {}) {
  const h = Math.round(size * 1.4)
  const badgeHtml = badge != null && badge > 0
    ? `<span class="gmap-pin-badge">${escapeHtml(badge > 99 ? '99+' : badge)}</span>`
    : ''
  return L.divIcon({
    className: 'gmap-pin',
    html: `<div class="gmap-pin-inner${ring ? ' gmap-pin-active' : ''}" style="width:${size}px;height:${h}px">
      <svg width="${size}" height="${h}" viewBox="0 0 30 42" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M15 0C6.7 0 0 6.7 0 15c0 11.2 15 27 15 27s15-15.8 15-27C30 6.7 23.3 0 15 0z" fill="${color}"/>
        <circle cx="15" cy="15" r="6" fill="white"/>
      </svg>${badgeHtml}</div>`,
    iconSize: [size, h],
    iconAnchor: [size / 2, h],
    popupAnchor: [0, -h + 4],
    tooltipAnchor: [0, -h],
  })
}

/** Small round dot for secondary markers (e.g. branches). */
export function dotIcon({ color = '#1D3557', size = 14 } = {}) {
  return L.divIcon({
    className: 'gmap-dot',
    html: `<span style="display:block;width:${size}px;height:${size}px;border-radius:9999px;background:${color};border:2.5px solid #fff;box-shadow:0 1px 4px rgb(0 0 0 / .35)"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
    tooltipAnchor: [0, -size / 2],
  })
}

/** Great-circle distance in km. */
export function haversineKm([lat1, lng1], [lat2, lng2]) {
  const toRad = (d) => (d * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return 6371 * 2 * Math.asin(Math.sqrt(a))
}

export function formatDistance(km) {
  if (km == null) return ''
  return km < 1 ? `${Math.round(km * 1000)} m` : `${km < 10 ? km.toFixed(1) : Math.round(km)} km`
}

let clusterPluginPromise = null
/** leaflet.markercluster is a UMD bundle that patches a *global* `L`, so
 * expose ours first, then load it lazily (also keeps it out of pages
 * without clustering). Resolves to the patched `L`. */
export function loadClusterPlugin() {
  if (!clusterPluginPromise) {
    window.L = L
    clusterPluginPromise = Promise.all([
      import('leaflet.markercluster'),
      import('leaflet.markercluster/dist/MarkerCluster.css'),
    ]).then(() => L)
  }
  return clusterPluginPromise
}
