"""Build the summer diorama: public/models/summer.glb + public/trees/summer.json.

Run from the repo root: Blender -b -P tools/tree-build/summer.py (Blender 5.2, headless). Deterministic (fixed SEED).
This file is the season: a stout shade tree (camphor / zelkova) under a broad, deep-green crown of layered foliage
puffs, a vivid lawn and hydrangea-coloured flowers. The base, props, slot cloud, self-checks and export are shared
with the other seasons in diorama.py.
"""
import math, os, sys
sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh, bpy
from mathutils import Vector, Matrix, noise
import diorama as D
from diorama import bez, lerp, horiz, wobbly, rng

SEED = 20260721
D.init(SEED)
COLOURS = {  # scenery material -> hex sRGB
    'Moss': '8fc83c', 'Stone': 'c9b8a0', 'PondBed': '3f7a6a', 'StoneChunk': '948572',
    'PondBank': '5f9a34', 'RimStone': 'bcae9a', 'RimStoneLight': 'd6cab8', 'Water': '7fd0ee',
    'FlowerCentre': 'f2c84b', 'LilyPad': '3f8f3a', 'Lotus': 'f6b7cf', 'Wood': '9c6b47', 'WoodDark': '6e4932',
    'LanternGlow': 'ffe2a0', 'LanternStone': 'bdb2a2', 'RockGrey': 'a39d93', 'RockPink': 'b0a496',
    'GrassDark': '4f9a2c', 'GrassLight': '9fd04a', 'MossDark': '7fba34', 'MossLight': 'a2d24a',
    'FlowerWhite': 'fbfaf4', 'FlowerLavender': '7d8fe8', 'Stem': '4f8f2e',
}

# ---------- trunk: a stout, nearly upright stem that forks into a few strong limbs reaching out and up ----------
SPLIT = Vector((0.6, -0.3, 13.0))


def axis(t):
    return bez(Vector((0, 0, -1.5)), Vector((-1.0, 0.5, 4.0)), Vector((1.5, -0.8, 9.0)), SPLIT, t)


MAIN = [  # azimuth deg, horizontal reach from the split, tip height, foliage cluster size
    (15, 17.0, 25.5, 9.0),
    (85, 14.5, 27.5, 8.5),
    (160, 17.0, 25.0, 9.0),
    (230, 15.5, 26.5, 9.0),
    (305, 16.5, 25.5, 9.0),
    (50, 4.0, 33.0, 9.5),  # leader
]
SECOND = [  # main branch, position along it, azimuth offset deg, length, rise, cluster size
    (0, 0.55, -50, 9, 3, 7.0), (1, 0.55, 50, 8, 4, 6.5), (2, 0.55, 45, 9, 3, 7.0),
    (3, 0.55, -45, 8, 4, 7.0), (4, 0.55, 50, 9, 3, 7.0), (2, 0.75, -50, 7, 5, 6.5),
]
splines, clusters, branches, tips = [], [], [], []

for i, (az_deg, reach, tip_z, size) in enumerate(MAIN):
    az = math.radians(az_deg)
    pts = [axis(k / 32) + horiz(az - 1.0 + 0.6 * k / 32) * lerp(1.9, 1.0, k / 32) for k in range(33)]
    rad = [lerp(2.5, 1.9, k / 32) * (1 + 0.15 * math.exp(-((k / 32 - 0.3) / 0.1) ** 2)) for k in range(33)]
    p0 = pts[-1]
    tip = SPLIT + horiz(az) * reach
    tip.z = tip_z
    L = (tip - p0).length
    d0 = (axis(1) - axis(0.9)).normalized()
    bp, br = wobbly(p0, p0 + (d0 * 0.8 + horiz(az)).normalized() * L * 0.35,
                    tip - horiz(az) * L * 0.35 - Vector((0, 0, L * 0.08)), tip, 1.8, 0.6, 1.6, i)
    splines.append((pts + bp, rad + br))
    branches.append((bp, br, az))
    clusters.append((tip + Vector((0, 0, size * 0.3)), size))
    tips.append(tip)

