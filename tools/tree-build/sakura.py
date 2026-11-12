"""Build the sakura diorama: public/models/sakura.glb + public/trees/sakura.json.

Run from the repo root: npm run tree:build (Blender 5.2, headless). Deterministic (fixed SEED).
This file is the season: a hanami garden. A wide, twisted cherry in full bloom (blossom shaded ball by ball toward the
sun, two drooping boughs trailing curtains of flowers, paper lanterns strung under the crown), the shared pond, bridge
and stone lantern, and round them a red picnic mat with tea and dango, a big red parasol, stepping stones, a bamboo
fence and drifts of fallen petals on the lawn and the water. The base, scatter, slot cloud, self-checks and export
are shared with the other seasons in diorama.py.
"""
import math, os, sys
sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh, bpy
from mathutils import Vector, Matrix, noise
import diorama as D
from diorama import Z, bez, lerp, horiz, wobbly, rng

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
FWD = (Vector((88.0, -98.0, 0.0)) - D.TREE).normalized()  # from the tree toward the hero camera, on the lawn
RIGHT = Z.cross(FWD)  # screen right
SUN = Vector((40.0, -50.0, 80.0)).normalized()  # the app's key light (three.js (40, 80, 50))

# ---------- trunk and limbs: strands wind up a short leaning trunk, then fork low into wide spreading limbs ----------
SPLIT = Vector((1.0, -0.5, 11.0))
TWIST = math.radians(200)


def axis(t):  # leans out low down, then sweeps back into the fork
    return bez(Vector((0, 0, -1.5)), Vector((-6.0, 2.5, 4.5)), Vector((6.5, -3.0, 8.0)), SPLIT, t)


MAIN = [  # azimuth deg, horizontal reach from the split, tip height, blossom cluster size, knot position on its strand
    (-40, 15.0, 25.0, 5.5, 0.30),  # front, over the picnic
    (25, 18.0, 27.0, 6.0, 0.62),
    (110, 13.0, 31.0, 5.5, 0.45),
    (185, 15.0, 27.0, 6.0, 0.18),
    (255, 16.0, 25.0, 5.5, 0.50),
    (60, 4.0, 34.0, 6.5, 0.78),  # leader
]
SECOND = [  # main limb, position along it, azimuth offset deg, length, rise, cluster size
    (0, 0.50, -50, 7, 3, 4.5), (0, 0.75, 45, 6, 4, 4.0), (1, 0.45, 55, 8, 4, 4.5), (1, 0.70, -50, 7, 3, 4.5),
    (2, 0.50, 50, 7, 4, 4.5), (2, 0.60, -55, 6, 3, 4.0), (3, 0.45, -50, 7, 3, 4.5), (3, 0.70, 50, 6, 4, 4.0),
    (4, 0.50, 55, 7, 3, 4.5), (4, 0.70, -45, 6, 4, 4.0), (5, 0.50, 40, 6, 5, 4.5),
]
BOUGHS = [(1, 0.50, 20, 13.0, 6.5), (4, 0.50, -30, 12.0, 6.0)]  # drooping, framing the trunk: limb, position, az offset, reach, drop
splines, clusters, branches, tips, boughs = [], [], [], [], []

for i, (az_deg, reach, tip_z, size, knot) in enumerate(MAIN):
    az = math.radians(az_deg)
    pts, rad = [], []
    for k in range(33):
        t = k / 32
        q = axis(t) + horiz(az - TWIST + TWIST * t) * lerp(2.6, 1.2, t)
        pts.append(q + noise.noise_vector(q * 0.3 + Vector((i * 3.7, 0, 0))) * 0.45 * math.sin(math.pi * t))  # gnarl
        rad.append(lerp(2.0, 1.5, t) * (1 + 0.4 * math.exp(-((t - knot) / 0.07) ** 2)))  # one knobbly bulge each
    p0 = pts[-1]
    tip = SPLIT + horiz(az) * reach
    tip.z = tip_z
    L = (tip - p0).length
    d0 = (axis(1) - axis(0.9)).normalized()
    bp, br = wobbly(p0, p0 + (d0 * 0.3 + horiz(az)).normalized() * L * 0.4,  # out first, then up: a spreading crown
                    tip - horiz(az) * L * 0.3 - Z * L * 0.08, tip, 1.5, 0.5, 2.0, i)
    splines.append((pts + bp, rad + br))
    branches.append((bp, br, az))
    clusters.append((tip, size))
    tips.append(tip)
    for at, s in ((0.55, 3.6), (0.8, 4.0)):  # blossom along the limb, not only at its end
        clusters.append((bp[int(at * (len(bp) - 1))] + Z * 0.8, s))

