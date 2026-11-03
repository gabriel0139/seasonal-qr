# Contributing

Thanks for helping. The contributions below are ordered from the quickest to the hardest. Start at the top if you are new.

## Ways to contribute

### (a) QR colour overrides for a season

Each season's QR colours are derived from its tree's palette. A season can hand-tune them instead by setting `overrides` on its entry in `src/seasons/index.ts`:

- `finalDark`: 8 hex colours, one per slot class (0 trunk, 1 to 3 canopy deep/mid/pale, 4 lawn, 5 wood, 6 stone, 7 pond water).
- `finalLight`: one hex colour for the light modules.
- `petals`: the slot classes whose tiles fall as particles.

Two checks run on the colours:

- `npm test` runs a unit test that enforces the brightness band: the darks sit in one narrow band and well below the light.
- `npm run test:scan` is the real gate. It renders each payload in headless Chromium and decodes it with two decoders, direct and degraded.

### (b) A new season tree

A tree is a GLB with this node contract:

- Y up, base top at y = 0, and everything within ±36 units in x and z.
- Root nodes `Trunk` (branches), `Blossoms` (the canopy), `Base` (the diorama plinth).
- Optional `Props`, with children `Bridge`, `Lantern`, `Rocks` and `Water` where the scene has them.

Import it with:

```sh
npm run tree:import -- <id> path/to/model.glb
```

The command copies the GLB to `public/models/<id>.glb`, samples `public/trees/<id>.json` from it, and fails with a message if the contract is not met. Then:

1. Add a registry entry (`id`, `name`) to `src/seasons/index.ts`.
2. Add a manifest entry to `assets-manifest.json` (see Licences below).
3. Run `npm run test:scan`. CI decodes every season that has a GLB, so no test changes are needed.

The built-in trees come from Blender scripts in `tools/tree-build/`. To make one that way, copy an existing script (`summer.py` is the simplest), run `npm run tree:build`, and check it with `npm run tree:open -- <id>`. Blender is needed only for that path. `.blend` files are not committed; the script is the source.

### (c) Code

Animation polish, a Lite mode for weak GPUs, new exporters, and accessibility fixes are all welcome. Open an issue first for anything larger than a fix.

## Licences

- Contributed assets (GLB, JSON, images, fonts) must be CC BY 4.0 or CC0 1.0. Say which one in the manifest.
- Code is MIT, as in `package.json`.
- Every asset needs an entry in `assets-manifest.json` with `path` (or `slots` for a tree JSON), `licence`, `author` and `generated`. CI checks that each file has an entry, that the files exist, and that the licence and author are set.

## Running it

From the README:

```sh
npm ci                 # install dependencies
npm run dev            # start the dev server
npm test               # unit tests (vitest)
npm run test:scan      # scan tests: render, then decode with two independent decoders
```

A change that breaks the decode matrix does not merge, whatever else it does well.

## Pull request checklist

The PR template repeats this list. Tick every item before asking for review:

- [ ] Assets are CC BY 4.0 or CC0 and have a manifest entry.
- [ ] A credit name is in the manifest and the PR description.
- [ ] Screenshots of the tree state and the QR state are in the PR.
- [ ] `npm test` passes.
- [ ] `npm run test:scan` passes.

CI does the correctness checks, so review focuses on taste and on the code.
