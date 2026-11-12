"""Build the snowman diorama: public/models/snowman.glb + public/trees/snowman.json.

Run from the repo root: Blender -b -P tools/tree-build/snowman.py (Blender 5.2, headless). Deterministic (fixed SEED).
This file is the season: no tree but a three-ball snowman (top hat, carrot nose, coal face, twig arms, red scarf,
a besom) in a snowy clearing someone has been playing in: snow-laden firs round the back, a half-built snow fort with
its snowball ammunition, a swept skating rink, a log pile, a dropped sledge and the trails between them. No pond,
bridge or lantern. The hat, twig arms and besom are the Trunk (the dark structural slot class, hat colour first); the
snow balls, scarf, carrot and coal are the canopy shells. The base, props, slot cloud, self-checks and export are
shared with the other seasons in diorama.py.
"""
import math, os, sys
sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh, bpy
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree
import diorama as D
from diorama import Z, lerp, horiz, wobbly, rng

SEED = 20261225
D.init(SEED)
D.TREE = Vector((-7.0, 6.0, 0.0))  # just behind the board centre: the clearing's set pieces ring it
COLOURS = {  # winter.py's garden: Moss is the snow on the base top
    'Moss': 'eef2f7', 'Stone': '8a8f99', 'PondBed': '587a8c', 'StoneChunk': '6c717b',
    'PondBank': 'dde4ed', 'RimStone': '7f848c', 'RimStoneLight': 'a3a8b0', 'Water': 'cfe5ef',
    'FlowerCentre': 'f2c84b', 'LilyPad': 'e1ecf2', 'Wood': 'a8432f', 'WoodDark': '742c20',
    'LanternGlow': 'ffd68a', 'LanternStone': 'a3a7ae', 'RockGrey': '6f747c', 'RockPink': '8a8f97',
    'GrassDark': 'a49c7e', 'GrassLight': 'c8bf9c', 'MossDark': 'f3f6fa', 'MossLight': 'f8fafd',
    'FlowerWhite': 'f6f3e8', 'FlowerLavender': 'c23a45', 'Stem': '50683a',
}
# canopy, deep to pale as in winter.py (the brightest is tinted so it does not derive to a vivid blue); the accents sit
# in the middle of the list because the slot palette reads materials 0, 1 and -1
SNOW = [('Snow_Shadow', 'c3d0e2'), ('Snow', 'e4ebf4'), ('Snow_Bright', 'f6f9fc')]
ACCENTS = [('Scarf', 'c4313a'), ('ScarfStripe', 'f1e4c3'), ('Carrot', 'f07a24'), ('Coal', '2b2a30')]
MATS = SNOW[:2] + ACCENTS + SNOW[2:]
MI = {n: i for i, (n, _) in enumerate(MATS)}

F = horiz(math.radians(-25))  # faces the default camera (az -47 deg), turned a touch for a three-quarter view
S = Z.cross(F)  # the snowman's left, the viewer's right
LIGHT = Vector((60, -40, 90)).normalized()  # preview.py's key light
LH = Vector((LIGHT.x, LIGHT.y, 0)).normalized()

BALLS = [  # centre, radius, height squash, lump amplitude: bottom, middle, head
    (Vector((0.0, 0.0, 5.8)), 6.5, 0.92, 0.45),
    (Vector((0.2, -0.1, 14.6)), 4.8, 1.0, 0.32),
    (Vector((0.1, 0.1, 21.8)), 3.5, 1.0, 0.2),
]
M, H = BALLS[1][0], BALLS[2][0]
PLACE = Matrix.Translation(D.TREE) @ Matrix.Scale(1.2, 4)  # modelled at 29 tall, shown at 35 to hold the board like the trees do
# one overlapping layer per snow shade (offset in ball radii, scale): where a layer pokes out of the others it shows
LAYERS = [((-Z * 0.85 - LH * 0.5).normalized() * 0.15, 0.966),  # shadow: the lower, far side
          (Vector(), 1.0),
          (LIGHT * 0.10, 0.96)]  # bright: the lit cap
ROT = Matrix.Rotation(math.radians(8), 3, F) @ Matrix.Rotation(math.radians(-6), 3, S)  # head: tilted, looking up
FH, SH, UH = ROT @ F, ROT @ S, ROT @ Z
UHAT = Matrix.Rotation(math.radians(7), 3, FH) @ UH  # a jaunty extra tilt
XHAT = (FH - UHAT * FH.dot(UHAT)).normalized()
HAT_AT = H + UHAT * 2.6
HAT_FRAME = D.frame(HAT_AT, XHAT, UHAT.cross(XHAT), UHAT)