FILL = [((9, 6, 30.5), 7.5), ((-8, 7, 30.5), 7.5), ((-8, -8, 29.5), 7.5), ((8, -8, 29.5), 7.5),  # dome gaps
        ((0, 0, 29.0), 8.0), ((15, 0, 21.5), 7.0), ((-15, 1, 21.5), 7.0), ((1, 15, 21.5), 7.0), ((1, -15, 21.5), 7.0)]
clusters += [(Vector(c), s) for c, s in FILL]

splines.append(([axis(k / 32) for k in range(33)], [lerp(2.5, 2.0, k / 32) for k in range(33)]))  # solid core

for j, (mi, at, off, length, rise, size) in enumerate(SECOND):
    bp, br, az = branches[mi]
    k = int(at * (len(bp) - 1))
    p0, r0 = bp[k], br[k] * 0.75
    a = az + math.radians(off)
    tip = p0 + horiz(a) * length + Vector((0, 0, rise))
    pts, rad = wobbly(p0, p0 + horiz(a) * length * 0.4, tip - Vector((0, 0, rise * 0.5)), tip, r0, 0.3, 0.8, 10 + j)
    splines.append(([p0] + pts, [r0] + rad))
    clusters.append((tip + Vector((0, 0, size * 0.3)), size))
    tips.append(tip)

a0 = axis(0.2)
for k in range(6):  # buttress roots sinking into the soil
    phi = math.radians(k * 60 + 20 + rng.uniform(-12, 12))
    a = a0 + horiz(phi) * 1.0
    c = Vector((a0.x, a0.y, -1.0)) + horiz(phi) * rng.uniform(5.0, 6.5)
    pts, rad = wobbly(a, a + horiz(phi) * 1.5 - Vector((0, 0, 1.5)), c - horiz(phi) * 2 + Vector((0, 0, 0.6)), c,
                      1.8, 0.35, 0.3, 20 + k)
    splines.append(([a] + pts, [1.8] + rad))

trunk = D.trunk_mesh(splines, '3a2b22')

# ---------- foliage: sphere puffs; one voxel-unioned shell per green so colour seams sit in the creases ----------
PINKS = [D.material(n, h) for n, h in (('Leaf_Deep', '2c6a35'), ('Leaf_Mid', '4a9a3a'),
                                       ('Leaf_Light', '78b83e'), ('Leaf_Sun', 'b2d24c'))]


def puff(bm, c, s):
    def ball(p, r):
        bmesh.ops.create_icosphere(bm, subdivisions=3 if r > 2 else 2, radius=r, matrix=Matrix.Translation(p))
    ball(c, s * 0.68)
    for _ in range(10):
        lc = c + D.rand_dir(0.15) * Vector((s * 0.55, s * 0.55, s * 0.4))
        lr = s * rng.uniform(0.42, 0.58)
        ball(lc, lr)
        for _ in range(6):  # small florets half-buried in each lobe
            ball(lc + D.rand_dir(0.3) * lr * 0.82, s * rng.uniform(0.18, 0.26))


cmax = max(c.z for c, _ in clusters)
cmin = min(c.z for c, _ in clusters)
level = [max(0, min(3, int(0.5 + 3 * (c.z - cmin) / (cmax - cmin) + rng.uniform(-0.9, 0.9)))) for c, _ in clusters]
shells = []
for lv in range(4):  # higher clusters sunnier
    bm = bmesh.new()
    for (c, s), l in zip(clusters, level):
        if l == lv:
            puff(bm, c, s)
    assert bm.verts, f'no cluster uses pink {lv}'
    me = bpy.data.meshes.new('shell')
    bm.to_mesh(me)
    bm.free()
    shells.append(D.link(f'LeafShell{lv}', me))
    D.voxel_union(shells[-1], 0.32, displace=0.3)
    D.florets(shells[-1], 0.5, 0.45, 1.05)
    D.voxel_union(shells[-1], 0.2)
leafs = D.canopy_mesh(shells, PINKS, 165000)

D.finish('summer', COLOURS, trunk, shells, leafs, tips, a0)
