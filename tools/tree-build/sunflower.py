"""Build the sunflower diorama: public/models/sunflower.glb + public/trees/sunflower.json.

Run from the repo root: Blender -b -P tools/tree-build/sunflower.py (Blender 5.2, headless). Deterministic (fixed SEED).
This file is the scene: a stand of giant sunflowers in the corner of a summer kitchen garden, instead of a tree and
the pond garden. The stalks and leaf stems are the Trunk; the seed discs, two rows of fat petals, calyxes and leaves
are the Blossoms shells. Tilled beds of young sunflowers, taller row by row, lead up to the giants; a picket fence with
a gate runs along the two back edges; a beehive, hay bales, a wheelbarrow, a rain barrel and a watering can stand on
the lawn. The base, the shared lawn scatter, slot cloud, self-checks and export are in diorama.py.
"""
import math, os, sys
sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh, bpy
from mathutils import Vector, Matrix
import diorama as D
from diorama import Z, bez, lerp, horiz, rng

SEED = 20260808
D.init(SEED)
D.TREE = Vector((-12.0, 10.0, 0.0))  # back left; > 8.8 from the shared boulder at (-3.5, 15)
COLOURS = {  # scenery material -> hex sRGB (summer's)
    'Moss': '8fc83c', 'Stone': 'c9b8a0', 'PondBed': '3f7a6a', 'StoneChunk': '948572',
    'PondBank': '5f9a34', 'RimStone': 'bcae9a', 'RimStoneLight': 'd6cab8', 'Water': '7fd0ee',
    'FlowerCentre': 'f2c84b', 'LilyPad': '3f8f3a', 'Lotus': 'f6b7cf', 'Wood': '9c6b47', 'WoodDark': '6e4932',
    'LanternGlow': 'ffe2a0', 'LanternStone': 'bdb2a2', 'RockGrey': 'a39d93', 'RockPink': 'b0a496',
    'GrassDark': '4f9a2c', 'GrassLight': '9fd04a', 'MossDark': '7fba34', 'MossLight': 'a2d24a',
    'FlowerWhite': 'fbfaf4', 'FlowerLavender': '7d8fe8', 'Stem': '4f8f2e',
}
CAM = Vector((88.0, -98.0, 66.0))  # the default view; the heads turn to it as if to the sun
GOLDEN = math.pi * (3 - math.sqrt(5))

# Blossoms materials, deep -> pale: the slot palette takes [0], [1] and [-1]; accents sit in between
MATS = [D.material(n, h) for n, h in (('SeedDisc', '4a2c17'), ('PetalGold', 'f0a31a'), ('SeedEye', '7d5a23'),
                                      ('SunLeaf', '3d8a32'), ('SunLeafLight', '5aa83c'), ('PetalPale', 'ffd43b'))]
DISC, GOLD, EYE, LEAF, LEAF2, PALE = range(len(MATS))
VOXEL = (0.14, 0.16, 0.14, 0.2, 0.2, 0.16)
bms = [bmesh.new() for _ in MATS]

FLOWERS = [  # foot (x, y), head centre, head radius, petal cup deg, turn off the sun line (yaw, pitch deg), S sign,
    #          leaves (t along the stalk, blade length)
    ((-1.2, 2.1), (-2.6, 4.4, 37.0), 8.2, 0, (6, 0), 1, [(0.14, 12.0), (0.29, 11.0), (0.44, 10.0), (0.6, 8.5)]),
    ((-2.0, -1.35), (-11.7, -7.9, 31.0), 7.6, 0, (-14, 6), -1, [(0.17, 11.5), (0.36, 10.0), (0.55, 8.5)]),
    ((1.8, 1.6), (10.4, 9.4, 25.5), 7.2, 0, (12, -3), 1, [(0.2, 11.0), (0.42, 9.5), (0.62, 8.0)]),
    ((0.35, -2.4), (1.1, -7.1, 20.0), 6.4, 0, (-4, 4), -1, [(0.25, 10.0), (0.52, 8.5)]),
    ((2.4, -0.2), (8.8, -0.8, 13.0), 3.4, 38, (-20, 25), 1, [(0.55, 5.5)]),  # young, half open
]
U, W = Vector((-1, 1, 0)).normalized(), Vector((1, 1, 0)).normalized()  # bed axes: toward the stand, across
BEDS = [(-8.4, -28.0, 4.0, 'sun'), (-1.4, -31.0, 2.5, 'sun'), (5.6, -26.0, 4.5, 'sun'),  # world (w centre, u start,
        (12.6, -24.0, -5.0, 'lettuce')]  # u end, crop); the middle bed points straight at the stand (w -1.4, u 15.6)
