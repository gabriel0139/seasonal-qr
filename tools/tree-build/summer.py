"""Build the summer diorama: public/models/summer.glb + public/trees/summer.json.

Run from the repo root: Blender -b -P tools/tree-build/summer.py (Blender 5.2, headless). Deterministic (fixed SEED).
This file is the season: a lazy summer afternoon by the water. A grand shade tree stands on buttress roots and spreads
wide limbs under a broad crown of many overlapping leaf masses, toned from shade to sun. A rope swing hangs from its
long low limb and a kite is caught in the leaves (ropes and kite are merged into the Trunk; the seat is a prop). The
pond is a swimming hole with a jetty, a rowing boat, reeds and cattails; a picnic blanket with a watermelon and a
basket lies at the edge of the shade. The base, shared lawn scatter, slot cloud, self-checks and export are in
diorama.py.
"""
import math, os, sys
sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh, bpy
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree
import diorama as D
from diorama import Z, bez, lerp, horiz, wobbly, rng

SEED = 20260721
D.init(SEED)
D.POND, D.POND_RX, D.POND_RY = Vector((12.5, -9.0, 0.0)), 13.0, 9.0  # a bigger swimming hole (no bridge to fit)
COLOURS = {  # scenery material -> hex sRGB
    'Moss': '8fc83c', 'Stone': 'c9b8a0', 'PondBed': '3f7a6a', 'StoneChunk': '948572',
    'PondBank': '5f9a34', 'RimStone': 'bcae9a', 'RimStoneLight': 'd6cab8', 'Water': '7fd0ee',
    'FlowerCentre': 'f2c84b', 'LilyPad': '3f8f3a', 'Lotus': 'f6b7cf', 'Wood': '9c6b47', 'WoodDark': '6e4932',
    'LanternGlow': 'ffe2a0', 'LanternStone': 'bdb2a2', 'RockGrey': 'a39d93', 'RockPink': 'b0a496',
    'GrassDark': '4f9a2c', 'GrassLight': '9fd04a', 'MossDark': '7fba34', 'MossLight': 'a2d24a',
    'FlowerWhite': 'fbfaf4', 'FlowerLavender': '7d8fe8', 'Stem': '4f8f2e',
}
CAM = Vector((88.0, -98.0, 66.0))  # the hero view
SUN = Vector((0.5, -0.33, 0.8)).normalized()  # the preview's key light: the crown is toned toward it
GOLDEN = math.pi * (3 - math.sqrt(5))

# ---------- trunk: a stout bole on buttress roots, forking low into wide limbs that run out under the crown ----------
SPLIT = Vector((0.4, -0.3, 11.5))


def axis(t):
    return bez(Vector((0, 0, -1.5)), Vector((-0.8, 0.5, 4.0)), Vector((1.0, -0.6, 8.0)), SPLIT, t)


SWING = 0  # the long low limb the swing hangs from, side on to the camera
LIMBS = [  # azimuth deg, tip reach, tip height; tips sit inside the crown's lower masses
    (13, 18.0, 23.5), (78, 15.0, 27.0), (140, 16.5, 25.5), (200, 15.0, 27.5), (262, 16.5, 25.0), (318, 14.5, 26.5),
    (40, 4.0, 33.0),  # leader
]
SECOND = [(1, 0.55, 50, 8, 4), (2, 0.55, -45, 8, 3), (3, 0.6, 45, 7, 4), (4, 0.55, -50, 8, 3), (5, 0.55, 45, 7, 4),
          (2, 0.75, 50, 6, 4), (4, 0.75, 45, 6, 4)]  # limb, position along it, azimuth offset deg, length, rise
splines, limbs, tips = [], [], []

