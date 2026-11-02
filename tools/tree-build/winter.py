"""Build the winter diorama: public/models/winter.glb + public/trees/winter.json.

Run from the repo root: npm run tree:build (Blender 5.2, headless). Deterministic (fixed SEED).
This file is the season: a bare, gnarled zelkova whose branch ends carry heavy mounded snow, on a snowy lawn with a
frozen pond, a vermilion bridge and a snow-capped lantern. The base, props, slot cloud, self-checks and export are
shared with the other seasons in diorama.py.
"""
import math, os, sys
sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh, bpy
from mathutils import Vector, Matrix, noise
import diorama as D
from diorama import Z, bez, lerp, horiz, wobbly, rng

SEED = 20261221
D.init(SEED)
COLOURS = {  # scenery material -> hex sRGB; Moss is the snow on the base top
    'Moss': 'eef2f7', 'Stone': '8a8f99', 'PondBed': '587a8c', 'StoneChunk': '6c717b',
    'PondBank': 'dde4ed', 'RimStone': '7f848c', 'RimStoneLight': 'a3a8b0', 'Water': 'cfe5ef',
    'FlowerCentre': 'f2c84b', 'LilyPad': 'e1ecf2', 'Wood': 'a8432f', 'WoodDark': '742c20',
    'LanternGlow': 'ffd68a', 'LanternStone': 'a3a7ae', 'RockGrey': '6f747c', 'RockPink': '8a8f97',
    'GrassDark': 'a49c7e', 'GrassLight': 'c8bf9c', 'MossDark': 'f3f6fa', 'MossLight': 'f8fafd',
    'FlowerWhite': 'f6f3e8', 'FlowerLavender': 'c23a45', 'Stem': '50683a',
}  # LilyPad: snow patches on the ice; FlowerWhite / FlowerLavender: narcissus and camellia
# canopy, deep to pale; the brightest is tinted: a near-pure white has full HSL saturation, so derives to a vivid blue
SNOW = [('Snow_Shadow', 'c3d0e2'), ('Snow', 'e4ebf4'), ('Snow_Bright', 'f6f9fc')]

# ---------- trunk and limbs: strands wind up a short stout trunk, then splay into a vase of rising limbs ----------
SPLIT = Vector((1.5, -1.0, 12.0))
TWIST = math.radians(160)


def axis(t):
    return bez(Vector((0, 0, -1.5)), Vector((-4.0, 2.0, 5.0)), Vector((5.0, -2.5, 8.5)), SPLIT, t)


MAIN = [  # azimuth deg, horizontal reach from the split, tip height, snow clump radius
    (15, 22.0, 24.0, 4.4),  # the long low limb reaching out over the lawn
    (95, 13.0, 33.0, 3.6),
    (165, 17.0, 29.0, 4.0),
    (235, 14.0, 34.0, 3.4),
    (305, 12.0, 31.0, 3.8),
    (50, 7.0, 38.0, 4.2),  # leader
]
SUB = [  # limb, position along it, azimuth offset deg, length, rise, clump radius
    (0, 0.45, -50, 8, 3.5, 3.4),
    (0, 0.70, 45, 6, 4.0, 2.9),
    (1, 0.55, 55, 7, 5.0, 3.2),
    (2, 0.40, 50, 8, 4.0, 3.3),
    (2, 0.65, -45, 7, 5.0, 2.9),
    (3, 0.50, -55, 7, 5.0, 3.1),
    (4, 0.55, 50, 7, 4.0, 2.9),
    (5, 0.60, -60, 6, 3.0, 3.4),
    (1, 0.35, -50, 7, 4.0, 2.9),
    (3, 0.70, 50, 6, 4.0, 3.0),
    (4, 0.35, -60, 8, 3.0, 3.2),
    (5, 0.40, 120, 6, 3.5, 2.9),
]
splines, branches, clumps, tips = [], [], [], []  # branches: the limb and side-branch splines that hold snow