BED_HW = 2.3


def sun(p):  # world point -> facing toward the camera, tilted up to the sun
    return ((CAM - p).normalized() + Z * 0.4).normalized()


PLANTS = []  # young sunflowers on the beds' two ridges (world foot, height), shorter toward the front
for wc, u0, u1, crop in BEDS[:3]:
    for j in range(int((u1 - u0 - 2.4) / 3.0) + 1):
        u = u0 + 1.2 + 3.0 * j
        PLANTS.append((U * u + W * (wc + 0.95 * (-1) ** j) + Z * 0.85,
                       lerp(0.8, 10.0, max(0.0, (u + 31) / 35.5) ** 1.25) * rng.uniform(0.9, 1.08)))
BORDER = [(Vector((x, y, 0)), rng.uniform(8.5, 11.0)) for x, y in  # clumps inside the back fences
          ((-31.5, -26.0), (-31.0, -21.5), (-31.5, -17.0), (13.5, 31.5), (18.0, 31.0), (22.5, 31.5))]


def ell(bm, c, x, y, z, sub=3):  # ellipsoid with semi-axes x, y, z (vectors, right-handed)
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0, matrix=D.frame(c, x, y, z))


def petal(bm, c, er, n, r0, L, W, T, bend):  # a fat petal from r0 to r0 + L along er, in the plane facing n
    et = n.cross(er)
    for v in bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)['verts']:
        x, y, z = v.co
        s = (x + 1) / 2
        v.co = c + er * (r0 + L * s) + et * (y * W / 2 * (1.15 - 0.4 * s)) + n * (z * T / 2 + bend * s * s)


def facing(H, yaw, pitch):  # toward the camera, tilted up to the sun, turned a little
    f = sun(H + D.TREE)
    f = Matrix.Rotation(math.radians(yaw), 3, 'Z') @ f
    return Matrix.Rotation(math.radians(pitch), 3, f.cross(Z).normalized()) @ f  # pitch > 0 tilts up


def head(H, f, R, cup):  # domed seed disc in a golden-angle spiral, two staggered petal rows, a green calyx behind
    u = Z.cross(f).normalized()
    v = f.cross(u)
    rd, dz = 0.5 * R, min(1.4, 0.3 * R)
    ell(bms[DISC], H, u * rd, v * rd, f * dz)
    ns = int(9 * rd * rd)
    for i in range(ns):
        r = rd * 0.93 * math.sqrt((i + 0.5) / ns)
        if r > rd * 0.38:
            th = i * GOLDEN
            p = H + (u * math.cos(th) + v * math.sin(th)) * r + f * dz * math.sqrt(1 - (r / rd) ** 2)
            bmesh.ops.create_icosphere(bms[DISC], subdivisions=1, radius=0.26, matrix=Matrix.Translation(p))
    ell(bms[EYE], H + f * (dz - 0.3), u * rd * 0.42, v * rd * 0.42, f * 0.55)
    n, a0, T = (14, rng.uniform(0, 2 * math.pi), 1.5) if R > 5 else (9, rng.uniform(0, 2 * math.pi), 1.2)
    c, s = math.cos(math.radians(cup)), math.sin(math.radians(cup))
    for row, (mi, fz, r0, reach, W, bend) in enumerate(((GOLD, -0.6, 0.8, 1.0, 0.3, -0.5),
                                                        (PALE, 0.1, 0.88, 0.93, 0.28, 0.6))):
        for k in range(n):
            th = a0 + 2 * math.pi * (k + 0.5 * row + rng.uniform(-0.08, 0.08)) / n
            er = u * math.cos(th) + v * math.sin(th)
            petal(bms[mi], H + f * fz, er * c + f * s, f * c - er * s, r0 * rd,
                  R * reach * rng.uniform(0.93, 1.05) - r0 * rd, W * R * 14 / n, T, bend + rng.uniform(-0.3, 0.3))
    cr = max(rd * 0.85, 1.7)
    ell(bms[LEAF], H - f * 1.0, u * cr, v * cr, f * 1.7)  # calyx
    for k in range(n):  # pointed bracts peeking behind the petals
        th = a0 + 2 * math.pi * (k + 0.25) / n
        er = u * math.cos(th) + v * math.sin(th)
        petal(bms[LEAF], H - f * 1.5, er * c + f * s, f * c - er * s, 0.5 * rd, 0.45 * R, 0.22 * R, 1.0, -0.6)


