import { seasons } from '../seasons'
import { hideBroken, preload } from './ScenePicker'
import { CAPTIONS, GROUPS, modelHref, thumb } from './scenes'

const REPO = 'https://github.com/gabriel0139/seasonal-qr'

const BEATS = [
  ['Hidden in the model', 'Every module of the code starts as a leaf tucked inside the scene: dark modules in the tree and props, light ones in the lawn. Up to 4,225 of them.'],
  ['Shed from the top down', 'The scene crumbles from the crown down. Leaves curl out on bowed paths and the three finder squares land first, so the code is recognisable early.'],
  ['Settled into a mosaic', 'Each leaf tumbles flat and grows to exactly one module, in a deep shade of its own colour, while the camera lifts to look straight down.'],
  ['Checked by two decoders', 'The last frame is flat colour on whole pixels. On every change, CI renders each scene with five payloads and both jsQR and ZXing must read them, sharp and camera-blurred.'],
]

interface Props {
  active: string
  onSeason: (id: string) => void
}

/** Below the first screen: how it works, the eight scenes, the open-source side. */
export function Story({ active, onSeason }: Props) {
  function show(id: string) {
    onSeason(id)
    const smooth = !matchMedia('(prefers-reduced-motion: reduce)').matches
    document.getElementById('top')?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' })
  }

  return (
    <>
      <section className="chapter" id="how" aria-labelledby="how-title">
        <div className="chapter-head">
          <span className="label">How it works</span>
          <h2 id="how-title">Every leaf is one module of the code.</h2>
        </div>
        <ol className="beats">
          {BEATS.map(([title, body], i) => (
            <li className="beat" key={title}>
              <img src={`/story/${i + 1}.webp`} alt="" width={480} height={480} loading="lazy" onError={hideBroken} />
              <h3>{title}</h3>
              <p>{body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="chapter" id="scenes" aria-labelledby="scenes-title">
        <div className="chapter-head">
          <span className="label">The scenes</span>
          <h2 id="scenes-title">Eight scenes, two for each season.</h2>
          <p>The page opens on the one for today’s date. Each is a small Blender diorama with its own palette, and the code lands in deep shades of it.</p>
        </div>
        <div className="gallery">
          {GROUPS.map((g) => (
            <div className="column" key={g.name}>
              <h3>
                <span lang="ja" aria-hidden="true">
                  {g.kanji}
                </span>
                {g.name}
              </h3>
              {g.ids.map((id) => (
                <article className="card" key={id} data-active={id === active || undefined}>
                  <button type="button" onClick={() => show(id)} onPointerEnter={() => preload(id)} onFocus={() => preload(id)} aria-label={`Show ${seasons[id].name}`}>
                    <img src={thumb(id)} alt="" width={400} height={400} loading="lazy" onError={hideBroken} />
                  </button>
                  <h4>
                    {seasons[id].name}
                    {id === active && <small>Showing</small>}
                  </h4>
                  <p>{CAPTIONS[id] ?? ''}</p>
                  <a href={modelHref(id)} download={`seasonal-qr-${id}.glb`}>
                    Download model (GLB, CC0)
                  </a>
                </article>
              ))}
            </div>
          ))}
        </div>
      </section>

      <section className="chapter" id="source" aria-labelledby="source-title">
        <div className="chapter-head">
          <span className="label">Open source</span>
          <h2 id="source-title">Take it apart, plant your own.</h2>
        </div>
        <div className="open">
          <article>
            <h3>The code</h3>
            <p>MIT licensed. React Three Fiber and GSAP: one timeline drives every tile on the GPU, so the reveal scrubs, reverses and exports to video at a fixed frame rate.</p>
            <a className="more" href={REPO}>
              Source on GitHub ↗
            </a>
          </article>
          <article>
            <h3>Use the models</h3>
            <p>
              All eight dioramas are CC0 1.0: use them in anything, no credit needed. Each is a plain GLB (Y up, 1 unit = 1 QR module, flat PBR colours, no textures) with named nodes <code>Trunk</code>, <code>Blossoms</code>, <code>Base</code> and <code>Props</code>, so it opens in Blender, three.js, Godot or Unity. The Blender Python scripts that build them are in <code>tools/tree-build/</code>, to rebuild or remix.
            </p>
            <a className="more" href={`${REPO}/blob/main/MODELS.md`}>
              About the models ↗
            </a>
          </article>
          <article>
            <h3>Add a scene</h3>
            <p>Model it in anything and export a GLB with those node names. One command samples its tiles; CI renders it, decodes it with both decoders and attaches screenshots to your pull request.</p>
            <pre>
              <code>npm run tree:import -- maple my-maple.glb</code>
            </pre>
            <a className="more" href={`${REPO}/blob/main/CONTRIBUTING.md`}>
              How to contribute ↗
            </a>
          </article>
        </div>
      </section>
    </>
  )
}