for i, (az_deg, reach, tip_z) in enumerate(LIMBS):
    az = math.radians(az_deg)
    pts = [axis(k / 32) + horiz(az - 1.0 + 0.6 * k / 32) * lerp(2.1, 1.1, k / 32) for k in range(33)]
    rad = [lerp(2.6, 1.9, k / 32) for k in range(33)]
    p0 = pts[-1]
    tip = horiz(az) * reach + Z * tip_z
    if i == SWING:  # out nearly level at swing height, then up into the crown
        bp, br = wobbly(p0, p0 + horiz(az) * 6 + Z * 1.5, horiz(az) * 13 + Z * 15.5, tip, 1.8, 0.7, 0.5, i)
    else:
        L = (tip - p0).length
        d0 = (axis(1) - axis(0.9)).normalized()
        bp, br = wobbly(p0, p0 + (d0 * 0.6 + horiz(az)).normalized() * L * 0.4,
                        tip - horiz(az) * L * 0.3 - Z * L * 0.1, tip, 1.8, 0.6, 1.4, i)
    splines.append((pts + bp, rad + br))
    limbs.append((bp, br, az))
    tips.append(tip)

splines.append(([axis(k / 32) for k in range(33)], [lerp(2.7, 2.1, k / 32) for k in range(33)]))  # solid core
for j, (mi, at, off, length, rise) in enumerate(SECOND):
    bp, br, az = limbs[mi]
    k = int(at * (len(bp) - 1))
    p0, r0 = bp[k], br[k] * 0.75
    a = az + math.radians(off)
    tip = p0 + horiz(a) * length + Z * rise
    pts, rad = wobbly(p0, p0 + horiz(a) * length * 0.4, tip - Z * rise * 0.5, tip, r0, 0.3, 0.8, 10 + j)
    splines.append(([p0] + pts, [r0] + rad))
    tips.append(tip)

a0 = axis(0.2)
for k in range(7):  # buttress roots: tall fins at the bole that sink into the lawn
    phi = math.radians(k * 360 / 7 + 10 + rng.uniform(-10, 10))
    a = a0 + horiz(phi) * 1.2 + Z * 1.5
    c = Vector((a0.x, a0.y, -0.8)) + horiz(phi) * rng.uniform(6.0, 7.5)
    pts, rad = wobbly(a, a + horiz(phi) * 1.5 - Z * 1.0, c - horiz(phi) * 2.5 + Z * 0.7, c, 2.1, 0.35, 0.3, 20 + k)
    splines.append(([a] + pts, [2.1] + rad))

trunk = D.trunk_mesh(splines, '5a3f2c')

# ---------- crown: overlapping leaf masses with flat-ish undersides in one body; leaf lumps toned by the sun ----------
LEAVES = [('Leaf_Shade', '24572d'), ('Leaf_Deep', '357a37'), ('Leaf_Mid', '4f9a3a'), ('Leaf_Light', '79b843'),
          ('Leaf_Sun', 'a9d255')]  # strictly dark -> light
C = Vector((0.5, -0.5, 30.0))
masses = [(t + Z * 0.5, rng.uniform(5.0, 6.0)) for t in tips]  # the flat base sits ~0.47 r below: tips stay deep
for n, rad, h, size in ((17, 16.0, 24.5, 5.6), (13, 10.5, 29.5, 5.8), (6, 4.5, 34.0, 5.6)):  # stepped tiers: a dome
    a1 = rng.uniform(0, 2 * math.pi)  # that spreads wide low down, lobed at the rim
    for k in range(n):
        p = horiz(a1 + 2 * math.pi * (k + rng.uniform(-0.3, 0.3)) / n) * rad * rng.uniform(0.85, 1.12)
        masses.append((C + Vector((p.x * 1.06, p.y, h - C.z + rng.uniform(-1.8, 1.8))), size * rng.uniform(0.8, 1.2)))
masses += [(C + Vector((rng.uniform(-8, 8), rng.uniform(-8, 8), rng.uniform(-3, 2))), 7.0) for _ in range(5)]  # core

