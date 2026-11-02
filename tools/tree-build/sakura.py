"""Build the sakura diorama: public/models/sakura.glb + public/trees/sakura.json.

Run from the repo root: npm run tree:build (Blender 5.2, headless). Deterministic (fixed SEED).
This file is the season: a twisted cherry trunk, round blossom puffs and the scenery colours. The base, props,
slot cloud, self-checks and export are shared with the other seasons in diorama.py.
"""
import math, os, sys
sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh, bpy
from mathutils import Vector, Matrix, noise
import diorama as D
from diorama import bez, lerp, horiz, wobbly, rng

SEED = 20261102
D.init(SEED)
COLOURS = {  # scenery material -> hex sRGB
    'Moss': 'a7b950', 'Stone': 'c6a9a2', 'PondBed': '4e7a68', 'StoneChunk': '9a7f79',
    'PondBank': '7f8d45', 'RimStone': 'b9a7a1', 'RimStoneLight': 'd3c3bc', 'Water': '9fd6ea',
    'FlowerCentre': 'f2c84b', 'LilyPad': '5f9b48', 'Lotus': 'f3a2c0', 'Wood': '9c6b47', 'WoodDark': '6e4932',
    'LanternGlow': 'ffe2a0', 'LanternStone': 'bdb0a8', 'RockGrey': 'a39b98', 'RockPink': 'bba7a1',
    'GrassDark': '7f9c3c', 'GrassLight': 'b8cc5c', 'MossDark': '9db14a', 'MossLight': 'b0c156',
    'FlowerWhite': 'faf7f0', 'FlowerLavender': 'b7a2e4', 'Stem': '6c9a3a',
}

# ---------- trunk and branches: one POLY spline per strand / branch / root / burl ----------
SPLIT = Vector((2.0, -0.5, 17.0))
TWIST = math.radians(230)  # strands wind around each other up the trunk, then fork into the main branches


def axis(t):  # S-bend: leans left low down, then sweeps back right into the fork
    return bez(Vector((0, 0, -1.5)), Vector((-7.5, 3.0, 6.5)), Vector((8.0, -3.5, 11.5)), SPLIT, t)


MAIN = [  # azimuth deg, horizontal reach from the split, tip height, blossom cluster size, knot position on its strand
    (10, 16.0, 30.5, 8.0, 0.30),
    (95, 13.0, 33.5, 7.5, 0.62),
    (190, 16.5, 29.5, 8.0, 0.45),
    (275, 12.5, 32.5, 7.5, 0.18),
    (40, 3.0, 37.5, 9.0, 0.78),  # leader
]
SECOND = [  # main branch, position along it, azimuth offset deg, length, rise, cluster size
    (0, 0.55, -55, 8, 4, 5.5),
    (1, 0.50, 50, 7, 5, 5.0),
    (2, 0.50, 50, 8, 3, 5.5),
    (2, 0.70, -45, 6, 5, 5.0),
    (3, 0.55, -50, 7, 4, 5.0),
]
splines, clusters, branches, tips = [], [], [], []

for i, (az_deg, reach, tip_z, size, knot) in enumerate(MAIN):
    az = math.radians(az_deg)
    pts, rad = [], []
    for k in range(33):
        t = k / 32
        q = axis(t) + horiz(az - TWIST + TWIST * t) * lerp(2.6, 1.2, t)
        pts.append(q + noise.noise_vector(q * 0.3 + Vector((i * 3.7, 0, 0))) * 0.45 * math.sin(math.pi * t))  # gnarl
        rad.append(lerp(2.1, 1.65, t) * (1 + 0.4 * math.exp(-((t - knot) / 0.07) ** 2)))  # one knobbly bulge each
    p0 = pts[-1]
    tip = SPLIT + horiz(az) * reach
    tip.z = tip_z
    L = (tip - p0).length
    d0 = (axis(1) - axis(0.9)).normalized()
    bp, br = wobbly(p0, p0 + (d0 * 0.5 + horiz(az)).normalized() * L * 0.35,
                    tip - horiz(az) * L * 0.35 - Vector((0, 0, L * 0.05)), tip, 1.6, 0.6, 2.2, i)
    splines.append((pts + bp, rad + br))
    branches.append((bp, br, az))
    clusters.append((tip + Vector((0, 0, size * 0.3)), size))
    tips.append(tip)

FILL = [((10, 7.5, 38.5), 6.5), ((-6, 6.5, 37.5), 6.5), ((-5, -7.5, 36.5), 6.5), ((10, -6.5, 36.5), 6.5)]  # dome gaps
clusters += [(Vector(c), s) for c, s in FILL]

splines.append(([axis(k / 32) for k in range(33)], [lerp(2.3, 1.4, k / 32) for k in range(33)]))  # solid core
for t, az, out in ((0.36, 200, 2.0), (0.6, 320, 1.6)):  # two burls bulging off the main stem
    a, d = axis(t), horiz(math.radians(az))
    splines.append(([a + d * 2.0, a + d * (3.6 + out * 0.5), a + d * (3.6 + out)], [1.7, 1.5, 1.1]))

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
for k in range(5):  # root flare sinking into the soil
    phi = math.radians(k * 72 + 20 + rng.uniform(-15, 15))
    a = a0 + horiz(phi) * 1.0
    c = Vector((a0.x, a0.y, -1.0)) + horiz(phi) * rng.uniform(5.5, 7.0)
    pts, rad = wobbly(a, a + horiz(phi) * 1.5 - Vector((0, 0, 1.5)), c - horiz(phi) * 2 + Vector((0, 0, 0.6)), c,
                      1.6, 0.35, 0.3, 20 + k)
    splines.append(([a] + pts, [1.6] + rad))

trunk = D.trunk_mesh(splines, '40281f')

# ---------- blossoms: sphere puffs; one voxel-unioned shell per pink so colour seams sit in the creases ----------
PINKS = [D.material(n, h) for n, h in (('Blossom_Deep', 'e8879f'), ('Blossom_Mid', 'f2a3b7'),
                                       ('Blossom_Light', 'f7bccb'), ('Blossom_Pale', 'f9cbd7'))]


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
for lv in range(4):  # higher clusters paler
    bm = bmesh.new()
    for (c, s), l in zip(clusters, level):
        if l == lv:
            puff(bm, c, s)
    assert bm.verts, f'no cluster uses pink {lv}'
    me = bpy.data.meshes.new('shell')
    bm.to_mesh(me)
    bm.free()
    shells.append(D.link(f'BlossomShell{lv}', me))
    D.voxel_union(shells[-1], 0.32, displace=0.3)
    D.florets(shells[-1], 0.5, 0.45, 1.05)
    D.voxel_union(shells[-1], 0.2)
blossoms = D.canopy_mesh(shells, PINKS, 165000)

D.finish('sakura', COLOURS, trunk, shells, blossoms, tips, a0)