def lathe(bm, mat4, prof, mis, seg=40, warp=None):  # closed surface of revolution: prof [(r, z)], r = 0 at both poles
    rings = []
    for r, z in prof:
        pts = [Vector((0, 0, z))] if r == 0 else [Vector((r * math.cos(a), r * math.sin(a), z))
                                                  for a in (2 * math.pi * k / seg for k in range(seg))]
        rings.append([bm.verts.new(mat4 @ (warp(p) if warp else p)) for p in pts])
    for j, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for k in range(seg):
            k1 = (k + 1) % seg
            vs = ((r0[0], r1[k1], r1[k]) if len(r0) == 1 else (r0[k], r0[k1], r1[0]) if len(r1) == 1
                  else (r0[k], r0[k1], r1[k1], r1[k]))
            bm.faces.new(vs).material_index = mis[j]


def ribbon(bm, pts, sides_v, w, t, mis, sides=10, closed=False):  # D.tube with an elliptic section (w along side)
    n, rings = len(pts), []
    for i, p in enumerate(pts):
        tg = (pts[(i + 1) % n if closed else min(i + 1, n - 1)] - pts[(i - 1) % n if closed else max(i - 1, 0)])
        tg.normalize()
        sd = sides_v[i]
        a = (sd - tg * sd.dot(tg)).normalized()
        b = tg.cross(a)
        rings.append([bm.verts.new(p + a * w * math.cos(2 * math.pi * k / sides) + b * t * math.sin(2 * math.pi * k / sides))
                      for k in range(sides)])
    pairs = list(zip(rings, rings[1:] + rings[:1] if closed else rings[1:]))
    for j, (r0, r1) in enumerate(pairs):
        for k in range(sides):
            bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k])).material_index = mis[j]
    if not closed:
        bm.faces.new(rings[0][::-1]).material_index = mis[0]
        bm.faces.new(rings[-1]).material_index = mis[-1]


def shell(name, bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return D.link(name, me)


def bvh(ob):
    return BVHTree.FromPolygons([v.co for v in ob.data.vertices], [p.vertices[:] for p in ob.data.polygons])


# ---------- snow: three lumpy balls, one voxel-unioned shell per shade, a bank of snow packed round the foot ----------
snow = []
for i, (off, scale) in enumerate(LAYERS):
    bm = bmesh.new()
    for j, (c, r, sz, lump) in enumerate(BALLS):
        o = c + off * r
        for v in bmesh.ops.create_icosphere(bm, subdivisions=5, radius=1.0, matrix=Matrix.Translation(o))['verts']:
            n = v.co - o  # unit; the lumps depend on the direction only, so every layer shares them
            v.co = o + Vector((n.x, n.y, n.z * sz)) * (r * scale + lump * noise.noise(n * r * 0.3 + Vector((5.1 * j, 0, 0))))
    if i == 1:
        for k in range(9):
            a = 2 * math.pi * k / 9 + rng.uniform(-0.2, 0.2)
            D.blob(bm, 0, horiz(a) * rng.uniform(3.6, 4.4) + Z * 0.2, rng.uniform(1.6, 2.1), (1, 1, 0.5), sub=3,
                   rough=0.1, yaw=a)
    if i == 2:  # a cushion of fresh snow on the hat
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0,
                                   matrix=D.frame(HAT_AT + UHAT * 4.25, XHAT * 2.25, UHAT.cross(XHAT) * 2.25, UHAT * 0.45))
    me = bpy.data.meshes.new('shell')
    bm.to_mesh(me)
    bm.free()
    ob = D.link(f'SnowShell{i}', me)
    D.voxel_union(ob, 0.2)
    for v in ob.data.vertices:  # each layer its own fine noise, so the shade boundaries wander
        v.co += v.normal * 0.07 * noise.noise(v.co * 0.3 + Vector((7.3 * i, 0, 0)))
        v.co.z = max(v.co.z, -0.25)  # flat on the lawn
    for p in ob.data.polygons:
        p.material_index = MI[SNOW[i][0]]
    snow.append(ob)
BVHS = [bvh(ob) for ob in snow]


def surf(c, d):  # outermost snow surface from c along unit d
    return c + d * max((b.ray_cast(c, d)[3] or 0.0) for b in BVHS)


def hdir(az, el):  # direction from the head centre in the head's frame, degrees: az to its left, el up
    az, el = math.radians(az), math.radians(el)
    return (FH * math.cos(az) + SH * math.sin(az)) * math.cos(el) + UH * math.sin(el)


# ---------- face and buttons: coal lumps half pressed in, a crooked carrot ----------
bm = bmesh.new()