def leaf_pt(b, a, L, W, s, yn, zn, droop):  # heart-shaped blade: s along the midrib, yn across, zn through
    hw = W / 2 * s ** 0.45 * (1 - s) ** 0.6 / 0.488  # ovate outline, widest a bit before the middle
    along = L * s + 0.1 * L * (1 - yn * yn) * (1 - s) ** 6  # notch at the base
    up = zn * 0.7 * (1 - 0.4 * s) + L * (0.3 * s - droop * s * s) + 0.22 * W * yn * yn * s  # droops, edges cup up
    return b + a * along + Z.cross(a) * hw * yn + Z * up


def leaf(bm, b, a, L, W, droop):
    for v in bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)['verts']:
        x, y, z = v.co
        w = math.sqrt(max(1e-9, 1 - x * x))
        v.co = leaf_pt(b, a, L, W, (x + 1) / 2, y / w, z / w, droop)


# ---------- stalks (Trunk) and heads; leaves placed clear of the stalks, heads, garden plants and each other ----------
splines, tips, stalks = [], [], []
obstacles = [(p - D.TREE + Z * z, 1.5 + 0.15 * h) for p, h in PLANTS + BORDER for z in (0, h / 2, h)]  # tree-local
obstacles.append((Vector((-3.5, 15, 0.5)) - D.TREE, 2.3))  # the shared boulder
away = D.flat(D.TREE - CAM).normalized().to_3d()  # a blade pointing away from the camera droops edge-on to it
for foot, Hc, R, cup, (yaw, pitch), sgn, _ in FLOWERS:
    H = Vector(Hc)
    f = facing(H, yaw, pitch)
    F = Vector((foot[0], foot[1], -1.0))
    T = H - f * 1.0  # buried in the calyx
    h = T.z - F.z
    lean = D.flat(T - F).normalized().to_3d()
    P1 = F + Z * h * 0.42 - lean * h * 0.06 + Z.cross(lean) * h * 0.1 * sgn  # gentle S, sideways to the lean
    P2 = T - f * h * 0.28  # the neck bends over into the back of the head
    r0, r1 = (1.35, 0.95) if R > 5 else (1.0, 0.7)
    n = int(h / 0.4)
    pts = [bez(F, P1, P2, T, k / n) for k in range(n + 1)]
    rad = [lerp(r0, r1, k / n) * (1 + 0.3 * math.exp(-(k / n / 0.05) ** 2)) for k in range(n + 1)]  # swells at soil
    splines.append((pts, rad))
    tips.append(T)
    stalks.append((F, P1, P2, T, r0, r1))
    obstacles += [(p, r) for p, r in zip(pts, rad)] + [(H, R)]
    head(H, f, R, cup)