bm = bmesh.new()
for c, r in masses:
    zb = c.z - r * 0.35  # flat-ish underside: the crown reads as layered masses with shaded bottoms
    for p, rr in [(c, r * 0.75)] + [(c + D.rand_dir(0.25) * r * 0.5, r * rng.uniform(0.45, 0.6)) for _ in range(6)]:
        for v in bmesh.ops.create_icosphere(bm, subdivisions=3 if rr > 2.5 else 2, radius=rr,
                                            matrix=Matrix.Translation(p))['verts']:
            if v.co.z < zb:
                v.co.z = zb - (zb - v.co.z) * 0.3
me = bpy.data.meshes.new('crown')
bm.to_mesh(me)
bm.free()
body = D.link('LeafShell0', me)
D.voxel_union(body, 0.4, displace=0.35)

bm = bmesh.new()  # leaf lumps over the body, toned by sun-facing, height and a slow noise; ranked so every tone shows
bm.from_mesh(body.data)
bm.normal_update()
faces = list(bm.faces)
picks = rng.choices(faces, [f.calc_area() for f in faces], k=int(2.0 * sum(f.calc_area() for f in faces)))
spots = [(f.calc_center_median(), f.normal.copy()) for f in picks]
bm.free()
zlo, zhi = min(c.z for c, _ in masses), max(c.z for c, _ in masses)
mass_val = [0.8 * (c - C).normalized().dot(SUN) + 0.6 * (c.z - zlo) / (zhi - zlo) + rng.gauss(0, 0.15)
            for c, _ in masses]  # each mass one coherent tone: sunny upper side light, shaded lower side dark


def mass_of(p):  # the leaf mass a crown point belongs to
    return min(range(len(masses)), key=lambda j: (p - masses[j][0]).length / masses[j][1])


val = [mass_val[mass_of(p)] + 0.6 * n.z + 0.2 * n.dot(SUN) + rng.gauss(0, 0.04) for p, n in spots]  # every top lit
rank = sorted(range(len(spots)), key=val.__getitem__)
CUM = [0.15, 0.36, 0.63, 0.87, 1.0]  # tone shares, shade -> sun
crust = [bmesh.new() for _ in LEAVES]
for r_, i in enumerate(rank):
    tone = next(t for t, c in enumerate(CUM) if r_ < c * len(rank))
    p, n = spots[i]
    r = rng.uniform(0.7, 1.3)
    bmesh.ops.create_icosphere(crust[tone], subdivisions=1, radius=r, matrix=Matrix.Translation(p + n * r * 0.25))

# the kite: caught on the crown's sunny shoulder, facing the camera; built now, while the body is tree-local
cam = CAM - D.TREE
bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
aims = [C + Vector((0.74, 0.67, 0)) * 12 + Z * dz for dz in (7, 5, 3, 1, -1)]  # top down: the first one that lands
hit, nor = next((h, n) for h, n, *_ in (bvh.ray_cast(cam, (a - cam).normalized()) for a in aims) if h)
KITE = hit + nor * 1.6 + D.TREE  # world
KITE_F = ((CAM - KITE).normalized() + nor * 0.5).normalized()

shells = [body]
for i, cb in enumerate(crust):
    if i:
        me = bpy.data.meshes.new('shell')
        shells.append(D.link(f'LeafShell{i}', me))
    else:
        cb.from_mesh(body.data)  # the darkest lumps join the body
    cb.to_mesh(shells[i].data)
    cb.free()
    D.voxel_union(shells[i], 0.22)
leafs = D.canopy_mesh(shells, [D.material(n, h) for n, h in LEAVES], 105000, smooth=1)