def coal(c, d, r, flat=0.6):
    a = d.orthogonal().normalized()
    p = surf(c, d) - d * r * 0.25
    for v in D.prim(bm, 'icosphere', MI['Coal'], D.frame(p, a, d.cross(a), d * flat), subdivisions=2, radius=r):
        v.co += (v.co - p).normalized() * r * 0.2 * noise.noise(v.co * 2.3)


for s in (-1, 1):
    coal(H, hdir(23 * s, 20), 0.5)
for k in range(7):
    az = -36 + 12 * k
    coal(H, hdir(az, -25 + 9 * (az / 36) ** 2), 0.28)
for el in (32, 10, -12):
    coal(M, (F * math.cos(math.radians(el)) + Z * math.sin(math.radians(el))), 0.55)
coal_ob = shell('Coal', bm)

bm = bmesh.new()
d = hdir(4, -10)
down = (-Z - d * (-Z).dot(d)).normalized()
L_CARROT = 4.4
prof = [(0, -0.9)] + [(0.66 * (1 - k / 18) ** 0.8 * (0.94 if k % 2 else 1.0), -0.8 + (L_CARROT + 0.8) * k / 18)
                      for k in range(18)] + [(0, L_CARROT)]
lathe(bm, D.frame(surf(H, hdir(0, -4)), down, d.cross(down), d), prof, [MI['Carrot']] * (len(prof) - 1), seg=16,
      warp=lambda p: p + Vector((0.4 * max(0.0, p.z / L_CARROT) ** 2, 0, 0)))  # droops a little at the tip
carrot_ob = shell('Carrot', bm)

# ---------- scarf: a fat knitted roll round the neck, a knot at the front, two tails down the chest ----------
A = (H - M).normalized()
NECK = M + (H - M) * 0.58
AX = (F - A * F.dot(A)).normalized()
AY = A.cross(AX)
bm, ring = bmesh.new(), []
for k in range(48):
    a = 2 * math.pi * k / 48
    dd = AX * math.cos(a) + AY * math.sin(a)
    ring.append(surf(NECK, dd) + dd * 0.5 - A * 0.25 * math.cos(a) + dd * 0.1 * noise.noise(dd * 3.0))
ribbon(bm, ring, [A] * 48, 1.1, 0.8, [MI['Scarf']] * 48, closed=True)
KD = (F * math.cos(math.radians(40)) + S * math.sin(math.radians(40)))
knot = surf(NECK, KD) + KD * 0.9 - A * 0.4
D.prim(bm, 'icosphere', MI['Scarf'], D.frame(knot, KD * 0.85, Z.cross(KD) * 1.0, Z * 1.05), subdivisions=3, radius=1.0)
kv = knot - M
e0 = math.degrees(math.atan2(kv.z, Vector((kv.x, kv.y)).length))
az0 = math.degrees(math.atan2(KD.y, KD.x))
for daz, e1, lift in ((-6, -16, 0.0), (16, 6, 0.6)):
    pts, sides = [], []
    for k in range(13):
        t = k / 12
        az, e = math.radians(az0 + daz * t), math.radians(lerp(e0 - 6, e1, t))
        dd = horiz(az) * math.cos(e) + Z * math.sin(e)
        pts.append(surf(M, dd) + dd * (0.3 + lift * t * t))
        sides.append(horiz(az + math.pi / 2))
    pts[0] = knot
    ribbon(bm, pts, sides, 0.85, 0.22,
           [MI['ScarfStripe'] if 0.66 <= k / 12 < 0.75 or 0.83 <= k / 12 < 0.92 else MI['Scarf'] for k in range(12)])
scarf_ob = shell('Scarf', bm)


def canopy(layers, accents, budget):  # D.canopy_mesh, but only the snow is decimated: the small accents keep every face
    ratio = budget / sum(D.tris(ob.data) for ob in layers)
    bm = bmesh.new()
    for ob in layers + accents:
        if ob in layers:
            D.smooth_decimate(ob, 2, ratio)
        ob.data.transform(PLACE)
        bm.from_mesh(ob.data)  # appends, keeping each face's material index
    me = bpy.data.meshes.new('Blossoms')
    bm.to_mesh(me)
    bm.free()
    ob = D.link('Blossoms', me)
    for n, h in MATS:
        me.materials.append(D.material(n, h))
    me.shade_smooth()
    return ob


accents = [scarf_ob, carrot_ob, coal_ob]
shells = snow + accents
blossoms = canopy(snow, accents, 60000)

# ---------- trunk: the top hat (red band) and the twig arms, one waving ----------
bm = bmesh.new()
HAT = [(0, 0.0), (2.0, 0.0), (3.0, 0.03), (3.28, 0.12), (3.3, 0.22), (3.12, 0.32), (2.4, 0.33), (2.18, 0.36),
       (2.24, 0.45), (2.26, 0.5), (2.26, 1.15), (2.24, 1.2), (2.2, 1.3), (2.36, 3.95), (2.3, 4.15), (2.1, 4.25),
       (1.2, 4.3), (0, 4.31)]