for j, (mi, at, off, length, rise, size) in enumerate(SECOND):
    bp, br, az = branches[mi]
    k = int(at * (len(bp) - 1))
    p0, r0 = bp[k], br[k] * 0.75
    a = az + math.radians(off)
    tip = p0 + horiz(a) * length + Z * rise
    pts, rad = wobbly(p0, p0 + horiz(a) * length * 0.4, tip - Z * rise * 0.5, tip, r0, 0.3, 0.8, 10 + j)
    splines.append(([p0] + pts, [r0] + rad))
    clusters.append((tip, size))
    clusters.append((pts[len(pts) // 2] + Z * 0.6, size * 0.65))
    tips.append(tip)

for j, (mi, at, off, reach, drop) in enumerate(BOUGHS):  # arch out and up, then sag well below the crown
    bp, br, az = branches[mi]
    k = int(at * (len(bp) - 1))
    p0, r0 = bp[k], br[k] * 0.7
    d = horiz(az + math.radians(off))
    tip = p0 + d * reach - Z * drop
    pts, rad = wobbly(p0, p0 + d * reach * 0.45 + Z * 3.0, p0 + d * reach * 0.85 + Z * 0.5, tip, r0, 0.3, 0.6, 30 + j)
    splines.append(([p0] + pts, [r0] + rad))
    clusters.append((tip, 3.8))
    for at, sz in ((0.45, 3.4), (0.7, 3.2)):  # pads of bloom cascading down the arc
        clusters.append((pts[int(at * (len(pts) - 1))] + Z * 0.4, sz))
    tips.append(tip)
    boughs.append(pts)

clusters += [(Vector(c), s) for c, s in (((4, 6, 33), 5.0), ((-5, 3, 32), 5.0), ((0, -6, 31), 4.5),
                                          ((7, -3, 31), 4.5),  # crown top
                                          ((1, 0, 27.5), 5.5), ((-2, -3, 25.5), 4.5))]  # heart: no sky through the ring

splines.append(([axis(k / 32) for k in range(33)], [lerp(2.3, 1.4, k / 32) for k in range(33)]))  # solid core
for t, az, out in ((0.36, 200, 2.0), (0.6, 320, 1.6)):  # two burls bulging off the main stem
    a, d = axis(t), horiz(math.radians(az))
    splines.append(([a + d * 2.0, a + d * (3.6 + out * 0.5), a + d * (3.6 + out)], [1.7, 1.5, 1.1]))

a0 = axis(0.2)
for k in range(5):  # root flare sinking into the soil
    phi = math.radians(k * 72 + 20 + rng.uniform(-15, 15))
    a = a0 + horiz(phi) * 1.0
    c = Vector((a0.x, a0.y, -1.0)) + horiz(phi) * rng.uniform(5.5, 7.0)
    pts, rad = wobbly(a, a + horiz(phi) * 1.5 - Z * 1.5, c - horiz(phi) * 2 + Z * 0.6, c, 1.6, 0.35, 0.3, 20 + k)
    splines.append(([a] + pts, [1.6] + rad))

# ---------- blossom: lobes and florets; each ball shaded toward the sun (crown-wide and within its cluster) ----------
balls = []  # centre, radius, light score


def add(p, r, c, s):
    balls.append((p, r, None, c, s))


def puff(c, s):
    add(c, s * 0.62, c, s)
    for _ in range(8):
        lc = c + D.rand_dir(0.1) * Vector((s * 0.6, s * 0.6, s * 0.32))
        lr = s * rng.uniform(0.36, 0.5)
        add(lc, lr, c, s)
        for _ in range(4):  # small florets half-buried in each lobe
            add(lc + D.rand_dir(0.3) * lr * 0.85, s * rng.uniform(0.16, 0.24), c, s)


for c, s in clusters:
    puff(c, s)
for pts in boughs:  # weeping: separate strings of small blossoms hanging off the bough's outer half
    for k in range(len(pts) // 2, len(pts) - 1, 4):
        n = rng.randint(2, 4)
        top = pts[k] + horiz(rng.uniform(0, 2 * math.pi)) * 0.7
        for m in range(n):
            add(top - Z * (1.0 + 1.05 * m), lerp(0.62, 0.42, m / n), pts[k], 2.5)

CC = sum((c for c, _ in clusters), Vector()) / len(clusters)
RC = max((c - CC).length + s for c, s in clusters)
score = [0.5 * (p - CC).dot(SUN) / RC + 0.6 * (p - c).dot(SUN) / s + 0.12 * noise.noise(p * 0.2)
         for p, r, _, c, s in balls]
rank = sorted(range(len(balls)), key=score.__getitem__)
CUTS = (0.16, 0.36, 0.58, 0.8)  # five shades, deep (away from the sun, undersides) to pale (sunlit tops)
PINKS = [D.material(n, h) for n, h in (('Blossom_Deep', 'e2728f'), ('Blossom_Rose', 'ec8ea7'),
                                       ('Blossom_Mid', 'f2a7ba'), ('Blossom_Light', 'f6bacb'),
                                       ('Blossom_Pale', 'f9ccd8'))]
bms = [bmesh.new() for _ in PINKS]
for r_, i in enumerate(rank):
    p, r, *_ = balls[i]
    lv = sum(r_ >= q * len(rank) for q in CUTS)
    bmesh.ops.create_icosphere(bms[lv], subdivisions=3 if r > 2 else 2, radius=r, matrix=Matrix.Translation(p))
shells = []
for lv, bm in enumerate(bms):
    me = bpy.data.meshes.new('shell')
    bm.to_mesh(me)
    bm.free()
    shells.append(D.link(f'BlossomShell{lv}', me))
    D.voxel_union(shells[-1], 0.3, displace=0.25)
    D.florets(shells[-1], 0.4, 0.35, 0.85)
    D.voxel_union(shells[-1], 0.2)

# ---------- the trunk mesh, with red and white paper lanterns strung between the two front limbs ----------
trunk = D.trunk_mesh(splines, '54372b')
bm = bmesh.new()
bm.from_mesh(trunk.data)
A, B = branches[0][0][14], branches[4][0][14]  # rope ends, part way out along the front limbs
rope = [A.lerp(B, u) - Z * 3.5 * 4 * u * (1 - u) for u in [k / 30 for k in range(31)]]
D.tube(bm, 3, rope, 0.1, side=(B - A).cross(Z).normalized(), sides=6)
for k in range(1, 6):
    top = rope[k * 5]
    c = top - Z * 1.6
    if all((c - p).length > r + 1.4 for p, r, *_ in balls):  # clear of the blossom
        D.rod(bm, 3, top + Z * 0.05, c, 0.05, 0.05, seg=4)
        D.blob(bm, 1 + k % 2, c - Z * 0.3, 0.95, (1, 1, 1.2), sub=3)
        for z in (0.92, -1.52):  # dark top and bottom rims
            D.rod(bm, 3, c + Z * (z - 0.15), c + Z * (z + 0.15), 0.55, 0.55, seg=10)
me = trunk.data
for v in list(bm.verts)[len(me.vertices):]:  # the lanterns were built tree-local; the trunk is already at D.TREE
    v.co += D.TREE
bm.to_mesh(me)
bm.free()
for n, h in (('LanternRed', 'd7353d'), ('LanternWhite', 'f7efe0'), ('LanternRim', '2b2326')):
    me.materials.append(D.material(n, h, 0.6))
blossoms = D.canopy_mesh(shells, PINKS, 96000)


# ---------- hanami: picnic mat, parasol, stepping stones, bamboo fence, fallen petals ----------
FOOTW = D.TREE + Vector((a0.x, a0.y, 0))
MAT_C, MAT_L, MAT_W = FOOTW + FWD * 14.0 - RIGHT * 7.0, 11.0, 7.0  # centre, length (screen right), width
PARASOL = MAT_C - RIGHT * 6.6 - FWD * 1.2
FENCE = [Vector((2.0, 32.5, 0)), Vector((32.5, 32.5, 0)), Vector((32.5, 4.0, 0))]
PATHS = [(Vector((-20.0, -31.0, 0)), MAT_C - RIGHT * 5.0 + FWD * 4.8),
         (MAT_C + RIGHT * 6.4 + FWD * 2.2, D.B0 - D.BDIR * 1.6)]


def stones():  # stepping stones along each path, a stride apart, zigzagging a little
    out = []
    for a, b in PATHS:
        n = max(2, int((b - a).length / 2.4))
        side = Z.cross(b - a).normalized()
        for k in range(n + 1):
            out.append(a.lerp(b, k / n) + side * (0.45 if k % 2 else -0.45))
    return [p for p in out if D.pond_gap(p) > 1.8 and D.bridge_dist(p) > 3.0]


def seg_dist(p, a, b):
    t = max(0.0, min(1.0, (p - a).dot(b - a) / (b - a).length_squared))
    return D.flat(p - a.lerp(b, t)).length


def on_mat(p, pad):
    d = p - MAT_C
    return abs(d.dot(RIGHT)) < MAT_L / 2 + pad and abs(d.dot(FWD)) < MAT_W / 2 + pad


STONES = stones()


def keep_clear(p, pad):  # the lawn scatter stays off the mat, parasol, stones and fence
    return (on_mat(p, pad + 0.8) or D.flat(p - PARASOL).length < 1.2 + pad
            or any(D.flat(p - s).length < 1.6 + pad for s in STONES)
            or any(seg_dist(p, a, b) < 1.0 + pad for a, b in zip(FENCE, FENCE[1:])))


PROPS = {n: D.material(n, h, r) for n, h, r in (
    ('Felt', 'c8343c', 0.95), ('Cushion', '3f5194', 0.9), ('Lacquer', '2a2226', 0.3), ('Gold', 'd8a443', 0.4),
    ('Celadon', 'a9c6a6', 0.4), ('Cup', 'f4ecdc', 0.5), ('DangoPink', 'f3a0b6', 0.7), ('DangoWhite', 'f8f4ea', 0.7),
    ('DangoGreen', 'a6c97c', 0.7), ('Skewer', 'dcbf90', 0.8), ('Parasol', 'd83a35', 0.7),
    ('ParasolRib', 'a8262a', 0.7), ('Bamboo', 'c9b47a', 0.6), ('BambooDark', 'a38f55', 0.6),
    ('StepStone', 'c9bdb4', 0.85), ('Petal', 'f8cdd8', 0.7), ('PetalDeep', 'f3b2c4', 0.7))}


def put(name, parts, names, sharp=None):  # parts: a bmesh; every vertex kept on or above the lawn's top
    for v in parts.verts:
        v.co.z = max(v.co.z, -0.08)
    return D.prop(name, parts, *[PROPS[n] for n in names], sharp=sharp)


def box(bm, mi, c, x, y, z, bev):  # a bevelled box: centre c, full-size axis vectors x, y, z
    tb = bmesh.new()
    bmesh.ops.create_cube(tb, size=1.0, matrix=D.frame(c, x, y, z))
    bmesh.ops.bevel(tb, geom=list(tb.edges), offset=bev, segments=2, profile=0.5, affect='EDGES')
    for f in tb.faces:
        f.material_index = mi
    me = bpy.data.meshes.new('box')
    tb.to_mesh(me)
    tb.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def picnic():  # red felt mat; cushions, a stacked lacquer box, tea on a tray, dango on a plate
    bm = bmesh.new()
    R, F = RIGHT, FWD
    box(bm, 0, MAT_C + Z * 0.04, R * MAT_L, F * MAT_W, Z * 0.16, 0.06)
    for s in (-1, 1):
        box(bm, 1, MAT_C - F * 1.5 + R * 2.6 * s + Z * 0.38, R * 2.5, F * 2.5, Z * 0.52, 0.22)
    j = MAT_C + F * 0.5 - R * 0.2
    for k in range(3):  # jubako: three black tiers with gold seams and a lid
        box(bm, 2, j + Z * (0.42 + 0.58 * k), R * 1.8, F * 1.8, Z * 0.52, 0.05)
        box(bm, 3, j + Z * (0.71 + 0.58 * k), R * 1.84, F * 1.84, Z * 0.07, 0.02)
    box(bm, 2, j + Z * 1.98, R * 1.9, F * 1.9, Z * 0.2, 0.06)
    t = MAT_C + R * 3.4 + F * 1.0
    D.rod(bm, 2, t + Z * 0.1, t + Z * 0.22, 1.25, 1.25, seg=20)  # tray
    D.blob(bm, 4, t + Z * 0.75 - R * 0.3, 0.6, (1, 1, 0.82), sub=3)  # kyusu teapot, spout, side handle, knob
    D.rod(bm, 4, t + Z * 0.7 - R * 0.3 - F * 0.45, t + Z * 1.1 - R * 0.3 - F * 0.95, 0.13, 0.07, seg=6)
    D.rod(bm, 4, t + Z * 0.75 - R * 0.85, t + Z * 0.85 - R * 1.6, 0.1, 0.1, seg=6)
    D.blob(bm, 4, t + Z * 1.27 - R * 0.3, 0.15, sub=2)
    for s in (0, 1):
        D.rod(bm, 5, t + Z * 0.2 + R * (0.55 + 0.1 * s) + F * (0.6 * s - 0.2), t + Z * 0.62 + R * (0.55 + 0.1 * s)
              + F * (0.6 * s - 0.2), 0.27, 0.3, seg=10)
    d = MAT_C - R * 3.4 + F * 1.2
    bm_plate = d + Z * 0.16
    D.blob(bm, 7, bm_plate, 1.0, (1.4, 1.0, 0.06), sub=3)
    for k in (-1, 0, 1):  # hanami dango: pink, white and green on a skewer
        c = d + F * 0.5 * k + Z * 0.5
        D.rod(bm, 9, c - R * 1.2, c + R * 1.1, 0.05, 0.05, seg=4)
        for m, mi in enumerate((6, 7, 8)):
            D.blob(bm, mi, c + R * (0.75 - 0.68 * m), 0.33, sub=2)
    return put('Picnic', bm, ['Felt', 'Cushion', 'Lacquer', 'Gold', 'Celadon', 'Cup', 'DangoPink', 'DangoWhite',
                              'DangoGreen', 'Skewer'], sharp=50)


def parasol():  # nodate-gasa: a big red paper parasol on a bamboo pole, leaning over the mat
    bm = bmesh.new()
    up = (Z + RIGHT * 0.22 + FWD * 0.05).normalized()
    apex = PARASOL + up * 6.6
    D.rod(bm, 2, PARASOL - Z * 0.1, apex + up * 0.3, 0.13, 0.13, seg=8)
    D.rod(bm, 0, apex - up * 1.35, apex, 4.4, 0.3, seg=32)
    x = up.orthogonal().normalized()
    for k in range(16):  # ribs on the canopy
        d = (Matrix.Rotation(2 * math.pi * k / 16, 3, up) @ x)
        D.rod(bm, 1, apex + up * 0.05, apex - up * 1.32 + d * 4.42, 0.06, 0.06, seg=4)
    D.blob(bm, 1, apex + up * 0.25, 0.3, sub=2)
    return put('Parasol', bm, ['Parasol', 'ParasolRib', 'Bamboo'])


def fence():  # low yotsume-gaki: bamboo posts, two rails and close-set verticals
    bm = bmesh.new()
    for a, b in zip(FENCE, FENCE[1:]):
        L = (b - a).length
        for k in range(int(L / 2.4) + 1):
            p = a.lerp(b, k * 2.4 / L)
            D.rod(bm, 0, p - Z * 0.1, p + Z * 2.7, 0.22, 0.22, seg=8)
        for z in (1.0, 2.1):
            D.rod(bm, 1, a + Z * z, b + Z * z, 0.13, 0.13, seg=6)
        for k in range(int(L / 0.8)):
            p = a.lerp(b, (k + 0.5) * 0.8 / L)
            D.rod(bm, 0, p - Z * 0.1, p + Z * 2.35, 0.09, 0.09, seg=5)
    return put('Fence', bm, ['Bamboo', 'BambooDark'])


def steps():
    bm = bmesh.new()
    for p in STONES:
        D.blob(bm, 0, p + Z * 0.04, rng.uniform(1.0, 1.35), (1.25, 1.0, 0.15), sub=2, rough=0.12,
               yaw=rng.uniform(0, 6.3))
    return put('SteppingStones', bm, ['StepStone'])


def petals():  # drifts under the crown, petals strewn over the lawn and the mat, rafts of petals on the pond
    bm = bmesh.new()

    def flake(p, r, z, thick, mi, sub=2):
        a = rng.uniform(0, 2 * math.pi)
        D.prim(bm, 'icosphere', mi, D.frame(p + Z * z, horiz(a) * r * 1.3, horiz(a + math.pi / 2) * r, Z * thick),
               subdivisions=sub, radius=1.0)

    def lawn(p, pad):
        return (max(abs(p.x), abs(p.y)) < 33.5 and D.pond_gap(p) > 1.4 + pad and D.bridge_dist(p) > 3.0 + pad
                and D.flat(p - D.LANTERN).length > 3.0 + pad and not keep_clear(p, pad))

    n = 0
    while n < 44:  # drifts: each a ragged sheet of small flat patches, thickest just beyond the trunk
        c = FOOTW + horiz(rng.uniform(0, 2 * math.pi)) * (9.5 + abs(rng.gauss(0, 4.5)))
        if not lawn(c, 1.5):
            continue
        n += 1
        for _ in range(9):
            p = c + horiz(rng.uniform(0, 2 * math.pi)) * 1.8 * math.sqrt(rng.random())
            if lawn(p, 0.6) and D.flat(p - FOOTW).length > 8.6:
                flake(p, rng.uniform(0.55, 1.0), 0.03, 0.07, 0, sub=1)
    n = 0
    while n < 120:  # strewn single petals
        p = FOOTW + horiz(rng.uniform(0, 2 * math.pi)) * rng.uniform(8.5, 34)
        if lawn(p, 0.2) and D.flat(p - FOOTW).length > 8.0:
            flake(p, rng.uniform(0.35, 0.5), 0.03, 0.05, 1, sub=1)
            n += 1
    for k in range(14):  # a few on the mat
        p = MAT_C + RIGHT * rng.uniform(-5, 5) + FWD * rng.uniform(-3, 3)
        flake(p, rng.uniform(0.35, 0.45), 0.15, 0.04, k % 2, sub=1)
    n = 0
    while n < 90:  # hanaikada: petals drifting in a band across the pond
        u = rng.uniform(-1, 1)
        p = D.POND + D.horiz(D.POND_A) * u * 8.5 + D.horiz(D.POND_A + math.pi / 2) * (2.2 * math.sin(2.5 * u)
                                                                                        + rng.gauss(0, 0.9))
        if D.pond_gap(p) < -0.9 and D.bridge_dist(p) > 2.8:
            big = n < 8
            flake(p, rng.uniform(0.7, 1.2) if big else rng.uniform(0.3, 0.45), 0.09, 0.03, n % 2, sub=2 if big else 1)
            n += 1
    return put('Petals', bm, ['Petal', 'PetalDeep'])


def hanami():
    picnic()
    parasol()
    fence()
    steps()
    petals()


D.finish('sakura', COLOURS, trunk, shells, blossoms, tips, a0, extras=hanami, keep_clear=keep_clear)
