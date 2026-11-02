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
  { id: 'summer', name: 'Summer' },
  { id: 'winter', name: 'Winter', overrides: { petals: [3] } }, // snowflakes
]

export const seasons: Record<string, SeasonEntry> = Object.fromEntries(list.map((s) => [s.id, s]))

// Northern-hemisphere astronomical seasons: equinoxes and solstices rounded to a fixed day
// (shortcut: the true dates drift by a day with the year; upgrade to a computed equinox if that ever matters).
const STARTS: [number, number, string][] = [[3, 20, 'sakura'], [6, 21, 'summer'], [9, 22, 'autumn'], [12, 21, 'winter']]

/** The season `date` (local time) falls in; before the spring equinox it is still winter. */
export function seasonFor(date = new Date()): string {
  const m = date.getMonth() + 1
  const d = date.getDate()
  return STARTS.filter(([sm, sd]) => m > sm || (m === sm && d >= sd)).pop()?.[2] ?? 'winter'
}