az = rng.uniform(0, 2 * math.pi)
for i, (*_, leaves) in enumerate(FLOWERS):
    F, P1, P2, T, r0, r1 = stalks[i]
    for t, L in leaves:
        S, rs = bez(F, P1, P2, T, t), lerp(r0, r1, t)
        az += math.radians(137.5)  # leaves spiral up the stalks
        wid, droop = L * 0.8, rng.uniform(0.55, 0.75)

        def blade(a):  # the blade's base and sample points for azimuth a
            b = S + horiz(a) * (rs + 1.8) + Z * 0.7
            return b, [leaf_pt(b, horiz(a), L, wid, s, yn, 0, droop)
                       for s in (0.3, 0.55, 0.8, 1.0) for yn in (-1, 0, 1)]

        def clearance(a):  # free space round the blade, and its lowest point
            qs = blade(a)[1]
            obs = [(p, r) for p, r in obstacles if (p - S).length > rs + 0.5]
            return min((q - p).length - r for q in qs for p, r in obs), min(q.z for q in qs)

        best = None
        for d in [0] + [sg * k for k in range(10, 190, 10) for sg in (1, -1)]:
            c, zlo = clearance(az + math.radians(d))
            ok = zlo > 1.0 and horiz(az + math.radians(d)).dot(away) < 0.55
            if ok and (best is None or c > best[0]):
                best = (c, az + math.radians(d))
            if ok and c > 1.5:
                break
        a = best[1]
        b, qs = blade(a)
        leaf(bms[LEAF2 if S.z > 13 else LEAF], b, horiz(a), L, wid, droop)  # upper leaves a sunnier green
        splines.append(([S, S + horiz(a) * (rs + 1.0) + Z * 0.5, b + horiz(a) * 0.6], [0.55, 0.5, 0.45]))  # leaf stem
        obstacles += [(q, 1.2) for q in qs]

trunk = D.trunk_mesh(splines, '3a6b28')

shells = []
for i, bm in enumerate(bms):
    me = bpy.data.meshes.new('shell')
    bm.to_mesh(me)
    bm.free()
    shells.append(D.link(f'SunShell{i}', me))
    D.voxel_union(shells[-1], VOXEL[i])
blossoms = D.canopy_mesh(shells, MATS, 68000, smooth=1)




# ---------- the garden: beds, fence and gate on the back edges, hive, bales, barrow, tomatoes, barrel, can ----------
def uw(u, w, z=0.0):  # world point from bed coordinates
    return U * u + W * w + Z * z


HIVE, BALES, BARROW, BARREL, CAN = uw(12, -21), uw(-2, -24), uw(-14, -15.5), uw(4, 17), uw(-33, 2.2)
TOMATOES = [uw(u, 20.0) for u in (-20, -13, -6)]
GATE, EDGE = (3.5, 9.5), 34.6  # x span of the gate in the back right fence; fence line, inside the base's bevel
KEEP = ([(HIVE, 3.5), (BALES, 5.0), (BARROW, 4.5), (BARREL, 3.0), (CAN, 3.5)] + [(p, 2.8) for p in TOMATOES]
        + [(p, 2.2) for p, _ in BORDER])


def open_ground(p, pad, _shared=D.open_ground):  # the shared grass, mounds, flowers and pebbles keep off beds and props
    u, w = p.dot(U), p.dot(W)  # 10.5 from the foot: a tuft 8.5 out can lean a blade 2.3 back into the 7 keep-out
    return (_shared(p, pad) and D.flat(p - D.FOOT).length > 10.5 + pad
            and all(D.flat(p - c).length > r + pad for c, r in KEEP)
            and not any(abs(w - wc) < BED_HW + 0.8 + pad and u0 - 0.8 - pad < u < u1 + 0.8 + pad
                        for wc, u0, u1, _ in BEDS))


D.open_ground = open_ground  # finish() looks the name up when it scatters


