// A season is data: this entry plus public/models/<id>.glb and public/trees/<id>.json (plan §6.2).
// Colours are derived from the JSON's `palette` (see derive.ts); `overrides` is for hand tuning.
import type { Overrides } from './derive'
export type { Season } from './derive'

export interface SeasonEntry {
  id: string
  name: string
  overrides?: Overrides
}

// The shipped scenes use hand-tuned QR colours (Gabriel preferred them over the derived ones);
// a scene without overrides gets colours derived from its JSON palette.
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
    id: 'bunny',
    name: 'Bunny',
    overrides: {
      finalDark: ['#5e3a1c', '#7a4424', '#9b2c5e', '#5b3a8c', '#5e3a1c', '#5e2f14', '#3d4049', '#173f66'], // wicker, fawn, ear pink, egg lilac
      finalLight: '#e9f0c4',
      petals: [2, 3],
    },
  },
  { id: 'summer', name: 'Summer' },
  {
    id: 'sunflower',
    name: 'Sunflowers',
    overrides: {
      finalDark: ['#2c531c', '#5a3216', '#7d4004', '#6e4a00', '#2c531c', '#5e2f14', '#3d4049', '#173f66'], // stalk, seed disc, ambers
      finalLight: '#f6efc4',
      petals: [2, 3],
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
  {
    id: 'pumpkin',
    name: 'Pumpkin',
    overrides: {
      finalDark: ['#3a4a1c', '#7a2a0c', '#96400c', '#8a3a0a', '#3a4a1c', '#5e2f14', '#3d4049', '#173f66'], // vine, burnt oranges
      finalLight: '#f3e9c8',
    },
  },
  { id: 'winter', name: 'Winter', overrides: { petals: [3] } }, // snowflakes
  {
    id: 'snowman',
    name: 'Snowman',
    overrides: {
      finalDark: ['#3a3b44', '#1f3f6e', '#24497c', '#9b1f2a', '#3a3b44', '#742c20', '#3d4049', '#173f66'], // hat, snow-shadow navies, scarf red
      finalLight: '#eef3fa',
      petals: [3], // snowflakes
    },
  },
]

export const seasons: Record<string, SeasonEntry> = Object.fromEntries(list.map((s) => [s.id, s]))

// Northern-hemisphere astronomical seasons: equinoxes and solstices rounded to a fixed day
// (shortcut: the true dates drift by a day with the year; upgrade to a computed equinox if that ever matters).
const STARTS: [number, number, string][] = [[3, 20, 'sakura'], [6, 21, 'summer'], [9, 22, 'autumn'], [12, 21, 'winter']]

// Companion scenes win over the tree inside these inclusive [month, day] windows; a window with start > end wraps the year.
// shortcut: Easter moves each year, so bunny gets a fixed window; compute Easter if that ever matters.
const WINDOWS: [[number, number], [number, number], string][] = [
  [[3, 25], [4, 20], 'bunny'],
  [[7, 20], [8, 20], 'sunflower'],
  [[10, 15], [11, 1], 'pumpkin'],
  [[12, 10], [1, 6], 'snowman'],
]

/** The scene `date` (local time) falls in: a companion scene inside its window, else the season's tree (before the spring equinox it is still winter). */
export function seasonFor(date = new Date()): string {
  const m = date.getMonth() + 1
  const d = date.getDate()
  const md = m * 100 + d
  const win = WINDOWS.find(([[sm, sd], [em, ed]]) => {
    const [s, e] = [sm * 100 + sd, em * 100 + ed]
    return s <= e ? md >= s && md <= e : md >= s || md <= e
  })
  if (win) return win[2]
  return STARTS.filter(([sm, sd]) => m > sm || (m === sm && d >= sd)).pop()?.[2] ?? 'winter'
}