# ---------- in the tree (merged into the Trunk, bark first): swing ropes off the long limb, kite and tail ----------
bp = limbs[SWING][0]
hang = [min(bp, key=lambda q: abs(D.flat(q).length - rr)) for rr in (10.2, 13.4)]  # tree-local, inside the limb
SEAT_Z = 3.2
SEAT = [D.TREE + Vector((q.x, q.y, SEAT_Z)) for q in hang]  # world rope feet
bm = bmesh.new()
bm.from_mesh(trunk.data)
for q, s in zip(hang, SEAT):
    D.tube(bm, 1, [q + D.TREE, s + Z * 0.1], 0.17, side=Vector((1, 0, 0)), sides=6)
ku = (Z - KITE_F * Z.dot(KITE_F)).normalized()
ku = Matrix.Rotation(math.radians(28), 3, KITE_F) @ ku  # jaunty
ks = ku.cross(KITE_F)
rim = [KITE + ku * 2.4, KITE + ks * 1.7 + ku * 0.6, KITE - ku * 3.0, KITE - ks * 1.7 + ku * 0.6]
front, back = bm.verts.new(KITE + KITE_F * 0.22), bm.verts.new(KITE - KITE_F * 0.22)
rv = [bm.verts.new(p) for p in rim]
for k in range(4):
    for apex in (front, back):
        bm.faces.new((apex, rv[k], rv[(k + 1) % 4])).material_index = 2 + k % 2  # red and yellow quarters
tail = [KITE - ku * 3.0 + (-ku * 1.6 * j + ks * 0.7 * math.sin(j * 1.3)) - Z * 0.25 * j * j for j in range(6)]
D.tube(bm, 1, tail, 0.07, side=KITE_F, sides=4)
for j in (1, 3, 5):  # bows on the tail
    c = tail[j]
    bv = [bm.verts.new(c + ks * x + KITE_F * y) for x, y in ((0.55, 0), (0, 0.12), (-0.55, 0), (0, -0.12))]
    for apex in (bm.verts.new(c + ku * 0.3), bm.verts.new(c - ku * 0.3)):
        for k in range(4):
            bm.faces.new((apex, bv[k], bv[(k + 1) % 4])).material_index = 2 + (j // 2) % 2
bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f.material_index])
for f in bm.faces:
    f.smooth = f.material_index < 2
bm.to_mesh(trunk.data)
bm.free()
for n, h in (('Rope', 'c9b27a'), ('KiteRed', 'e0453a'), ('KiteYellow', 'f6c445')):
    trunk.data.materials.append(D.material(n, h))

# ---------- the water and the lawn: jetty, boat, reeds, picnic, deckchair, beach toys, hammock ----------
JA = math.radians(222)  # the jetty leaves the pond's left bank, running across the view into the water
JD = -horiz(JA)
J0 = D.pond_pt(JA) - JD * 3.0  # land end
JL = 11.0
PICNIC, PICNIC_YAW = Vector((-6.5, -9.0, 0.0)), math.radians(18)
CHAIR, BALL = Vector((19.0, 7.5, 0.0)), Vector((-2.0, -19.0, 0.0))  # deckchair facing the water; ball on the bank
HAMMOCK, HDIR = Vector((-17.0, -19.0, 0.0)), Vector((0.74, 0.67, 0.0)).normalized()  # on a stand, side on to the view


def keep_clear(p, pad):  # the shared pebbles, mounds, grass and flowers keep off the scene's own props
    return (D.flat(p - PICNIC).length < 6.5 + pad or D.flat(p - J0).length < 3.5 + pad
            or D.flat(p - CHAIR).length < 3.5 + pad or D.flat(p - BALL).length < 2.0 + pad
            or (abs((p - HAMMOCK).dot(HDIR)) < 6.5 + pad and abs((p - HAMMOCK).dot(Z.cross(HDIR))) < 2.5 + pad)
            or min(D.flat(p - s).length for s in SEAT) < 2.5 + pad)


def egg(bm, mi, c, x, y, z, sub=2):  # ellipsoid with semi-axes x, y, z (right-handed)
    D.prim(bm, 'icosphere', mi, D.frame(c, x, y, z), subdivisions=sub, radius=1.0)


