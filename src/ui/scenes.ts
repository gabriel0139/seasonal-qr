import { seasons } from '../seasons'

// Picker and gallery groups. A registry scene missing here still shows, under "More".
const KNOWN = [
  { name: 'Spring', kanji: '春', ids: ['sakura', 'bunny'] },
  { name: 'Summer', kanji: '夏', ids: ['summer', 'sunflower'] },
  { name: 'Autumn', kanji: '秋', ids: ['autumn', 'pumpkin'] },
  { name: 'Winter', kanji: '冬', ids: ['winter', 'snowman'] },
]
const rest = Object.keys(seasons).filter((id) => !KNOWN.some((g) => g.ids.includes(id)))
export const GROUPS = [...KNOWN.map((g) => ({ ...g, ids: g.ids.filter((id) => seasons[id]) })), ...(rest.length ? [{ name: 'More', kanji: '庭', ids: rest }] : [])]

export const groupOf = (id: string) => GROUPS.find((g) => g.ids.includes(id)) ?? GROUPS[0]

export const CAPTIONS: Record<string, string> = {
  sakura: 'Cherry blossom and a picnic by the pond',
  bunny: 'Egg hunt in a spring meadow',
  summer: 'A shade tree by the swimming hole',
  sunflower: 'Sunflowers and vegetable beds',
  autumn: 'A maple in the temple garden',
  pumpkin: 'Jack-o’-lantern in the patch',
  winter: 'A garden under snow',
  snowman: 'A snowman’s clearing',
}

/** The untouched GLB: production serves meshopt-compressed models, which Blender cannot import. */
export const modelHref = (id: string) => (import.meta.env.DEV ? `/models/${id}.glb` : `/downloads/${id}.glb`)

export const thumb = (id: string) => `/thumbs/${id}.webp`