def curl(p):  # the brim turns up at the sides
    r = p.xy.length
    if r > 2.5:
        p.z += 0.5 * ((r - 2.5) / 0.8) ** 2 * (p.y / r) ** 2
    return p


lathe(bm, HAT_FRAME, HAT, [1 if 0.44 < z0 < 1.25 and 0.44 < z1 < 1.25 else 0 for (_, z0), (_, z1) in zip(HAT, HAT[1:])],
      seg=48, warp=curl)
hat = shell('Hat', bm)


def twig(q, d, length, r0, r1, key):
    end = q + d.normalized() * length
    pts, rad = wobbly(q, q + (end - q) * 0.33, q + (end - q) * 0.66, end, r0, r1, 0.15, key)
    return [q] + pts, [r0] + rad


splines, hands = [], {}
for side, p1, p2, p3, fingers, sprig, key in (
        (1, (6.5, 1.6, 0.5), (8.6, 4.5, 1.2), (9.0, 8.0, 1.5),  # waving: out and up (side, up, forward)
         ((0.5, 0.85, 0.0, 1.9), (0.0, 1.0, 0.3, 2.3), (0.9, 0.3, -0.2, 1.6)), (0.55, (0.5, 0.6, -0.6), 1.8), 0),
        (-1, (5.5, 1.2, 0.3), (8.0, 0.2, 1.2), (9.5, -1.8, 1.8),  # resting: out and a little down
         ((1.0, -0.4, 0.0, 1.8), (0.7, -0.2, 0.6, 1.6), (0.8, -0.8, 0.0, 1.5)), (0.5, (-0.5, 0.8, 0.0), 1.6), 1)):
    W = S * side

    def at(v, base=M):
        return base + W * v[0] + Z * v[1] + F * v[2]

    p0 = at((2.0, 0.8, 0.0))
    pts, rad = wobbly(p0, at(p1), at(p2), at(p3), 0.5, 0.2, 0.4, 60 + key)
    splines.append(([p0] + pts, [0.5] + rad))
    q = hands[side] = pts[int(0.88 * len(pts))]
    for j, (x, y, z, length) in enumerate(fingers):
        splines.append(twig(q, W * x + Z * y + F * z, length, 0.2, 0.1, 70 + 5 * key + j))
    at_, (x, y, z), length = sprig
    k = int(at_ * len(pts))
    splines.append(twig(pts[k], W * x + Z * y + F * z, length, rad[k] * 0.7, 0.1, 80 + key))

# a besom in the resting hand: the handle stands in the snow, the bristles up by the head
q = hands[-1]
BD = (Z + S * 0.08 + F * 0.03).normalized()  # leans in a little
foot_b = q - BD * ((q.z + 0.05) / BD.z)
handle = [foot_b + BD * (k * 0.5) for k in range(int((q - foot_b).length / 0.5) + 15)]
splines.append((handle, [0.3] * len(handle)))
bm = bmesh.new()
BX = BD.orthogonal().normalized()
lathe(bm, D.frame(foot_b + BD * ((q - foot_b).length + 6.4), BX, BD.cross(BX), BD),
      [(0, -0.2), (0.42, -0.2), (0.5, 0.2), (0.5, 0.75), (0.62, 0.9), (1.0, 2.0), (1.45, 3.7), (1.55, 4.4), (1.1, 4.8),
       (0, 4.9)], [1, 1, 1, 3, 3, 3, 3, 3, 3], seg=36,
      warp=lambda p: p + Vector((p.x, p.y, 0)) * 0.12 * math.sin(9 * math.atan2(p.y, p.x)) * max(0.0, p.z / 4.9))
broom = shell('Broom', bm)

cu =bpy.data.curves.new('ArmCurve', 'CURVE')  # as D.trunk_mesh, with finer voxels for the slim twigs
cu.dimensions, cu.bevel_depth, cu.bevel_resolution, cu.use_fill_caps = '3D', 1.0, 4, True
for pts, rad in splines:
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for p, co, r in zip(sp.points, pts, rad):
        p.co, p.radius = (co.x, co.y, co.z, 1.0), r
cob = bpy.data.objects.new('ArmCurve', cu)
bpy.context.scene.collection.objects.link(cob)
arms = D.link('Arms', bpy.data.meshes.new_from_object(cob.evaluated_get(bpy.context.evaluated_depsgraph_get())))
bpy.data.objects.remove(cob)
D.voxel_union(arms, 0.07)
D.smooth_decimate(arms, 3, 9000 / D.tris(arms.data))
for p in arms.data.polygons:
    p.material_index = 2