def box(bm, mi, c, x, y, z):  # box with full-length axes x, y, z (right-handed)
    D.prim(bm, 'cube', mi, D.frame(c, x, y, z), size=1.0)


def extras():
    wood, dark = D.material('JettyWood', COLOURS['Wood']), D.material('JettyPost', COLOURS['WoodDark'])
    side = Z.cross(JD)

    bm = bmesh.new()  # swing seat: a plank between the rope feet
    d = (SEAT[1] - SEAT[0]).normalized()
    box(bm, 0, (SEAT[0] + SEAT[1]) / 2, d * ((SEAT[1] - SEAT[0]).length + 1.0), Z.cross(d) * 1.3, Z * 0.35)
    D.prop('SwingSeat', bm, wood, sharp=40)

    bm = bmesh.new()  # jetty: planks across two stringers, posts down into the water (on land they stop at the lawn)
    n = int(JL / 0.85)
    for k in range(n):
        c = J0 + JD * (JL * (k + 0.5) / n) + Z * 0.9
        box(bm, 0, c, JD * 0.72, side * (3.4 + rng.uniform(-0.2, 0.2)), Z * 0.28)
    for s in (-1, 1):
        box(bm, 1, J0 + JD * (JL / 2) + side * s * 1.2 + Z * 0.6, JD * JL, side * 0.4, Z * 0.35)
        for k in range(4):
            p = J0 + JD * (0.4 + (JL - 0.8) * k / 3) + side * s * 1.45
            D.rod(bm, 1, p + Z * (-0.1 if D.pond_gap(p) > 0.3 else -0.9), p + Z * 1.35, 0.28, 0.28, seg=8)
    D.prop('Jetty', bm, wood, dark, sharp=50)

    bm = bmesh.new()  # rowing boat in the open water by the jetty: cream hull, red gunwale, wooden floor, thwarts
    bd = Matrix.Rotation(math.radians(-8), 3, 'Z') @ JD
    bs = Z.cross(bd)
    pads = [D.flat(v.co) for v in bpy.data.objects['LilyPads'].data.vertices]  # finish() floats them first

    def jetty_gap(q):
        return D.flat(q - (J0 + JD * max(0.0, min(JL, (q - J0).dot(JD))))).length

    def foot(b):  # the hull's outline points
        return [b + bd * x + bs * y for x, y in ((3.9, 0), (-3.9, 0), (0, 1.8), (0, -1.8), (2, 1.2), (-2, -1.2))]

    B = max((b for b in (D.POND + Vector((x, y, 0.4)) for x in range(-9, 10) for y in range(-7, 8))
             if all(D.pond_gap(q) < -1.3 and jetty_gap(q) > 2.4 for q in foot(b))),  # clear of the reeds at the rim
            key=lambda b: (min(3.5, min((D.flat(q) - c).length for q in foot(b) for c in pads)), -jetty_gap(b)))
    # ^ clear of the pads, then as near the jetty as that allows: moored, not adrift

    def hull(x, y, z, k=1.0):  # unit sphere point -> hull: a pointed bow at +x, a flat top at the gunwale
        return B + bd * (x * 3.7 * k) + bs * (y * 1.6 * k * (1 - 0.6 * max(0.0, x) ** 2)) + Z * (min(z, 0.25) * 1.2)

    for v in D.prim(bm, 'icosphere', 0, Matrix.Identity(4), subdivisions=3, radius=1.0):
        v.co = hull(*v.co)
    for v in D.prim(bm, 'icosphere', 2, Matrix.Identity(4), subdivisions=3, radius=1.0):
        x, y, z = v.co
        v.co = hull(x, y, 0.25, 0.86) + Z * (0.02 + 0.08 * z)
    D.tube(bm, 1, [hull(0.968 * math.cos(a), 0.968 * math.sin(a), 0.25) + Z * 0.05
                   for a in (2 * math.pi * k / 40 for k in range(40))], 0.17, sides=6, closed=True)
    for x, w in ((-1.3, 2.7), (1.0, 2.2)):
        box(bm, 2, B + bd * x + Z * 0.3, bd * 0.6, bs * w, Z * 0.18)
    for s in (-1, 1):  # oars stowed along the thwarts
        a, b = B - bd * 1.9 + bs * s * 0.5 + Z * 0.5, B + bd * 1.6 + bs * s * 0.75 + Z * 0.5
        D.rod(bm, 2, a, b, 0.09, 0.09, seg=5)
        o = (b - a).normalized()
        box(bm, 2, b + o * 0.6, o * 1.3, Z.cross(o).normalized() * 0.5, Z * 0.1)
    D.prop('Boat', bm, D.material('BoatHull', 'f1ead8'), D.material('BoatTrim', 'c4473a'), wood, sharp=50)

    bm = bmesh.new()  # reeds and cattails along the far and right banks, clear of the jetty
    for a_deg in (20, 62, 105, 160):  # the front stays open: the boat is seen across it
        a = math.radians(a_deg)
        c = D.pond_pt(a) + horiz(a) * rng.uniform(-0.6, 0.6)
        for _ in range(rng.randint(7, 9)):
            phi, tilt, h = rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(4, 22)), rng.uniform(2.8, 5.0)
            b = c + horiz(phi) * rng.uniform(0, 1.0) - Z * 0.05
            D.rod(bm, rng.randrange(2), b, b + (horiz(phi) * math.sin(tilt) + Z * math.cos(tilt)) * h, 0.26, 0.0, seg=3)
        for _ in range(2):
            b = c + horiz(rng.uniform(0, 2 * math.pi)) * rng.uniform(0, 0.8) - Z * 0.05
            top = b + Z * rng.uniform(4.5, 6.0) + horiz(rng.uniform(0, 2 * math.pi)) * 0.4
            D.rod(bm, 0, b, top + Z * 0.5, 0.08, 0.06, seg=4)
            egg(bm, 2, top - Z * 0.4, Vector((0.3, 0, 0)), Vector((0, 0.3, 0)), Z * 0.85)
    D.prop('Reeds', bm, D.material('Reed', '5d9440'), D.material('ReedLight', '86b84c'),
           D.material('Cattail', '6f4527'))

    bm = bmesh.new()  # picnic: a checked blanket, half a watermelon and slices, a wicker basket, a straw hat
    x, y = horiz(PICNIC_YAW), horiz(PICNIC_YAW + math.pi / 2)
    box(bm, 1, PICNIC + Z * 0.09, x * 8.4, y * 6.0, Z * 0.14)  # cream cloth, red squares raised a hair on alternate
    for i in range(7):  # tiles (boxes, not an extruded grid: bmesh's extrude orders its output by memory address)
        for j in range(5):
            if (i + j) % 2 == 0:
                box(bm, 0, PICNIC + x * (1.2 * i - 3.6) + y * (1.2 * j - 2.4) + Z * 0.16, x * 1.17, y * 1.17, Z * 0.06)
    M = PICNIC + x * 1.6 + y * 0.6
    for v in D.prim(bm, 'icosphere', 2, Matrix.Translation(M + Z * 1.7), subdivisions=3, radius=1.7):
        v.co.z = min(v.co.z, M.z + 1.7)  # half a melon, cut face up
    D.prim(bm, 'cone', 3, Matrix.Translation(M + Z * 1.72), segments=24, radius1=1.5, radius2=1.5, depth=0.1)
    for k in range(3):  # slices: red half-moons with a green rind arc
        a = PICNIC_YAW + math.radians(200 + 35 * k)
        c = PICNIC + x * -0.4 + y * -0.4 + horiz(a) * 1.4 + Z * 0.2
        o, w = horiz(a), Z.cross(horiz(a))
        arc = [c + w * 1.2 * math.cos(t) + o * 1.2 * math.sin(t)
               for t in (math.pi * j / 10 - math.pi / 2 for j in range(11))]
        hull_pts = arc + [p + Z * 0.45 for p in arc]
        res = bmesh.ops.convex_hull(bm, input=[bm.verts.new(p) for p in hull_pts])
        for g in res['geom']:
            if isinstance(g, bmesh.types.BMFace):
                g.material_index = 3
        D.tube(bm, 2, arc, 0.22, side=Z, sides=6)
    K = PICNIC - x * 2.2 + y * 0.9  # basket: a tapered wicker box, a lid and an arched handle
    res = bmesh.ops.convex_hull(bm, input=[bm.verts.new(K + x * a * s + y * b * s + Z * z) for z, s in ((0.15, 0.85),
                                                                                                       (1.6, 1.0))
                                         for a in (-1.2, 1.2) for b in (-0.8, 0.8)])
    for g in res['geom']:
        if isinstance(g, bmesh.types.BMFace):
            g.material_index = 4
    box(bm, 4, K + Z * 1.7, x * 2.5, y * 1.7, Z * 0.25)
    D.tube(bm, 4, [K + x * 1.0 * math.cos(math.pi * j / 8) + Z * (1.8 + 1.3 * math.sin(math.pi * j / 8))
                   for j in range(9)], 0.14, side=y, sides=6)
    H = PICNIC - x * 2.6 - y * 1.6  # straw hat
    D.prim(bm, 'cone', 5, Matrix.Translation(H + Z * 0.25), segments=24, radius1=1.5, radius2=1.4, depth=0.12)
    egg(bm, 5, H + Z * 0.3, x * 0.85, y * 0.85, Z * 0.65)
    D.prim(bm, 'cone', 0, Matrix.Translation(H + Z * 0.45), segments=24, radius1=0.88, radius2=0.86, depth=0.22)
    D.prop('Picnic', bm, D.material('BlanketRed', 'd9443c'), D.material('BlanketWhite', 'f6efe4'),
           D.material('MelonRind', '2f7d36'), D.material('MelonFlesh', 'ef5a5a'), D.material('Wicker', 'c4934f'),
           D.material('HatStraw', 'ead07c'), sharp=40)

    bm = bmesh.new()  # striped deckchair: a sling of five stripes on a wooden A-frame, facing the pond
    fwd = D.flat(D.POND - CHAIR).normalized().to_3d()
    rt = fwd.cross(Z)
    sling = [CHAIR + fwd * (1.6 - 3.4 * t) + Z * (1.4 + 2.6 * t * t - 0.5 * math.sin(math.pi * t)) for t in
             (k / 6 for k in range(7))]  # front lip to the top of the back
    for j in range(5):
        for p0, p1 in zip(sling, sling[1:]):
            dd = p1 - p0
            box(bm, j % 2, (p0 + p1) / 2 + rt * (j - 2) * 0.5, rt * 0.47, dd * 1.12, rt.cross(dd.normalized()) * 0.12)
    for s_ in (-1, 1):
        o = rt * s_ * 1.35
        D.rod(bm, 2, CHAIR + fwd * 1.9 + o - Z * 0.05, CHAIR - fwd * 2.2 + o + Z * 4.4, 0.13, 0.13, seg=6)  # back legs
        D.rod(bm, 2, CHAIR - fwd * 2.0 + o - Z * 0.05, CHAIR + fwd * 0.6 + o + Z * 2.3, 0.13, 0.13, seg=6)  # front legs
    for z_, x_ in ((1.45, 1.65), (4.15, -1.95)):
        D.rod(bm, 2, CHAIR + fwd * x_ - rt * 1.4 + Z * z_, CHAIR + fwd * x_ + rt * 1.4 + Z * z_, 0.13, 0.13, seg=6)
    D.prop('Deckchair', bm, D.material('StripeBlue', '3f7fc4'), D.material('StripeWhite', 'f4f1ea'), wood, sharp=40)

    bm = bmesh.new()  # beach ball on the bank, and a swim ring afloat clear of the pads, jetty and boat
    D.prim(bm, 'icosphere', 0, Matrix.Translation(BALL + Z * 1.1), subdivisions=3, radius=1.15)
    for f in bm.faces:
        c = f.calc_center_median() - BALL - Z * 1.1
        f.material_index = 3 if abs(c.z) > 0.95 else int((math.atan2(c.y, c.x) + math.pi) / (math.pi / 3)) % 3
    pads = [v.co for v in bpy.data.objects['LilyPads'].data.vertices]
    boat = [v.co for v in bpy.data.objects['Boat'].data.vertices]
    clutter = [D.flat(q) for q in pads + boat]
    ring = max((D.POND + Vector((x, y, 0)) for x in range(-8, 9) for y in range(-6, 7)
                if D.pond_gap(D.POND + Vector((x, y, 0))) < -2.8 and jetty_gap(D.POND + Vector((x, y, 0))) > 3.0),
               key=lambda p: min((D.flat(p) - q).length for q in clutter))
    before = set(bm.faces)  # one closed torus, coloured in eight bands (overlapping parts would fool ray parity)
    D.tube(bm, 0, [ring + horiz(math.pi * k / 16) * 1.3 + Z * 0.2 for k in range(32)], 0.45, side=Z, sides=8,
           closed=True)
    for f in set(bm.faces) - before:
        c = f.calc_center_median() - ring
        f.material_index = 3 * (int((math.atan2(c.y, c.x) + math.pi) / (math.pi / 4)) % 2)
    D.prop('BeachToys', bm, D.material('ToyRed', 'e2453a'), D.material('ToyYellow', 'f6c83f'),
           D.material('ToyBlue', '3f7fc4'), D.material('ToyWhite', 'f7f3ea'))

    bm = bmesh.new()  # hammock: a striped sling sagging between two posts with braced feet
    hs = Z.cross(HDIR)
    for e in (-1, 1):
        foot = HAMMOCK + HDIR * e * 5.6
        D.rod(bm, 3, foot - Z * 0.05, foot + Z * 6.6, 0.32, 0.28, seg=8)
        egg(bm, 3, foot + Z * 6.75, HDIR * 0.4, hs * 0.4, Z * 0.32)  # knob
        for s_ in (-1, 1):  # splayed brace feet
            D.rod(bm, 3, foot + Z * 2.2, foot + hs * s_ * 1.8 - HDIR * e * 0.6 - Z * 0.05, 0.18, 0.18, seg=6)
    curve = [HAMMOCK + HDIR * lerp(-3.9, 3.9, t) + Z * (4.9 - 3.1 * math.sin(math.pi * t)) for t in
             (k / 10 for k in range(11))]
    for j in range(5):
        for p0, p1 in zip(curve, curve[1:]):
            dd = p1 - p0
            box(bm, j % 3, (p0 + p1) / 2 + hs * (j - 2) * 0.52, dd * 1.1, hs * 0.5, dd.normalized().cross(hs) * 0.14)
    for e, end in ((-1, curve[0]), (1, curve[-1])):
        hook = HAMMOCK + HDIR * e * 5.4 + Z * 6.2
        for s_ in (-1, 0, 1):
            D.rod(bm, 4, hook, end + hs * s_ * 1.2, 0.07, 0.07, seg=4)
    D.prop('Hammock', bm, D.material('HammockCoral', 'e2603a'), D.material('HammockCream', 'f4e3b5'),
           D.material('HammockGold', 'f2b53c'), dark, D.material('HammockCord', 'd9c79b'), sharp=40)


D.finish('summer', COLOURS, trunk, shells, leafs, tips, a0, pebbles=16, mounds=12, tufts=70, clumps=16, lotus=2,
         extras=extras, bridge=False, lantern=False, keep_clear=keep_clear)
