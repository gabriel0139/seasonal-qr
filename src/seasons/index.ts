// A season is data: this entry plus public/models/<id>.glb and public/trees/<id>.json (plan §6.2).
// Colours are derived from the JSON's `palette` (see derive.ts); `overrides` is for hand tuning.
import type { Overrides } from './derive'
export type { Season } from './derive'

export interface SeasonEntry {
  id: string
  name: string
  overrides?: Overrides
}

// The shipped seasons use hand-tuned QR colours (Gabriel preferred them over the derived ones);
// a season without overrides gets colours derived from its JSON palette.
const list: SeasonEntry[] = [
  {
    id: 'sakura',
    name: 'Sakura',
    overrides: {
      finalDark: ['#3a2218', '#8c1f52', '#962758', '#a02f60', '#3a2218', '#5e2f14', '#3d4049', '#173f66'],
      finalLight: '#e9f0c4',
    },
  },
  {
    id: 'autumn',
    name: 'Autumn',
    overrides: {
      finalDark: ['#4a2a1c', '#7a1f12', '#7f2412', '#602a10', '#4a2a1c', '#5e2f14', '#3d4049', '#173f66'],
      finalLight: '#efe6c2',
    },
  },
]

export const seasons: Record<string, SeasonEntry> = Object.fromEntries(list.map((s) => [s.id, s]))
export const DEFAULT_SEASON = 'sakura'