def egg(bm, mi, c, x, y, z, sub=2):  # ellipsoid with semi-axes x, y, z (right-handed)
    D.prim(bm, 'icosphere', mi, D.frame(c, x, y, z), subdivisions=sub, radius=1.0)


def box(bm, mi, c, x, y, z, bev=0.0):  # box with full-length axes x, y, z (right-handed), edges bevelled
    verts = D.prim(bm, 'cube', mi, D.frame(c, x, y, z), size=1.0)
    if bev:
        bmesh.ops.bevel(bm, geom=list({e for v in verts for e in v.link_edges}), offset=bev, segments=2, profile=0.5,
                        affect='EDGES')


def hull(bm, mi, pts):
    for g in bmesh.ops.convex_hull(bm, input=[bm.verts.new(p) for p in pts])['geom']:
        if isinstance(g, bmesh.types.BMFace):
            g.material_index = mi


def picket(bm, mi, p, out, t, h, y=0.55):  # a board with a pointed top, leaning a hair
    up = (Z + t * rng.uniform(-0.03, 0.03) + out * rng.uniform(-0.02, 0.02)).normalized()
    hull(bm, mi, [p + out * x + t * yy + up * z for x in (-0.22, 0.22) for yy in (-y, y) for z in (-0.15, h)]
         + [p + out * x + up * (h + 0.7) for x in (-0.22, 0.22)])