bm = bmesh.new()
for ob in (hat, broom, arms):
    bm.from_mesh(ob.data)
    bpy.data.objects.remove(ob)
me = bpy.data.meshes.new('Trunk')
bm.to_mesh(me)
bm.free()
trunk = D.link('Trunk', me)
trunk.data.transform(PLACE)
for n, h in (('Hat', '2a2b31'), ('HatBand', 'c4313a'), ('Twig', '5b3f2c'), ('Straw', 'c9a24f')):  # first: the trunk slot colour
    trunk.data.materials.append(D.material(n, h))
trunk.data.shade_smooth()
trunk.data.set_sharp_from_angle(angle=math.radians(50))




# ---------- the clearing: firs round the back, a snow fort, a swept rink, a log pile, the sledge and trails ----------
RINK, RINK_ROT, RX, RY = Vector((15.0, -13.0, 0.0)), Matrix.Rotation(math.radians(-20), 3, Z), 10.0, 6.5
RINK_GATE = math.radians(158)  # the gap in the banks, toward the snowman
FORT, FORT_AZ, FORT_R = Vector((-21.0, -15.0, 0.0)), math.radians(56), 6.2  # the wall's outside faces the snowman
LOGS, LOG_DIR = Vector((10.0, 22.0, 0.0)), horiz(math.radians(-30))  # end grain toward the camera
SLEDGE, SLEDGE_DIR = Vector((-2.0, -16.0, 0.0)), horiz(math.radians(-104))
FIRS = [((-29, 16), 13.4), ((-22, 29), 12.0), ((-12, 31), 9.5), ((-31, 3), 8.0), ((4, 30.5), 11.5), ((14, 30), 8.0),
        ((31, 18), 10.5), ((-31, -20), 7.0), ((31, -4), 7.5), ((28, -10), 5.5)]  # (x, y), height: <= 14 with snow
ANGEL, ANGEL_UP = Vector((-13.0, -28.0, 0.0)), horiz(math.radians(132))  # a snow angel, head away from the camera


def rink_pt(a, s=1.0, z=0.0):  # the rink's wobbly elliptic outline at local angle a
    w = s * (1 + 0.06 * math.sin(3 * a + 0.5) + 0.04 * math.sin(5 * a + 1.3))
    return RINK + RINK_ROT @ Vector((RX * w * math.cos(a), RY * w * math.sin(a), 0)) + Z * z


FOOT = D.TREE
TRAILS = [  # footprint trails as bezier controls: into the fort, round its wall to the snowman, on to the rink
    [Vector(p) for p in ((-35, -10, 0), (-30, -12, 0), (-26, -17, 0), (-22.5, -17, 0))],
    [Vector((-19, -17, 0)), Vector((-13, -21, 0)), Vector((-6, -12, 0)), FOOT + F * 9.5 + S * 1.0],
    [FOOT + F * 9.5 - S * 1.5, Vector((6, 0, 0)), Vector((7, -4, 0)), rink_pt(RINK_GATE, 1.05)],
]
TRACK = [Vector(p) for p in ((8, 15, 0), (11, 4, 0), (4, -6, 0))] + [SLEDGE - SLEDGE_DIR * 3.75]  # from the logs
BROOM_FOOT = PLACE @ foot_b

# the shared scatter keeps grass, mounds and flowers off the garden's set pieces only; this adds the clearing's.
# shortcut: patches D.open_ground at runtime (diorama.py is shared); move into finish() if another scene needs it
KEEP_OUT = ([(FORT, 8.5), (LOGS, 6.0), (SLEDGE, 5.0), (BROOM_FOOT, 1.5), (ANGEL, 4.5)]
            + [(Vector((x, y, 0)), 0.36 * h + 1.0) for (x, y), h in FIRS]
            + [(D.bez(*c, k / 12), 1.6) for c in TRAILS + [TRACK] for k in range(13)])
_open_ground = D.open_ground


def open_ground(p, pad):
    d = RINK_ROT.inverted() @ (p - RINK)
    return (_open_ground(p, pad) and (d.x / (RX * 1.3 + pad)) ** 2 + (d.y / (RY * 1.4 + pad)) ** 2 > 1
            and all(D.flat(p - c).length > r + pad for c, r in KEEP_OUT))


D.open_ground = open_ground


