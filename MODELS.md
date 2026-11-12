# The models

The eight dioramas are free to take. They are dedicated to the public domain under [CC0 1.0](LICENSE-CC0): use them in games, renders, prints, teaching or anything else, commercial or not, with no credit required. (Credit is welcome: "Seasonal QR contributors".)

| id | Scene | Setting |
|---|---|---|
| `sakura` | Cherry tree in full bloom | Hanami garden: pond, arched bridge, stone lantern, picnic under a parasol, paper lanterns, petal drifts |
| `bunny` | Rabbit with a basket of painted eggs | Egg-hunt meadow: burrow, carrot patch, tulips, daffodils, toadstools |
| `summer` | Broad shade tree | Swimming hole: jetty, rowing boat, rope swing, hammock, picnic, kite |
| `sunflower` | Stand of giant sunflowers | Kitchen garden: picket fence, soil beds, beehive, wheelbarrow, rain barrel |
| `autumn` | Leaning Japanese maple | Temple garden: plaster wall, stepping stones across the pond, parasol and bench, leaf piles, pampas grass |
| `pumpkin` | Glowing jack-o'-lantern | Harvest patch: rail fence with a crow, corn shocks, hay bales, vines and gourds |
| `winter` | Bare zelkova under snow | Snow garden: half-frozen pond, vermilion bridge, snow-viewing lantern, snow hut, pine under a rope tent |
| `snowman` | Snowman with hat, scarf and broom | Snowy clearing: firs, snow fort, skating rink, log pile, sledge |

## Getting the files

- **From the repository:** `public/models/<id>.glb`. These are the originals, exactly as Blender exported them.
- **From the website:** the "Download model" link on each scene. It serves the same original from `/downloads/<id>.glb`.

The site itself loads a Meshopt-compressed copy from `/models/<id>.glb` (about a quarter of the size). three.js reads that with a Meshopt decoder, but Blender does not import Meshopt-compressed files, so use the originals for editing.

## What is in a file

- glTF 2.0 binary (`.glb`), Y up, 2.4–3.5 MB, 110–180k triangles. One unit is one QR tile; the base is 72 × 72 units with its top at y = 0.
- No textures and no UVs: every material is a flat PBR colour, so the files recolour easily. `Water` is the only transparent material; lantern fireboxes, the jack-o'-lantern's face and candlelight are emissive.
- No animation or rigging. The reveal on the site is a shader in the app, not part of the model.
- Named root nodes: `Trunk` (the dark structural part: a trunk, a basket, a hat), `Blossoms` (the main body: canopy, rabbit, pumpkins, snowballs), `Base` (the tiered slab) and `Props` (a group of scenery meshes such as `Bridge`, `Lantern`, `Rocks`, `Grass`, `Flowers`). Take the centrepiece alone by keeping `Trunk` and `Blossoms`.

Beside each model sits `public/trees/<id>.json`, the cloud of points sampled inside it that the site uses as tile start positions. You only need it for the QR morph; its format is in the [README](README.md#adding-a-season).

## Using them

**Blender:** File → Import → glTF 2.0, pick the `.glb`. Blender converts to Z up on import.

**three.js:**

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

const { scene } = await new GLTFLoader().loadAsync('sakura.glb')
scene.getObjectByName('Props').visible = false // just the tree on its base
```

**React Three Fiber:** `const { scene } = useGLTF('/sakura.glb')`, then `<primitive object={scene} />`.

**Godot, Unity, Unreal, Babylon.js:** import the `.glb` as any other glTF file. Scale to taste: the scenes are 72 units wide.

Light them with one warm sun and a cool sky fill; the colours are tuned for that, without tone mapping.

## Rebuilding and remixing

There are no `.blend` files: each scene is a Python script, `tools/tree-build/<id>.py`, on top of the shared builder `tools/tree-build/diorama.py`. With Blender 5.2:

```sh
npm run tree:open -- sakura     # open the built scene in the Blender UI to look around or edit by hand
/Applications/Blender.app/Contents/MacOS/Blender -b -P tools/tree-build/sakura.py   # rebuild the GLB and slot file
npm run tree:build              # rebuild all eight
```

The scripts are deterministic (fixed seeds), MIT-licensed like the rest of the code, and meant to be read: change a colour table, a branch list or a prop and rebuild. On Linux or Windows, point the commands at your own Blender binary (`BLENDER=/path/to/blender` for `tree:open`).

To make a scene of your own for the site, from a script or from any GLB you have modelled by hand, follow [Adding a season](README.md#adding-a-season) and [CONTRIBUTING.md](CONTRIBUTING.md).
