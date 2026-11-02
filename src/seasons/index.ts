// A season is data: this entry plus public/models/<id>.glb and public/trees/<id>.json (plan §6.2).
// `tree` is indexed by Slot.paletteIndex for the tiles' start colours:
// 0 trunk, 1–3 canopy shades, 4 lawn, 5 wood, 6 stone, 7 pond water.
// The scan-ready QR is a mosaic: light modules and the quiet zone are `finalLight`, dark modules take
// `finalDark[paletteIndex]` of the tile's source. Every dark must stay deep and the light pale so the
// decoders' luminance threshold separates them; the CI decode matrix enforces it (plan §5.8).
export interface Season {
  /** URL id and file stem */
  id: string
  /** UI label */
  name: string
  tree: string[]
  finalDark: string[]
  finalLight: string
  /** world units across the base top; the landed QR always spans this */
  baseSize: number
  /** slot classes whose `tree` colours the falling particles use */
  petals: number[]
}

const list: Season[] = [
  {
    id: 'sakura',
    name: 'Sakura',
    tree: ['#5c3d2e', '#d9739b', '#efa3c0', '#f9d4e2', '#9bc24a', '#b8743f', '#9a9aa6', '#5aa9e0'],
    finalDark: ['#3a2218', '#8c1f52', '#962758', '#a02f60', '#3a2218', '#5e2f14', '#3d4049', '#173f66'],
    finalLight: '#e9f0c4',
    baseSize: 72,
    petals: [1, 2, 3],
  },
  {
    id: 'autumn',
    name: 'Autumn',
    tree: ['#3b2a22', '#b3341e', '#d9542a', '#e8873a', '#a8b84a', '#8a5a3a', '#8d8d99', '#5aa9e0'],
    finalDark: ['#4a2a1c', '#7a1f12', '#7f2412', '#602a10', '#4a2a1c', '#5e2f14', '#3d4049', '#173f66'],
    finalLight: '#efe6c2',
    baseSize: 72,
    petals: [1, 2, 3],
  },
]

export const seasons: Record<string, Season> = Object.fromEntries(list.map((s) => [s.id, s]))
export const DEFAULT_SEASON = 'sakura'
