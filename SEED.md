# Seasonal QR — Seed Doc

_Last updated: 2026-11-01_

## What this is
An open-source, client-side creative coding project: a stylised seasonal 3D tree unfolds into a real, scannable QR code for any URL or text the visitor enters. Desktop-first, no backend. Goal: portfolio piece + open-source community project. Art direction: tile tree (trees built from the QR tiles, stored as voxel slot clouds).

## Stack & environment
- Vite + React + TypeScript (Next.js static export acceptable if preferred)
- Three.js + React Three Fiber + Drei; GSAP for the timeline and camera; custom instanced shader for tile motion
- `qrcode` (node-qrcode) for encoding; ZXing JS + jsQR for decode tests
- Vitest (QR engine, mapping) + Playwright (render → screenshot → decode)
- Trees as slot-cloud files (MagicaVoxel or voxelised Blender), platform/props as optimised GLB
- Static hosting (GitHub Pages / Cloudflare Pages / Vercel)
- Plan: `seasonal-qr-project-plan.md` · Decisions: `running_decisions.md`

## Conventions & hard constraints
- The final QR must scan. Any change that breaks the CI decode matrix doesn't merge.
- The final state follows the scan-ready spec: orthographic top-down, whole-pixel modules, tone mapping off, unlit, zero gaps, no post-processing or particles, dark on light, quiet zone rendered as light tiles.
- The QR engine (`src/qr`) and mapping (`src/mapping`) are pure modules with no rendering imports.
- QR content never depends on the seed or theme.
- Everything runs locally; never upload or log user input. Share links use the URL fragment only.
- Every asset has an entry in `assets-manifest.json` (CI-enforced). Contributed trees/palettes must be CC BY 4.0 or CC0.
- Nothing that serves neither the portfolio nor the community (accounts, monetisation, invasive analytics).

## Current state
v2.1 plan written (goal and art direction confirmed). No code yet. First task: flat instanced QR grid + Playwright decode test, then placeholder-tree morph (plan §21).

## Known gotchas
- R3F's default tone mapping shifts colours and lowers contrast; set it off for final tiles.
- Tile count varies with QR version: (4v + 17 + 8)² tiles, ~1,100 at v2 to 4,225 at v10. Input is capped at v10, EC level M.
- Gaps between cubes and fractional module sizes can break decoding.
- Recording video in real time drops frames; record at a fixed timestep.
- Procedural Blender tree add-ons (Easy Tree, tree-gen) are GPL; check generated-output terms before use.

## Key files / links
- `seasonal-qr-project-plan.md` — full plan (§3 tile system, §5 scan-ready spec, §6 tests, §15 roadmap)
- `running_decisions.md` — decision log
- https://github.com/soldair/node-qrcode — encoder
- https://ephtracy.github.io/ — MagicaVoxel