def lumpy_lathe(bm, P, prof, mi, seg, wob, ph, yaw):  # a lathe whose outer rings wobble (rim lumps)
    X = horiz(yaw)
    rmax = max(r for r, _ in prof)

    def warp(p):
        r = p.xy.length
        if r > 0.6 * rmax:
            a = math.atan2(p.y, p.x)
            k = math.sin(7 * a + ph) * (r - 0.6 * rmax) / (0.4 * rmax)
            p.x, p.y, p.z = p.x * (1 + wob * k), p.y * (1 + wob * k), p.z - 0.25 * max(0.0, k)
        return p
    lathe(bm, D.frame(P, X, Z.cross(X), Z), prof, [mi] * (len(prof) - 1), seg=seg, warp=warp)


def fir(bm, P, h):  # chunky stacked tiers, each with a snow blanket whose lumpy lip leaves the green rim showing
    n = 4 if h > 10 else 3
    D.rod(bm, 2, P - Z * 0.05, P + Z * h * 0.35, 0.07 * h, 0.05 * h, seg=8)
    for i in range(n):
        zb = h * (0.1 + 0.62 * i / n)
        zt = h if i == n - 1 else zb + (h - zb) * 0.55
        R, Ht = h * 0.36 * (1 - 0.72 * i / n), zt - zb

        def zg(r):  # the green's upper surface, roughly
            return zb + 0.07 * Ht + (1 - r / R) * 0.93 * Ht
        ph, yaw = rng.uniform(0, 6.3), rng.uniform(0, 6.3)
        lumpy_lathe(bm, P, [(0, zb + 0.2 * Ht), (0.88 * R, zb), (R, zb + 0.07 * Ht), (0.6 * R, zb + 0.42 * Ht),
                            (0.25 * R, zb + 0.78 * Ht), (0, zt)], 0, 28, 0.05, ph, yaw)
        lumpy_lathe(bm, P, [(0, zg(0) - 0.6 * Ht), (0.76 * R, zg(0.76 * R) - 0.15), (0.84 * R, zg(0.84 * R) + 0.15),
                            (0.5 * R, zg(0.5 * R) + 0.32), (0.2 * R, zg(0.2 * R) + 0.32), (0, zt + 0.3)], 1, 28, 0.1,
                    ph + 1.0, yaw)


def block(bm, mi, matrix):  # a rounded snow block, bevelled on its own: one bevel over many blocks orders its output
    tmp, me = bmesh.new(), bpy.data.meshes.new('block')  # by memory address, so the GLB would differ run to run
    D.prim(tmp, 'cube', mi, matrix, size=1.0)
    bmesh.ops.bevel(tmp, geom=list(tmp.edges), offset=0.22, segments=2, profile=0.5, affect='EDGES')
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def blocks(bm):  # the half-built fort wall: courses of snow blocks on an arc, fewer towards the ends, two dropped ones
    for c, span in enumerate((75, 55, 34, 14)):
        step = 2.4 / FORT_R
        k0 = 0.5 * (c % 2)
        for k in range(-8, 9):
            th = (k + k0) * step
            if abs(th) > math.radians(span):
                continue
            a = FORT_AZ + th + rng.uniform(-0.03, 0.03)
            ctr = FORT + horiz(a) * (FORT_R + rng.uniform(-0.08, 0.08)) + Z * (0.55 + 1.1 * c)
            x = horiz(a + math.pi / 2 + rng.uniform(-0.06, 0.06))
            block(bm, (k + c) % 2, D.frame(ctr, x * 2.3, Z.cross(x) * 1.35, Z * 1.1))
    for a, off, yaw in ((FORT_AZ - math.radians(98), 7.6, 0.4), (FORT_AZ + math.radians(95), 8.0, -0.7)):
        x = horiz(a + yaw)
        block(bm, 1, D.frame(FORT + horiz(a) * off + Z * 0.55, x * 2.3, Z.cross(x) * 1.35, Z * 1.1))


