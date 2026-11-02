// A season is data: this entry plus public/models/<id>.glb and public/trees/<id>.json (plan §6.2).
// Colours are derived from the JSON's `palette` (see derive.ts); `overrides` is for hand tuning.
import type { Overrides } from './derive'
export type { Season } from './derive'

export interface SeasonEntry {
  id: string
  name: string
  overrides?: Overrides
}

const list: SeasonEntry[] = [
  {
    id: 'sakura',
    name: 'Sakura',
  },
  {
    id: 'autumn',
    name: 'Autumn',
  },
]

export const seasons: Record<string, SeasonEntry> = Object.fromEntries(list.map((s) => [s.id, s]))
export const DEFAULT_SEASON = 'sakura'