def extras():
    stalk_mat, leaf_mat = bpy.data.objects['Trunk'].data.materials[0], MATS[LEAF2]
    wood, dark = D.material('GardenWood', COLOURS['Wood']), D.material('GardenDark', '3b3632')

    bm = bmesh.new()  # tilled beds: a low soil slab (bottom just under the lawn top) with two ridges
    for wc, u0, u1, _ in BEDS:
        box(bm, 0, uw((u0 + u1) / 2, wc, 0.225), W * 2 * BED_HW, U * (u1 - u0), Z * 0.55, bev=0.25)
        for side in (-1, 1):
            D.tube(bm, 1, [uw(lerp(u0 + 0.5, u1 - 0.5, k / 12), wc + 0.95 * side, 0.5) for k in range(13)], 0.42,
                   side=Z, sides=8)
    D.prop('Beds', bm, D.material('Soil', '6b472c'), D.material('SoilTilled', '86603c'))

    bm = bmesh.new()  # sprouts at the front of the beds, young sunflowers facing the sun toward the back
    for p, h in PLANTS + BORDER:
        a0 = rng.uniform(0, 2 * math.pi)
        if h < 3.0:
            D.rod(bm, 0, p - Z * 0.3, p + Z * h, 0.1, 0.08, seg=5)
            for k in (0, 1):
                d = (horiz(a0 + math.pi * k) + Z * 0.35).normalized()
                s = Z.cross(d).normalized()
                egg(bm, 1, p + Z * h + d * 0.5, d * 0.55, s * 0.32, d.cross(s) * 0.1)
            continue
        R = 0.35 + 0.16 * h
        f = sun(p + Z * h)
        top = p + Z * h + D.flat(f).to_3d() * h * 0.08
        D.rod(bm, 0, p - Z * 0.3, top, 0.14 + 0.025 * h, 0.1 + 0.015 * h, seg=6)
        for k in range(2 if h < 6 else 3):
            d = (horiz(a0 + 2.4 * k) - Z * 0.3).normalized()
            s = Z.cross(d).normalized()
            L = min(3.2, 0.9 + 0.25 * h)
            egg(bm, 1, p + Z * h * (0.28 + 0.24 * k) + d * (L * 0.5 + 0.1), d * L * 0.5, s * L * 0.32,
                d.cross(s) * 0.12)
        u = Z.cross(f).normalized()
        v = f.cross(u)
        egg(bm, 4, top - f * R * 0.15, u * R * 0.42, v * R * 0.42, f * R * 0.25)  # calyx
        egg(bm, 3, top + f * R * 0.08, u * R * 0.5, v * R * 0.5, f * R * 0.22)  # seed disc
        for k in range(10):
            er = u * math.cos(a0 + 0.2 * math.pi * k) + v * math.sin(a0 + 0.2 * math.pi * k)
            egg(bm, 2, top + er * R * 0.72, er * R * 0.34, f.cross(er) * R * 0.15, f * max(0.1, R * 0.08), sub=1)
    wc, u0, u1, _ = BEDS[3]
    for j in range(int((u1 - u0 - 1.6) / 2.4) + 1):  # lettuces: a loose dark rosette round a pale heart
        c = uw(u0 + 1.0 + 2.4 * j, wc + 0.95 * (-1) ** j, 0.95)
        D.blob(bm, 4, c, 1.05, (1, 1, 0.55), sub=2, rough=0.3, yaw=rng.uniform(0, 6.3))
        D.blob(bm, 1, c + Z * 0.3, 0.7, (1, 1, 0.8), sub=2, rough=0.15)
    for p in TOMATOES:  # tomatoes on a teepee of three canes
        a0 = rng.uniform(0, 2 * math.pi)
        for k in range(3):
            foot = p + horiz(a0 + 2 * math.pi * k / 3) * 1.4
            D.rod(bm, 5, foot - Z * 0.05, foot + (p + Z * 7.6 - foot) * 1.12, 0.12, 0.1, seg=5)
        for k in range(6):  # leafy tufts climbing the canes in turn, the canes showing between them
            z = 1.0 + 1.1 * k
            c = p + horiz(a0 + 2 * math.pi * k / 3) * 1.4 * (1 - z / 7.6) + Z * z
            r = lerp(0.95, 0.6, k / 5)
            D.blob(bm, 4, c, r, (1, 1, 0.8), sub=2, rough=0.3, yaw=rng.uniform(0, 6.3))
            for _ in range(3 if k < 4 else 1):  # trusses hanging off the tuft
                a = rng.uniform(0, 2 * math.pi)
                D.blob(bm, 6, c + horiz(a) * r * 0.9 - Z * rng.uniform(0.2, 0.6), 0.42, sub=2)
    D.prop('Seedlings', bm, stalk_mat, leaf_mat, MATS[PALE], MATS[DISC], MATS[LEAF], D.material('Cane', 'c9b27a'),
           D.material('Tomato', 'e2432e'))

    bm = bmesh.new()  # picket fence on the two back edges, rails on the garden side, an arched gate
    for a, b, out in ((Vector((-EDGE, -33.0, 0)), Vector((-EDGE, EDGE, 0)), Vector((-1, 0, 0))),
                      (Vector((-EDGE, EDGE, 0)), Vector((33.0, EDGE, 0)), Vector((0, 1, 0)))):
        t, n = (b - a).normalized(), int((b - a).length / 1.75)
        spans = [(a, b)] if out.x else [(a, Vector((GATE[0], EDGE, 0))), (Vector((GATE[1], EDGE, 0)), b)]
        for k in range(1, n):
            p = a + (b - a) * k / n
            if out.x or not GATE[0] - 0.6 < p.x < GATE[1] + 0.6:
                picket(bm, 0, p, out, t, 6.0 + rng.uniform(-0.2, 0.2))
        for p0, p1 in spans:
            for z in (1.6, 4.4):
                box(bm, 0, (p0 + p1) / 2 - out * 0.42 + Z * z, t * (p1 - p0).length, out * 0.3, Z * 0.6)
        for p in (a, b):
            box(bm, 0, p + Z * 3.5, t * 0.9, out * 0.9, Z * 7.2, bev=0.1)
            egg(bm, 0, p + Z * 7.4, t * 0.5, out * 0.5, Z * 0.5)
    t, out = Vector((1, 0, 0)), Vector((0, 1, 0))
    for x in GATE:
        box(bm, 0, Vector((x, EDGE, 3.6)), t * 0.9, out * 0.9, Z * 7.4, bev=0.1)
        egg(bm, 0, Vector((x, EDGE, 7.6)), t * 0.5, out * 0.5, Z * 0.5)
    for k in range(5):
        x = lerp(GATE[0] + 0.95, GATE[1] - 0.95, k / 4)
        picket(bm, 0, Vector((x, EDGE, 0.3)), out, t, 5.0 + 0.9 * math.sin(math.pi * k / 4), y=0.45)
    for z in (1.5, 4.2):
        box(bm, 0, Vector(((GATE[0] + GATE[1]) / 2, EDGE - 0.42, z)), t * (GATE[1] - GATE[0] - 0.8), out * 0.3,
            Z * 0.55)
    D.rod(bm, 0, Vector((GATE[0] + 0.7, EDGE - 0.45, 1.6)), Vector((GATE[1] - 0.7, EDGE - 0.45, 4.1)), 0.2, 0.2, seg=4)
    D.prop('Fence', bm, D.material('Picket', 'f3eee2'), sharp=40)

    bm = bmesh.new()  # beehive: stand, three stacked boxes (overlapping, so no coincident faces), lid, gable roof
    x = D.flat(CAM - HIVE).normalized().to_3d()
    y = Z.cross(x)
    for sx in (-1, 1):
        for sy in (-1, 1):
            D.rod(bm, 4, HIVE + x * 1.2 * sx + y * 1.0 * sy - Z * 0.1, HIVE + x * 1.2 * sx + y * 1.0 * sy + Z * 1.1,
                  0.18, 0.18, seg=6)
    box(bm, 4, HIVE + Z * 1.2, x * 3.4, y * 3.0, Z * 0.3, bev=0.05)
    for z0, z1, mi in ((1.3, 3.25, 0), (3.2, 4.95, 1), (4.9, 6.1, 0)):
        box(bm, mi, HIVE + Z * ((z0 + z1) / 2), x * 3.0, y * 2.6, Z * (z1 - z0), bev=0.1)
    box(bm, 2, HIVE + Z * 6.25, x * 3.3, y * 2.9, Z * 0.35, bev=0.05)
    hull(bm, 2, [HIVE + x * sx * 1.75 + y * sy * 1.6 + Z * 6.35 for sx in (-1, 1) for sy in (-1, 1)]
         + [HIVE + y * sy * 1.6 + Z * 7.4 for sy in (-1, 1)])
    box(bm, 3, HIVE + x * 1.45 + Z * 1.65, x * 0.25, y * 1.6, Z * 0.25)  # entrance slot
    box(bm, 4, HIVE + x * 1.8 + Z * 1.42, x * 0.7, y * 1.8, Z * 0.12)  # landing board
    D.prop('Beehive', bm, D.material('HiveWhite', 'f4ecd6'), D.material('HiveHoney', 'f2c45a'),
           D.material('HiveRoof', '8d949c'), dark, wood, sharp=40)

    bm = bmesh.new()  # hay bales: two side by side, one across on top, each with two twine bands
    x = horiz(0.35)
    y = Z.cross(x)
    for c, bx, by in ((BALES - y * 1.25 + Z * 0.95, x, y), (BALES + y * 1.25 + Z * 0.95, x, y),
                      (BALES + Z * 2.8, y, -x)):
        box(bm, 0, c, bx * 3.6, by * 2.2, Z * 1.9, bev=0.35)
        for s in (-0.9, 0.9):
            box(bm, 1, c + bx * s, bx * 0.18, by * 2.3, Z * 2.0, bev=0.08)
    D.prop('HayBales', bm, D.material('Straw', 'e6c55a'), D.material('Twine', 'b88f3a'), sharp=50)

    bm = bmesh.new()  # wheelbarrow, wheel toward the stand, a heap of soil in the tray
    d, s = U, Z.cross(U)
    P = BARROW
    hull(bm, 0, [P + d * a + s * b + Z * 1.5 for a in (-1.3, 1.0) for b in (-0.9, 0.9)]
         + [P + d * a + s * b + Z * 2.8 for a in (-1.9, 1.9) for b in (-1.5, 1.5)])
    D.blob(bm, 1, P + Z * 2.75, 1.3, (1.25, 1.0, 0.45), sub=2, rough=0.15)
    hub = P + d * 2.4 + Z * 0.95
    D.prim(bm, 'cone', 2, D.frame(hub, Z, d, s), segments=16, radius1=0.95, radius2=0.95, depth=0.55, cap_ends=True)
    for b in (-1, 1):
        D.rod(bm, 3, P + d * 1.2 + s * b * 0.6 + Z * 1.8, hub + s * b * 0.35, 0.12, 0.12, seg=5)
        D.rod(bm, 3, P + d * -0.6 + s * b * 1.0 + Z * 1.7, P + d * -4.0 + s * b * 1.3 + Z * 2.0, 0.15, 0.13, seg=6)
        D.rod(bm, 3, P + d * -1.0 + s * b * 0.8 + Z * 1.7, P + d * -1.2 + s * b * 0.9 - Z * 0.05, 0.13, 0.13, seg=5)
    D.prop('Wheelbarrow', bm, D.material('Barrow', 'd2553f'), D.material('BarrowSoil', '6b472c'),
           D.material('Tyre', '3a3a3a'), wood)

    bm = bmesh.new()  # rain barrel: two overlapping bellied halves, iron hoops, dark water on top
    for z0, z1, r0, r1 in ((0.0, 1.7, 1.4, 1.66), (1.5, 3.2, 1.66, 1.4)):
        D.prim(bm, 'cone', 0, Matrix.Translation(BARREL + Z * ((z0 + z1) / 2)), segments=18, radius1=r0, radius2=r1,
               depth=z1 - z0, cap_ends=True)
    for z, r in ((0.45, 1.5), (1.6, 1.69), (2.75, 1.5)):
        D.tube(bm, 1, [BARREL + horiz(2 * math.pi * k / 18) * r + Z * z for k in range(18)], 0.1, sides=5, closed=True)
    D.prim(bm, 'cone', 2, Matrix.Translation(BARREL + Z * 3.15), segments=18, radius1=1.25, radius2=1.25, depth=0.12,
           cap_ends=True)
    D.prop('RainBarrel', bm, wood, D.material('Hoop', '5b5f63'), D.material('BarrelWater', '4f8fb0'), sharp=50)

    bm = bmesh.new()  # watering can at the end of the beds, side on to the camera
    P, k = CAN, 1.3
    view = P - CAM
    d = Vector((view.y, -view.x, 0)).normalized()
    D.prim(bm, 'cone', 0, Matrix.Translation(P + Z * 1.2 * k), segments=20, radius1=1.35 * k, radius2=1.2 * k,
           depth=2.4 * k, cap_ends=True)
    tip = P + (d * 3.0 + Z * 2.7) * k
    D.rod(bm, 0, P + (d * 0.9 + Z * 0.6) * k, tip, 0.3 * k, 0.18 * k, seg=8)
    sd = (d + Z).normalized()
    D.rod(bm, 1, tip - sd * 0.1 * k, tip + sd * 0.35 * k, 0.18 * k, 0.45 * k, seg=10)
    D.tube(bm, 0, [P + (d * (-1.0 + 1.4 * j / 8) + Z * (2.3 + 1.3 * math.sin(math.pi * j / 8))) * k for j in range(9)],
           0.17 * k, side=Z.cross(d), sides=6)
    D.prop('WateringCan', bm, D.material('Can', '5f9fd0'), D.material('CanRose', '4a7fa8'), sharp=50)


D.finish('sunflower', COLOURS, trunk, shells, blossoms, tips, Vector((0, 0, 0)), pebbles=12, mounds=10, tufts=70,
         clumps=10, lotus=0, extras=extras, pond=False, bridge=False, lantern=False)
