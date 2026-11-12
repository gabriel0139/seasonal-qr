import { useGLTF } from '@react-three/drei'
import type { SyntheticEvent } from 'react'
import { seasons } from '../seasons'
import { CAPTIONS, GROUPS, modelHref, thumb } from './scenes'

interface Props {
  active: string
  pending: string | null
  onSeason: (id: string) => void
}

export const preload = (id: string) => useGLTF.preload(`/models/${id}.glb`)
// A scene without a rendered thumbnail (tools/thumbs.mjs not run yet) shows its name alone.
export const hideBroken = (e: SyntheticEvent<HTMLImageElement>) => (e.currentTarget.hidden = true)

/** Eight scenes as rendered plates, one row per season (one column per season on narrow screens). */
export function ScenePicker({ active, pending, onSeason }: Props) {
  return (
    <div>
      <fieldset className="picker">
        <legend className="label">Scene</legend>
        {GROUPS.map((g) => (
          <div className="group" key={g.name} role="group" aria-label={g.name}>
            <span className="season-tag" aria-hidden="true">
              <span lang="ja">{g.kanji}</span>
              {g.name}
            </span>
            {g.ids.map((id) => (
              <button
                key={id}
                type="button"
                className="pick"
                aria-pressed={id === active}
                aria-busy={id === pending}
                onClick={() => onSeason(id)}
                onPointerEnter={() => preload(id)}
                onFocus={() => preload(id)}
              >
                <img src={thumb(id)} alt="" width={56} height={56} onError={hideBroken} />
                <span>{seasons[id].name}</span>
              </button>
            ))}
          </div>
        ))}
      </fieldset>
      <p className="about">
        <span>{CAPTIONS[active] ?? seasons[active].name}</span>
        <a href={modelHref(active)} download={`seasonal-qr-${active}.glb`}>
          Download model (GLB, CC0)
        </a>
      </p>
    </div>
  )
}