for i, (az_deg, reach, tip_z, R) in enumerate(MAIN):
    az = math.radians(az_deg)
    pts, rad = [], []
    for k in range(33):
        t = k / 32
        q = axis(t) + horiz(az - TWIST + TWIST * t) * lerp(2.4, 1.0, t)
        pts.append(q + noise.noise_vector(q * 0.3 + Vector((i * 3.7, 0, 0))) * 0.4 * math.sin(math.pi * t))
        rad.append(lerp(1.8, 1.25, t))
    p0 = pts[-1]
    tip = SPLIT + horiz(az) * reach
    tip.z = tip_z
    L = (tip - p0).length
    d0 = (axis(1) - axis(0.9)).normalized()
    bp, br = wobbly(p0, p0 + (d0 * 0.6 + horiz(az)).normalized() * L * 0.35,
                    tip - (horiz(az) * 0.7 + Z * 0.7).normalized() * L * 0.3, tip, 1.25, 0.35, 2.0, i)
    splines.append((pts + bp, rad + br))
    branches.append((bp, br, az))
    clumps.append((tip, R, bp))
    tips.append(tip)

for j, (mi, at, off, length, rise, R) in enumerate(SUB):
    bp, br, az = branches[mi]
    k = int(at * (len(bp) - 1))
    p0, r0 = bp[k], br[k] * 0.75
    a = az + math.radians(off)
    tip = p0 + horiz(a) * length + Z * rise
    pts, rad = wobbly(p0, p0 + horiz(a) * length * 0.4, tip - Z * rise * 0.5, tip, r0, 0.3, 0.8, 10 + j)
    splines.append(([p0] + pts, [r0] + rad))
    branches.append((pts, rad, a))
    clumps.append((tip, R, pts))
    tips.append(tip)


def heading(bp):  # horizontal direction of a branch's end
    d = bp[-1] - bp[-6]
    d.z = 0
    return d.normalized()


for j, (tip, R, bp) in enumerate(clumps):  # a fan of fine twigs splaying off the branch end and up into its clump
    d = heading(bp)
    for k in range(3):
        p0 = bp[-8 - 2 * k]
        end = tip + (d * rng.uniform(-0.2, 0.25) + d.cross(Z) * rng.uniform(-0.25, 0.25)
                     + Z * rng.uniform(-0.05, 0.05)) * R
        bulge = d.cross(Z) * (0.8 if k % 2 else -0.8) + Z * 0.5
        pts, rad = wobbly(p0, p0 + (end - p0) * 0.35 + bulge, end - Z * 1.0, end, 0.38, 0.25, 0.3, 40 + 3 * j + k)
        splines.append(([p0] + pts, [0.38] + rad))
        tips.append(end)

splines.append(([axis(k / 32) for k in range(33)], [lerp(2.2, 1.3, k / 32) for k in range(33)]))  # solid core
a0 = axis(0.2)
for k in range(6):  # nebari: a root flare sinking into the snow
    phi = math.radians(k * 60 + 15 + rng.uniform(-12, 12))
    a = a0 + horiz(phi) * 1.0
    c = Vector((a0.x, a0.y, -1.0)) + horiz(phi) * rng.uniform(5.0, 6.8)
    pts, rad = wobbly(a, a + horiz(phi) * 1.5 - Z * 1.2, c - horiz(phi) * 2 + Z * 0.5, c, 1.5, 0.35, 0.3, 20 + k)
    splines.append(([a] + pts, [1.5] + rad))

trunk = D.trunk_mesh(splines, '3a2f2b')

# ---------- snow: mounded clumps on every branch end and a blanket along the flatter branch tops ----------
# Shells: 0 the clumps' shadowed undersides, 1 the blanket on the branches, 2 the clumps' white tops.
bms = [bmesh.new() for _ in SNOW]


def ellipsoid(bm, c, r, sz):
    bmesh.ops.create_icosphere(bm, subdivisions=3 if r > 1.5 else 2, radius=r,
                               matrix=Matrix.LocRotScale(c, None, (1, 1, sz)))


