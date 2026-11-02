// Sakura palette. `tree` is indexed by Slot.paletteIndex for the tiles' start colours:
// 0 trunk, 1–3 blossom shades, 4 lawn, 5 wood, 6 stone, 7 pond water.
// The scan-ready QR is a mosaic: light modules and the quiet zone are `finalLight`, dark modules take
// `finalDark[paletteIndex]` of the tile's source. Every dark must stay deep and the light pale so the
// decoders' luminance threshold separates them; the CI decode matrix enforces it (plan §5.8).
export const sakura = {
  /** world units across the base top; the landed QR always spans this */
  baseSize: 72,
  tree: ['#5c3d2e', '#d9739b', '#efa3c0', '#f9d4e2', '#9bc24a', '#b8743f', '#9a9aa6', '#5aa9e0'],
  finalLight: '#e9f0c4',
  finalDark: ['#3a2218', '#8c1f52', '#962758', '#a02f60', '#3a2218', '#5e2f14', '#3d4049', '#173f66'],
}