def extras():
    snow_mat = D.material('GroundSnow', 'f4f7fb')

    # snow caps on the boulders (winter.py's): a copy of each, tops pushed out, sides and bottom tucked in
    bm = bmesh.new()
    bm.from_mesh(bpy.data.objects['Rocks'].data)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * (0.45 * max(0.0, v.normal.z) ** 1.5 - 0.12)
    for f in bm.faces:
        f.material_index = 0
    D.prop('Snow', bm, snow_mat)

    bm = bmesh.new()
    for (x, y), h in FIRS:
        fir(bm, Vector((x, y, 0)), h)
    D.prop('Firs', bm, D.material('FirGreen', '2e5b45'), snow_mat, D.material('FirTrunk', '5a4030'), sharp=55)

    # the fort, and its ammunition: a pyramid of snowballs inside the wall
    bm = bmesh.new()
    blocks(bm)
    hx = horiz(FORT_AZ + math.pi / 2)
    base = FORT + horiz(FORT_AZ) * 3.4
    for lv, rows in enumerate(((3, 2, 1), (2, 1), (1,))):
        for j, n in enumerate(rows):
            for i in range(n):
                p = (base + hx * ((i - (n - 1) / 2) * 1.38) - horiz(FORT_AZ) * (j * 1.2 + lv * 0.4)
                     + Z * (0.68 + lv * 1.12))
                D.blob(bm, 2, p, 0.68, sub=2, rough=0.06)
    for a, d in ((FORT_AZ + 2.4, 2.2), (FORT_AZ - 2.1, 3.4)):
        D.blob(bm, 2, FORT + horiz(a) * d + Z * 0.62, 0.68, sub=2, rough=0.06)
    D.prop('Fort', bm, D.material('SnowBlock', 'edf2f8'), D.material('SnowBlockShade', 'd0dcea'),
           D.material('Snowball', 'f1f5fa'), sharp=40)

    # the rink: a slab of swept ice, banks of pushed-off snow with a gap toward the snowman, skate loops
    bm, K = bmesh.new(), 72
    top = [bm.verts.new(rink_pt(2 * math.pi * k / K, 1.0, 0.06)) for k in range(K)]
    bot = [bm.verts.new(rink_pt(2 * math.pi * k / K, 1.0, -0.04)) for k in range(K)]
    ct, cb = bm.verts.new(RINK + Z * 0.06), bm.verts.new(RINK - Z * 0.04)
    for k in range(K):
        k1 = (k + 1) % K
        for vs in ((ct, top[k], top[k1]), (cb, bot[k1], bot[k]), (bot[k], bot[k1], top[k1], top[k])):
            bm.faces.new(vs)
    for k in range(34):
        a = 2 * math.pi * (k + rng.uniform(-0.3, 0.3)) / 34
        if abs((a - RINK_GATE + math.pi) % (2 * math.pi) - math.pi) < math.radians(17):
            continue
        p, t = rink_pt(a, 1.1), rink_pt(a + 0.01) - rink_pt(a - 0.01)
        r = rng.uniform(0.9, 1.4)
        D.blob(bm, 1, p, r, (1.7, 0.95, 0.55), sub=2, rough=0.12, yaw=math.atan2(t.y, t.x))
    for k in range(3):  # figure-of-eight skate loops, a hair above the ice
        ph, sx, sy = rng.uniform(0, 6.3), rng.uniform(0.45, 0.7), rng.uniform(0.4, 0.6)
        loop = [RINK + RINK_ROT @ Vector((RX * sx * math.sin(t), RY * sy * math.sin(2 * t + ph), 0.075 + 0.01 * k))
                for t in (2 * math.pi * j / 90 for j in range(90))]
        ribbon(bm, loop, [Z] * 90, 0.02, 0.11, [2] * 90, sides=6, closed=True)
    D.prop('Rink', bm, D.material('Ice', 'bcdbea', 0.15), snow_mat, D.material('SkateMark', 'f6f9fc'))

    # the log pile: a pyramid of logs, end grain and heartwood toward the camera, snow along every top
    bm, hy = bmesh.new(), Z.cross(LOG_DIR)
    for j, n in enumerate((4, 3, 2, 1)):
        for i in range(n):
            rr, half = 0.8 * rng.uniform(0.9, 1.04), 3.0 + rng.uniform(-0.3, 0.3)
            c = LOGS + hy * ((i - (n - 1) / 2) * 1.62) + Z * (0.8 + j * 1.38) + LOG_DIR * rng.uniform(-0.3, 0.3)
            D.rod(bm, 0, c - LOG_DIR * half, c + LOG_DIR * half, rr, rr, seg=12)
            for s in (-1, 1):
                e = c + LOG_DIR * s * half
                D.rod(bm, 1, e - LOG_DIR * s * 0.05, e + LOG_DIR * s * 0.04, rr * 0.9, rr * 0.9, seg=12)
                D.rod(bm, 2, e, e + LOG_DIR * s * 0.07, rr * 0.35, rr * 0.35, seg=8)
            w, t = (1.0, 0.45) if j == 3 else (rr * 0.62, rr * 0.3)
            ribbon(bm, [c + LOG_DIR * u * (half - 0.35) + Z * rr * 0.82 for u in (-1, -0.5, 0, 0.5, 1)], [hy] * 5, w, t,
                   [3] * 4)
    D.prop('LogPile', bm, D.material('Bark', '6b4a35'), D.material('LogEnd', 'd9b27c'),
           D.material('LogHeart', 'b88650'), snow_mat, sharp=50)

    # the red sledge, dropped with its rope trailing
    bm, h = bmesh.new(), SLEDGE_DIR
    hs = Z.cross(h)

    def at(x, y, z):  # sledge-local, 1.25 x the unit drawing below
        return SLEDGE + (h * x + hs * y + Z * z) * 1.25

    for y in (-1.05, 1.05):
        pts = [at(x, y, 0.2) for x in (-2.8, -1.6, -0.4, 0.8, 1.9)]
        pts += [at(2.0 + 0.75 * math.sin(a), y, 0.95 - 0.75 * math.cos(a)) for a in (math.radians(d) for d in range(30, 241, 30))]
        D.tube(bm, 0, pts, 0.2, side=hs, sides=6)
        for x in (-2.0, -0.2, 1.5):
            D.rod(bm, 0, at(x, y, 0.2), at(x, y, 1.0), 0.15, 0.15, seg=6)
        D.rod(bm, 0, at(-2.5, y, 0.98), at(1.9, y, 0.98), 0.14, 0.14, seg=6)
    D.rod(bm, 0, at(2.72, -1.2, 0.95), at(2.72, 1.2, 0.95), 0.12, 0.12, seg=6)
    for x in (-2.2, -1.6, -1.0, -0.4, 0.2, 0.8, 1.4):
        D.prim(bm, 'cube', 1, D.frame(at(x, 0, 1.15), h * 0.6, hs * 3.25, Z * 0.18), size=1.0)
    rope = [at(2.72, 0, 0.95), at(3.3, 0.15, 0.45)] + [D.bez(at(3.9, 0.3, 0.12), at(6.5, 1.8, 0.12), at(7.0, -1.5, 0.12),
                                                             at(5.6, -3.0, 0.12), k / 16) for k in range(17)]
    D.tube(bm, 2, rope, 0.14, sides=6)
    D.prop('Sledge', bm, D.material('SledgeRed', 'b3392d'), D.material('SledgePine', 'd2a26a'),
           D.material('Rope', 'cdb78a'), sharp=50)

    # trails: footprints (alternating shallow ovals) and the sledge's two runner tracks, blue-shadowed
    bm = bmesh.new()
    for c in TRAILS:
        n = int(sum((D.bez(*c, (k + 1) / 50) - D.bez(*c, k / 50)).length for k in range(50)) / 1.3)
        for k in range(n):
            t = k / (n - 1)
            tg = (D.bez(*c, min(1, t + 0.01)) - D.bez(*c, max(0, t - 0.01))).normalized()
            p = D.bez(*c, t) + Z.cross(tg) * (0.45 if k % 2 else -0.45)
            D.prim(bm, 'icosphere', 0, D.frame(p + Z * 0.02, tg * 0.75, Z.cross(tg) * 0.42, Z * 0.05), subdivisions=2,
                   radius=1.0)
    line = [D.bez(*TRACK, k / 60) for k in range(61)]
    for side in (-1, 1):
        pts = []
        for i, p in enumerate(line):
            tg = (line[min(i + 1, 60)] - line[max(i - 1, 0)]).normalized()
            pts.append(p + Z.cross(tg) * side * 1.31 + Z * 0.02)
        ribbon(bm, pts, [Z] * 61, 0.03, 0.22, [0] * 60, sides=6)
    av = Z.cross(ANGEL_UP)  # the snow angel: head, body, a fan of arm sweeps each side, a fan of leg sweeps

    def oval(c, d, ln, wd):
        D.prim(bm, 'icosphere', 1, D.frame(c + Z * 0.02, d * ln, Z.cross(d) * wd, Z * 0.06), subdivisions=2, radius=1.0)
    oval(ANGEL + ANGEL_UP * 3.0, ANGEL_UP, 0.85, 0.8)
    oval(ANGEL + ANGEL_UP * 0.8, ANGEL_UP, 1.8, 1.0)
    for side in (-1, 1):
        for k in range(7):
            phi = math.radians(15 + 15 * k)
            d = ANGEL_UP * math.cos(phi) + av * side * math.sin(phi)
            oval(ANGEL + ANGEL_UP * 1.9 + av * side * 0.6 + d * 1.7, d, 1.3, 0.55)
    for k in range(5):
        phi = math.radians(160 + 10 * k)
        d = ANGEL_UP * math.cos(phi) + av * math.sin(phi)
        oval(ANGEL - ANGEL_UP * 0.6 + d * 1.9, d, 1.6, 0.6)
    D.prop('Trails', bm, D.material('Footprint', 'c3d0e2'), D.material('AngelPrint', 'b8c7dc'))


D.finish('snowman', COLOURS, trunk, shells, blossoms, [], Vector((0, 0, 0)), pebbles=0, mounds=18, tufts=34, clumps=2,
         lotus=0, extras=extras, pond=False, bridge=False, lantern=False)