for tip, R, bp in clumps:  # lobes strung along the branch end, a domed top: shadowed body, white cap lifted over it
    d = heading(bp)
    c = tip + Z * R * 0.05
    lobes = [(c, R * 0.85)]
    for _ in range(6):
        lobes.append((c + (d * rng.uniform(-0.7, 0.35) + d.cross(Z) * rng.uniform(-0.4, 0.4)) * R
                      + Z * R * rng.uniform(-0.1, 0.15), R * rng.uniform(0.45, 0.6)))
    lobes.append((c + d * R * rng.uniform(-0.2, 0.1) + Z * R * 0.25, R * 0.5))
    for p, r in lobes:
        ellipsoid(bms[0], p, r, 0.7)
        ellipsoid(bms[2], p + Z * r * rng.uniform(0.06, 0.16), r * rng.uniform(0.97, 1.02), 0.7)  # wandering edge

for pts, rad, _ in branches:  # snow along the branch tops, thickest on the flattest stretches
    for k in range(len(pts)):
        slope = abs((pts[min(k + 4, len(pts) - 1)] - pts[max(k - 4, 0)]).normalized().z)  # over ~4 units: no dashes
        flat = max(0.0, min(1.0, (0.9 - slope) / 0.5))
        if flat > 0.05:
            ellipsoid(bms[1], pts[k] + Z * rad[k] * 0.7, (rad[k] + 0.35) * flat, 0.65)

shells = []
for i, bm in enumerate(bms):
    me = bpy.data.meshes.new('shell')
    bm.to_mesh(me)
    bm.free()
    shells.append(D.link(f'SnowShell{i}', me))
    D.voxel_union(shells[-1], 0.22)
    for v in shells[-1].data.vertices:  # lumpy, each layer its own noise so the shadow / white boundary wanders
        v.co += v.normal * 0.15 * noise.noise(v.co * 0.5 + Vector((7.3 * i, 0, 0)))
blossoms = D.canopy_mesh(shells, [D.material(n, h) for n, h in SNOW], 140000)


# ---------- ground extras: snow on the bridge, a snow hat on the lantern (yukimi-doro), caps on the boulders ----------
def deck_pt(s):  # the bridge's deck line, as in diorama.finish
    return D.B0 + D.BDIR * s + Z * (0.25 + D.H_BR * math.sin(math.pi * s / D.L_BR))


def snow():
    bm = bmesh.new()
    for k in range(31):  # a flattened ellipsoid per stretch of deck, between the rails
        s = D.L_BR * k / 30
        t = (deck_pt(s + 0.01) - deck_pt(s - 0.01)).normalized()
        D.prim(bm, 'icosphere', 0, D.frame(deck_pt(s), t * 0.8, D.BSIDE * 1.5, t.cross(D.BSIDE) * 0.22),
               subdivisions=2, radius=1.0)
    for side in (-1, 1):  # a roll along each top rail
        D.tube(bm, 0, [deck_pt(D.L_BR * k / 40) + D.BSIDE * side * (D.W_BR / 2 - 0.15) + Z * 2.13 for k in range(41)],
               0.19, side=D.BSIDE, sides=8)
    D.blob(bm, 0, D.LANTERN + Z * 7.95, 3.0, (1, 1, 0.33), sub=3, rough=0.05)
    bm.from_mesh(bpy.data.objects['Rocks'].data)  # a copy of each boulder: tops pushed out, sides and bottom tucked in
    bm.normal_update()
    first = len(bm.verts) - len(bpy.data.objects['Rocks'].data.vertices)
    for v in list(bm.verts)[first:]:
        v.co += v.normal * (0.45 * max(0.0, v.normal.z) ** 1.5 - 0.12)
    for f in bm.faces:
        f.material_index = 0
    D.prop('Snow', bm, D.material('SnowCap', 'f4f7fb'))


D.finish('winter', COLOURS, trunk, shells, blossoms, tips, a0, pebbles=0, mounds=18, tufts=30, clumps=3, lotus=0,
         extras=snow)
