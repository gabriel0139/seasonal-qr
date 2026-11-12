"""Build the bunny diorama: public/models/bunny.glb + public/trees/bunny.json.

Run from the repo root: Blender -b -P tools/tree-build/bunny.py (Blender 5.2, headless). Deterministic (fixed SEED).
A spring meadow on an egg-hunt morning, no tree and no garden pond: a plump sitting rabbit (the canopy shells: fur,
pink, eyes, and the painted eggs) beside a wicker basket heaped with eggs (the basket is the Trunk); round them a burrow
mound, a carrot patch, tulips, daffodils, toadstools and eggs hidden in the grass. The base, lawn scatter, slot cloud,
self-checks and export are shared with the other seasons in diorama.py.
"""
import math, os, sys
sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh, bpy
from mathutils import Vector, Matrix, Euler, noise
import diorama as D
from diorama import Z, horiz, rng

SEED = 20260404
D.init(SEED)
AZ = math.atan2(-98.0, 88.0)  # from the board centre toward the hero camera
RIGHT, AWAY = horiz(AZ + math.pi / 2), -horiz(AZ)  # screen right, and away from the camera, on the lawn


def at(l, d):  # a lawn point: l to the right on screen, d away from the camera
    return RIGHT * l + AWAY * d


D.TREE = at(-2, 6)  # the rabbit just behind the board centre, the burrow behind its shoulder, carrots in front right
COLOURS = {  # scenery material -> hex sRGB (sakura's spring garden)
    'Moss': 'a7b950', 'Stone': 'c6a9a2', 'PondBed': '4e7a68', 'StoneChunk': '9a7f79',
    'PondBank': '7f8d45', 'RimStone': 'b9a7a1', 'RimStoneLight': 'd3c3bc', 'Water': '9fd6ea',
    'FlowerCentre': 'f2c84b', 'LilyPad': '5f9b48', 'Lotus': 'f3a2c0', 'Wood': '9c6b47', 'WoodDark': '6e4932',
    'LanternGlow': 'ffe2a0', 'LanternStone': 'bdb0a8', 'RockGrey': 'a39b98', 'RockPink': 'bba7a1',
    'GrassDark': '7f9c3c', 'GrassLight': 'b8cc5c', 'MossDark': '9db14a', 'MossLight': 'b0c156',
    'FlowerWhite': 'faf7f0', 'FlowerLavender': 'b7a2e4', 'Stem': '6c9a3a',
}
# canopy shells, deep to pale: the slot palette takes the first (deep), second (mid) and last (pale); accents between
SHELLS = [('Fur_Fawn', 'd3a47c', 0.8), ('Fur_Cream', 'f3dfbf', 0.8), ('Pink', 'f4a9bb', 0.6), ('Eye', '2b1d22', 0.15),
          ('Egg_Blue', 'a9d2f0', 0.45), ('Egg_Mint', 'b5e3c0', 0.45), ('Egg_Yellow', 'fbe08f', 0.45),
          ('Egg_Lilac', 'cdb8ef', 0.45), ('Fur_White', 'fdf9f2', 0.8)]
FAWN, CREAM, PINK, EYE, BLUE, MINT, YELLOW, LILAC, WHITE = range(len(SHELLS))
MATS = [D.material(n, h, r) for n, h, r in SHELLS]
bms = [bmesh.new() for _ in SHELLS]
Y = Vector((0, 1, 0))
GROW = 1.3  # modelled 23.5 tall, shown at 30 to hold the board like the trees do

# ---------- layout: a scene frame round the footprint centre (the root), +y toward the default camera ----------
cam = Vector((88.0, -98.0)) - D.TREE.xy
ROT = Matrix.Rotation(math.atan2(cam.y, cam.x) - math.pi / 2, 4, 'Z')  # scene frame -> tree-local
RAB = Vector((3.6, -0.4, 0.0))  # rabbit's seat; +x is screen left
BASKET, R0, R1, H = Vector((-5.0, 1.5, 0.0)), 3.0, 3.7, 4.6  # basket centre, bottom / rim radius, wall height
NECK, PITCH = Vector((0, 0.5, 10.5)), math.radians(12)  # head tips up a touch toward the high camera
MB = ROT @ Matrix.Translation(RAB)  # rabbit body space -> tree-local
MH = MB @ Matrix.Translation(NECK) @ Matrix.Rotation(PITCH, 4, 'X') @ Matrix.Translation(-NECK)  # head space


def ell(bm, mi, L, shape=None, sub=4):  # unit icosphere, optionally reshaped, through matrix L
    vs = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)['verts']
    for v in vs:
        v.co = L @ (shape(v.co) if shape else v.co)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mi


def part(sh, M, c, r, rot=None):  # an ellipsoid of shell sh: centre c, radii r in space M
    ell(bms[sh], 0, M @ Matrix.LocRotScale(Vector(c), rot, Vector(r)),
        sub=5 if max(r) > 2.5 else 4 if max(r) > 0.9 else 3)


def loft(bm, rings, M):  # closed tube through (centre, side, front) elliptical rings, like D.tube's winding
    K = 16
    vs = [[bm.verts.new(M @ (c + a * math.cos(2 * math.pi * k / K) + b * math.sin(2 * math.pi * k / K)))
           for k in range(K)] for c, a, b in rings]
    for r0, r1 in zip(vs, vs[1:]):
        for k in range(K):
            bm.faces.new((r0[k], r0[(k + 1) % K], r1[(k + 1) % K], r1[k]))
    bm.faces.new(vs[0][::-1])
    bm.faces.new(vs[-1])


def smooth01(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ---------- the rabbit: ellipsoid fur masses, lofted ears; each colour one shell ----------
part(FAWN, MB, (0, -0.6, 4.7), (4.7, 4.7, 5.0))  # pear body
part(FAWN, MB, (0, 0.3, 8.7), (3.9, 3.5, 3.4))  # shoulders
part(CREAM, MB, (0, 1.3, 4.9), (3.4, 3.2, 4.1))  # tummy
part(CREAM, MB, (0, 2.2, 8.8), (2.7, 1.9, 2.3))  # chest bib
for s in (-1, 1):
    part(FAWN, MB, (s * 3.0, -1.2, 3.0), (2.0, 3.6, 3.0))  # haunch
    splay = Matrix.Rotation(-s * 0.12, 3, 'Z')
    foot = Vector((s * 2.9, 2.2, 0.85))
    part(FAWN, MB, foot, (1.45, 3.2, 1.0), splay)  # big hind foot, toes turned out a little
    part(CREAM, MB, foot + splay @ Vector((0, 2.0, -0.08)), (1.2, 1.45, 0.86), splay)  # its pale toes
    for k in range(5):  # short forearm from the shoulder; the paws are held up over the tummy
        part(FAWN, MB, Vector((s * 2.3, 2.4, 8.4)).lerp(Vector((s * 1.45, 4.3, 6.9)), k / 4), (0.85, 0.85, 0.85))
    part(CREAM, MB, (s * 1.35, 4.65, 6.6), (0.85, 0.75, 0.9))  # front paw
part(WHITE, MB, (0, -5.4, 3.0), (1.5, 1.3, 1.4))  # tail, with fluff
for _ in range(7):
    part(WHITE, MB, Vector((0, -5.6, 3.0)) + D.rand_dir(0) * 1.1, (0.65, 0.65, 0.65))

HEAD_C, HEAD_R = Vector((0, 1.0, 13.6)), Vector((4.5, 3.9, 3.9))
part(FAWN, MH, HEAD_C, HEAD_R)
part(WHITE, MH, (0, 3.85, 11.6), (0.8, 0.75, 0.55))  # chin, tucked under the muzzle
part(PINK, MH, (0, 5.2, 13.25), (0.6, 0.42, 0.45))  # nose
for s in (-1, 1):
    CHEEK_C, CHEEK_R = Vector((s * 2.3, 3.0, 12.2)), Vector((2.3, 2.0, 1.9))
    part(FAWN, MH, CHEEK_C, CHEEK_R)  # chubby cheek
    d = Vector((s * 0.55, 0.75, 0.35))  # blush: a pink disc on the cheek
    q = CHEEK_C + d / math.sqrt(sum((d[i] / CHEEK_R[i]) ** 2 for i in range(3)))
    n = Vector([(q - CHEEK_C)[i] / CHEEK_R[i] ** 2 for i in range(3)]).normalized()
    ux = Z.cross(n).normalized()
    ell(bms[PINK], 0, MH @ D.frame(q - n * 0.2, ux * 0.75, n.cross(ux) * 0.55, n * 0.28))
    part(WHITE, MH, (s * 0.85, 4.45, 12.35), (1.15, 0.95, 0.95))  # muzzle puff
    q = Vector((s * 1.9, 0, 14.3))  # eye: a glossy bead set into the head's surface, a white catchlight on it
    q.y = HEAD_C.y + HEAD_R.y * math.sqrt(1 - ((q.x - HEAD_C.x) / HEAD_R.x) ** 2 - ((q.z - HEAD_C.z) / HEAD_R.z) ** 2)
    n = Vector([(q - HEAD_C)[i] / HEAD_R[i] ** 2 for i in range(3)]).normalized()
    ux = Z.cross(n).normalized()
    uy = n.cross(ux)
    c = q - n * 0.15
    ell(bms[EYE], 0, MH @ D.frame(c, ux * 0.75, uy * 0.95, n * 0.5))
    side = Vector((1, 0, 0)) - n * n.x
    ell(bms[WHITE], 0, MH @ Matrix.Translation(c + n * 0.4 + uy * 0.38 + side.normalized() * 0.2) @ Matrix.Scale(0.21, 4),
        sub=3)
    # ear: a flat lofted blade (pink pad on its front) rising from the crown; the screen-left one flops outward
    p, d0, pts = Vector((s * 1.6, 0.4, 16.2)), Vector((s * 0.2, 0.1, 1.0)).normalized(), []
    for k in range(29):
        t = k / 28
        a = s * (math.radians(115) * smooth01((t - 0.42) / 0.3) if s > 0 else math.radians(10) * t)
        pts.append((t, p.copy()))
        p += Matrix.Rotation(a, 3, 'Y') @ d0 * (7.8 / 28)
    fur, pad = [], []
    for k, (t, c) in enumerate(pts):
        T = (pts[min(k + 1, 28)][1] - pts[max(k - 1, 0)][1]).normalized()
        F = (Y - T * T.dot(Y)).normalized()
        S = F.cross(T)
        hw = max(0.3, 1.35 * math.sqrt(max(0.0, math.sin(math.pi * (0.12 + 0.88 * t)))))
        ht = 0.55 * (0.55 + 0.45 * hw / 1.35)
        fur.append((c, S * hw, F * ht))
        if 0.1 <= t <= 0.86:
            pw = max(0.05, 0.62 * hw * math.sin(math.pi * (t - 0.1) / 0.76) ** 0.5)
            pad.append((c + F * (ht - 0.12), S * pw, F * 0.24 * min(1.0, pw / 0.4 + 0.2)))
    loft(bms[FAWN], fur, MH)
    loft(bms[PINK], pad, MH)


# ---------- painted eggs: egg-shaped ellipsoids, banded or dotted in a second colour ----------
DECO = {BLUE: ('bands', WHITE), PINK: ('dots', WHITE), YELLOW: ('bands', PINK), MINT: ('dots', YELLOW),
        LILAC: ('bands', YELLOW)}
EGG = Vector((0.8, 0.8, 1.15))


def egg_shape(q):  # unit sphere -> egg: narrower toward +z
    return Vector((q.x * (1 - 0.15 * q.z), q.y * (1 - 0.15 * q.z), q.z))


def egg(put, M, col, sub=4):  # put(colour) -> (bmesh, material index); M: unit sphere -> the egg
    ell(*put(col), M, egg_shape, sub)
    kind, dc = DECO[col]
    if kind == 'bands':  # the egg grown 12%, squashed into a slab: a closed ring standing proud of the shell
        for z0 in (-0.32, 0.3):
            ell(*put(dc), M, lambda q, z0=z0: (lambda e: Vector((e.x * 1.12, e.y * 1.12,
                                                                  max(z0 - 0.14, min(z0 + 0.14, e.z)))))(egg_shape(q)),
                sub)
    else:
        r, Mn = M.to_scale().x * 0.3, M.to_3x3().inverted().transposed()
        for _ in range(8):  # flat discs lying on the shell
            u = D.rand_dir(0)
            u.z *= 0.85
            u.normalize()
            n = (Mn @ u).normalized()
            ux = n.orthogonal().normalized()
            ell(*put(dc), D.frame(M @ egg_shape(u) - n * r * 0.12, ux * r, n.cross(ux) * r, n * r * 0.36), sub=2)


HEAP = [(2.15, 5.1, 6, 0.35), (0.9, 6.4, 3, 0.7), (0.0, 7.5, 1, 1.0)]  # ring radius, height, count, uprightness
cols = [BLUE, PINK, YELLOW, MINT, LILAC]
i = 0
for rad, z, count, up in HEAP:
    a0 = rng.uniform(0, 2 * math.pi)
    for k in range(count):
        a = a0 + 2 * math.pi * k / count + rng.uniform(-0.15, 0.15)
        axis = horiz(a + math.pi / 2) * (1 - up) + horiz(a) * 0.25 + Z * up + D.rand_dir(0) * 0.2
        c = BASKET + horiz(a) * rad + Z * z
        egg(lambda col: (bms[col], 0), ROT @ Matrix.LocRotScale(c, Z.rotation_difference(axis), EGG * 1.15),
            cols[i % len(cols)])
        i += 1

shells, reach = [], 0.0
for i, bm in enumerate(bms):
    for v in bm.verts:  # flat bottom where the rabbit sits
        v.co.z = max(v.co.z, -0.25)
    me = bpy.data.meshes.new('shell')
    bm.to_mesh(me)
    bm.free()
    shells.append(D.link(f'BunnyShell{i}', me))
    D.voxel_union(shells[-1], 0.12 if i in (FAWN, CREAM) else 0.07)
    reach = max([reach] + [v.co.xy.length for v in shells[-1].data.vertices if v.co.z < 3])
for ob in shells:
    ob.data.transform(Matrix.Scale(GROW, 4))
blossoms = D.canopy_mesh(shells, MATS, 62000)


# ---------- the basket (Trunk): a woven frustum, braided rim, foot ring and a twisted arched handle ----------
def tube_line(bm, line, r, side, twist, strands=2, closed=False, lay=0.2):  # strands twisted round a centre line
    n = len(line)
    for j in range(strands):
        pts = []
        for k, c in enumerate(line):
            t = (line[(k + 1) % n if closed else min(k + 1, n - 1)] - line[(k - 1) % n if closed else max(k - 1, 0)])
            t.normalize()
            a = (side - t * side.dot(t)).normalized()
            phi = twist * k / n + 2 * math.pi * j / strands
            pts.append(c + (a * math.cos(phi) + t.cross(a) * math.sin(phi)) * lay)
        D.tube(bm, 0, pts, r, side=side, sides=8, closed=closed)


bm = bmesh.new()
D.prim(bm, 'cone', 0, Matrix.Translation(BASKET + Z * H / 2), segments=64, radius1=R0, radius2=R1, depth=H,
       cap_ends=True)
tube_line(bm, [BASKET + horiz(2 * math.pi * k / 160) * (R1 + 0.05) + Z * (H + 0.15) for k in range(160)], 0.27, Z,
          2 * math.pi * 22, closed=True)
D.tube(bm, 0, [BASKET + horiz(2 * math.pi * k / 96) * (R0 + 0.05) + Z * 0.3 for k in range(96)], 0.34, sides=8,
       closed=True)
A = horiz(math.radians(15))
tube_line(bm, [BASKET - A * (R1 - 0.1) * math.cos(math.pi * u) + Z * (H + 0.1 + 5.0 * math.sin(math.pi * u))
               for u in [-0.04 + 1.08 * k / 90 for k in range(91)]], 0.27, A.cross(Z), 2 * math.pi * 7)
bmesh.ops.transform(bm, matrix=ROT, verts=bm.verts)
me = bpy.data.meshes.new('Trunk')
bm.to_mesh(me)
bm.free()
trunk = D.link('Trunk', me)
D.voxel_union(trunk, 0.09)
D.smooth_decimate(trunk, 2, 1.0)
Cw = ROT @ BASKET
for v in trunk.data.vertices:  # weave: rows of weavers passing over and under 28 stakes
    d = (v.co - Cw).xy
    if 0.7 < v.co.z < 4.2 and abs(v.normal.z) < 0.6 and abs(d.length - (R0 + (R1 - R0) * v.co.z / H)) < 0.3:
        row = (v.co.z - 0.7) / 0.5
        over = math.cos(28 * math.atan2(d.y, d.x) + math.pi * math.floor(row))
        v.co += d.normalized().to_3d() * 0.14 * math.sin(math.pi * (row % 1)) ** 0.6 * (0.6 + 0.4 * over)
reach = max([reach] + [v.co.xy.length for v in trunk.data.vertices if v.co.z < 3])
D.smooth_decimate(trunk, 0, 18000 / D.tris(trunk.data))
trunk.data.transform(Matrix.Translation(D.TREE) @ Matrix.Scale(GROW, 4))
trunk.data.materials.append(D.material('Wicker', 'b07b45'))
print('BUNNY footprint radius below z = 3:', round(reach, 2))
assert reach < 9.4, reach  # modelled inside the 8.5 the lawn's scenery keeps from the root; prune() clears what GROW then reaches


# ---------- the meadow (extras): burrow, carrot patch, bulbs, toadstools; then the lawn scatter is cleared round them ----------
MEADOW = {n: D.material(n, h, r) for n, h, r in (
    ('Turf', '9db74c', 0.9), ('Burrow', '2b1e17', 1.0), ('Soil', '8d5f3d', 0.95), ('SoilDark', '6e482e', 0.95),
    ('PathStone', 'cbbfb3', 0.8), ('Carrot', 'f28a3a', 0.6), ('CarrotTop', '5aa63b', 0.7), ('Leaf', '5f9f3f', 0.7),
    ('Tulip_Pink', 'f59ab3', 0.5), ('Tulip_Coral', 'f5806f', 0.5), ('Tulip_Lilac', 'c5a4ee', 0.5),
    ('Tulip_Cream', 'fff0d4', 0.5), ('Daffodil', 'fff09b', 0.5), ('Trumpet', 'f6b13a', 0.5),
    ('Toadstool', 'e65a4f', 0.45), ('ToadstoolStem', 'f4e8d2', 0.7))}


def meadow_prop(name, bm, names):  # every vertex on or above the lawn: the lawn slots below z = -0.6 keep 0.5 clear
    for v in bm.verts:
        v.co.z = max(v.co.z, -0.08)
    return D.prop(name, bm, *[MEADOW.get(n) or bpy.data.materials[n] for n in names])


def spindle(bm, mi, a, b, w, t, sub=2):  # ellipsoid spanning a -> b, w wide (level), t thick: leaves, petals, fronds
    z = (b - a) / 2
    x = z.cross(Z)
    x = (x if x.length > 1e-6 else z.orthogonal()).normalized()
    ell(bm, mi, D.frame((a + b) / 2, x * w / 2, z.normalized().cross(x) * t / 2, z), sub=sub)


def scatter(c, rad, count, gap):  # count points within rad of c, at least gap apart
    pts = []
    while len(pts) < count:
        p = c + horiz(rng.uniform(0, 2 * math.pi)) * rad * math.sqrt(rng.random())
        if all((p - q).length > gap for q in pts):
            pts.append(p)
    return pts


Mb = D.frame(at(-22, 8), RIGHT * 7.0, AWAY * 6.0, Z * 4.6)  # the burrow mound: unit sphere -> mound
Mn = Mb.to_3x3().inverted().transposed()


def surf(u):  # the lumpy mound surface along direction u (unit-sphere space): point, normal
    u = u.normalized()
    return Mb @ (u * (1 + 0.06 * noise.noise(u * 2.0 + Vector((3.1, 0, 0))))), (Mn @ u).normalized()


def burrow():  # a grassy mound, its round dark doorway to the camera under a soil lip, stepping stones, tufts on top
    bm = bmesh.new()  # 0 turf, 1 doorway, 2 soil, 3 stone, 4 grass
    for v in bmesh.ops.create_icosphere(bm, subdivisions=5, radius=1.0)['verts']:
        v.co = surf(v.co)[0]
    q, n = surf(Vector((0, -1, 0.35)))
    side = Z.cross(n).normalized()
    up = n.cross(side)
    ell(bm, 1, D.frame(q - n * 0.5, side * 1.75, up * 2.05, n * 0.72), sub=3)
    arch = []
    for k in range(25):
        phi = -0.7 + (math.pi + 1.4) * k / 24
        s, ns = surf(Mb.inverted() @ (q + side * 2.0 * math.cos(phi) + up * 2.3 * math.sin(phi)))
        arch.append(s + ns * 0.1)
    D.tube(bm, 2, arch, 0.42, side=n, sides=8)
    nh = n.copy()
    nh.z = 0
    foot = Vector((q.x, q.y, 0)) + nh.normalized() * 0.6
    for k in range(3):
        D.blob(bm, 3, foot + nh.normalized() * (1.3 + 1.6 * k) + side * rng.uniform(-0.5, 0.5) + Z * 0.04, 0.7,
               (1.2, 0.95, 0.22), sub=2, yaw=rng.uniform(0, 6.3))
    for _ in range(7):
        u = D.rand_dir(0)
        u.z = abs(u.z) * 0.6 + 0.35
        p, pn = surf(u)
        for _ in range(7):
            phi, h = rng.uniform(0, 2 * math.pi), rng.uniform(0.9, 1.7)
            b = p + horiz(phi) * rng.uniform(0, 0.4) - pn * 0.15
            D.rod(bm, 4, b, b + (pn * 0.7 + Z * 0.5 + horiz(phi) * rng.uniform(0.2, 0.6)).normalized() * h, 0.2, 0.0,
                  seg=3)
    return meadow_prop('Burrow', bm, ['Turf', 'Burrow', 'Soil', 'PathStone', 'GrassLight'])


def carrot_top(bm, mi, p, axis, count):  # feathery fronds: a stalk with leaflet pairs and a tip
    a0 = rng.uniform(0, 2 * math.pi)
    e1 = axis.orthogonal().normalized()
    e2 = axis.cross(e1)
    for k in range(count):
        th = a0 + 2 * math.pi * k / count + rng.uniform(-0.3, 0.3)
        d = (axis + (e1 * math.cos(th) + e2 * math.sin(th)) * rng.uniform(0.35, 0.7)).normalized()
        L = rng.uniform(1.8, 2.5)
        D.rod(bm, mi, p, p + d * L, 0.07, 0.05, seg=4)
        w = d.cross(Z).normalized() if abs(d.z) < 0.99 else e1
        for t, s in ((0.5, 1), (0.5, -1), (0.78, 1), (0.78, -1)):
            b = p + d * L * t
            spindle(bm, mi, b, b + (d * 0.5 + w * s).normalized() * 0.75, 0.42, 0.12, sub=1)
        spindle(bm, mi, p + d * (L - 0.1), p + d * (L + 0.75), 0.48, 0.14)


def carrot_patch():  # a raised soil bed lying on the lawn, three ridged rows of carrots, one carrot half pulled
    bm = bmesh.new()  # 0 soil, 1 ridge soil, 2 carrot, 3 tops
    c = at(18, -9)
    vs = bmesh.ops.create_cube(bm, size=1.0)['verts']
    for v in vs:
        v.co = D.frame(c + Z * 0.17, RIGHT * 15.0, AWAY * 8.6, Z * 0.5) @ v.co
    bmesh.ops.bevel(bm, geom=list({e for v in vs for e in v.link_edges}), offset=0.3, segments=3, profile=0.5,
                    affect='EDGES')
    for row, v0 in enumerate((-2.6, 0.0, 2.6)):
        D.tube(bm, 1, [c + RIGHT * u + AWAY * (v0 + 0.15 * noise.noise(Vector((u * 0.4, v0, 1.7)))) + Z * 0.36
                       for u in [-6.4 + 12.8 * k / 26 for k in range(27)]], 0.45, sides=8)
        for j, u in enumerate((-5.2, -2.6, 0.0, 2.6, 5.2)):
            if (row, j) == (0, 4):
                continue  # this one is half pulled, below
            p = c + RIGHT * (u + rng.uniform(-0.3, 0.3)) + AWAY * v0 + Z * 0.7
            ell(bm, 2, Matrix.LocRotScale(p, None, (0.45, 0.45, 0.42)), sub=2)
            carrot_top(bm, 3, p + Z * 0.3, (Z + D.rand_dir(0) * 0.15).normalized(), 4)
    tip = c + RIGHT * 4.6 + AWAY * -2.6 + Z * 0.25
    axis = (RIGHT * 0.45 - AWAY * 0.4 + Z * 0.8).normalized()
    sh = tip + axis * 2.7
    D.rod(bm, 2, tip, sh, 0.08, 0.5, seg=12)
    ell(bm, 2, D.frame(sh, axis.orthogonal().normalized() * 0.5, axis.cross(axis.orthogonal().normalized()) * 0.5,
                       axis * 0.28), sub=3)
    for k in range(5):  # clods heaved up round the hole
        D.blob(bm, 0, tip + Z * 0.35 + horiz(k * 1.257 + 0.3) * 0.75, 0.32, (1, 1, 0.7), sub=2, rough=0.2)
    carrot_top(bm, 3, sh + axis * 0.2, axis, 5)
    return meadow_prop('CarrotPatch', bm, ['Soil', 'SoilDark', 'Carrot', 'CarrotTop'])


TULIPS, LEAF, DAFF, TRUMPET = ['Tulip_Pink', 'Tulip_Coral', 'Tulip_Lilac', 'Tulip_Cream'], 4, 5, 6


def leaves(bm, c, h, count, w):  # strap leaves splaying from the foot
    a0 = rng.uniform(0, 2 * math.pi)
    for k in range(count):
        phi = a0 + 2 * math.pi * k / count + rng.uniform(-0.4, 0.4)
        spindle(bm, LEAF, c - Z * 0.1, c + horiz(phi) * h * 0.35 + Z * h * rng.uniform(0.45, 0.6), w, 0.16)


def tulip(bm, c, col):  # stem, two leaves, a chunky cup of three outer and three inner petals
    h = rng.uniform(2.8, 4.0)
    top = c + Z * h + horiz(rng.uniform(0, 2 * math.pi)) * rng.uniform(0, 0.4)
    D.rod(bm, LEAF, c - Z * 0.1, top, 0.13, 0.11, seg=6)
    leaves(bm, c, h, 2, 0.62)
    a0 = rng.uniform(0, 2 * math.pi)
    for ring, (rr, zz, s) in enumerate(((0.3, 0.75, 1.0), (0.18, 0.9, 0.9))):
        for k in range(3):
            d = horiz(a0 + 2 * math.pi * k / 3 + ring * math.pi / 3)
            x = d.cross(Z).normalized() * 0.5 * s
            zax = (Z + d * 0.2).normalized()
            ell(bm, col, D.frame(top + d * rr + Z * zz, x, zax.cross(x.normalized()) * 0.27 * s, zax * 0.8 * s), sub=2)


def daffodil(bm, c):  # stem, narrow leaves, six pale petals round a golden trumpet, facing the camera
    h = rng.uniform(2.4, 3.4)
    top = c + Z * h
    D.rod(bm, LEAF, c - Z * 0.1, top, 0.11, 0.1, seg=6)
    leaves(bm, c, h * 1.1, 2, 0.42)
    f = (-AWAY * 0.7 + Z * 0.55 + D.rand_dir(0) * 0.35).normalized()
    fc = top + f * 0.2
    e1 = f.orthogonal().normalized()
    e2 = f.cross(e1)
    a0 = rng.uniform(0, 2 * math.pi)
    for k in range(6):
        d = e1 * math.cos(a0 + k * math.pi / 3) + e2 * math.sin(a0 + k * math.pi / 3)
        ell(bm, DAFF, D.frame(fc + d * 0.55, d * 0.58, f.cross(d) * 0.34, f * 0.1), sub=2)
    D.rod(bm, TRUMPET, fc - f * 0.05, fc + f * 0.7, 0.28, 0.38, seg=10)


def bulbs():  # tulip and daffodil clumps round the board's edges, framing the rabbit
    bm = bmesh.new()
    for l, d, n, cols in ((-24, -12, 6, (0, 2)), (2, -26, 6, (1, 3)), (16, 24, 5, (0, 3)), (-14, 28, 5, (2, 1)),
                          (24, 14, 5, (2, 0)), (-16, -21, 5, (3, 0))):
        for k, p in enumerate(scatter(at(l, d), 2.4, n, 1.1)):
            tulip(bm, p, cols[k % 2])
    for l, d, n in ((-8, -21, 5), (18, -24, 6), (30, 6, 5), (-34, -2, 4)):
        for p in scatter(at(l, d), 2.2, n, 1.0):
            daffodil(bm, p)
    for a in (-0.5, 0.1, 0.6):  # on the burrow's crown
        daffodil(bm, surf(Vector((math.sin(a), 0.25, math.cos(a))))[0] - Z * 0.1)
    return meadow_prop('Bulbs', bm, TULIPS + ['Leaf', 'Daffodil', 'Trumpet'])


def toadstools():  # red caps with white spots, in little clusters
    bm = bmesh.new()  # 0 cap, 1 stem, 2 spots
    for l, d, n in ((-15, -6, 3), (33, -3, 2), (4, 30, 3)):
        for k, p in enumerate(scatter(at(l, d), 2.2, n, 2.6)):
            s = (1.0, 0.75, 0.6)[k] * rng.uniform(0.9, 1.1)
            h, R = 2.2 * s, 1.5 * s
            tilt = Euler((rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15), 0)).to_matrix()
            ell(bm, 1, Matrix.LocRotScale(p + Z * h * 0.45, tilt, (0.48 * s, 0.48 * s, h * 0.5)), sub=2)
            Mc = Matrix.LocRotScale(p + tilt @ (Z * h), tilt, (R, R, R * 0.62))
            ell(bm, 0, Mc, lambda q: Vector((q.x, q.y, max(q.z, -0.2))), sub=3)  # dome with a flat underside
            Mn = Mc.to_3x3().inverted().transposed()
            for j in range(6):  # spots: flush discs on the dome
                u = horiz(2 * math.pi * j / 6 + rng.uniform(-0.3, 0.3)) * 0.75 + Z * rng.uniform(0.45, 0.75)
                u.normalize()
                nn = (Mn @ u).normalized()
                x = nn.orthogonal().normalized()
                ell(bm, 2, D.frame(Mc @ u - nn * 0.03, x * 0.27 * R, nn.cross(x) * 0.27 * R, nn * 0.07), sub=1)
            u = Vector((0, 0, 1))
            nn = (Mn @ u).normalized()
            x = nn.orthogonal().normalized()
            ell(bm, 2, D.frame(Mc @ u - nn * 0.03, x * 0.3 * R, nn.cross(x) * 0.3 * R, nn * 0.07), sub=1)
    return meadow_prop('Toadstools', bm, ['Toadstool', 'ToadstoolStem', 'Fur_White'])


def islands_of(bm):
    islands, seen = [], set()
    for v in bm.verts:
        if v not in seen:
            isl, stack = [], [v]
            seen.add(v)
            while stack:
                u = stack.pop()
                isl.append(u)
                for e in u.link_edges:
                    w = e.other_vert(u)
                    if w not in seen:
                        seen.add(w)
                        stack.append(w)
            islands.append(isl)
    return islands


def prune(keep_out):  # drop every piece of the lawn scatter (blades, mounds, flowers, pebbles, rocks) touching ours
    out = [D.bvh_of(ob) for ob in keep_out]

    def touches(p):
        for b in out:
            co, nor, _, dist = b.find_nearest(p)
            if dist < 0.3 or dist < 2.5 and (co - p).dot(nor) > 0:  # far off, a thin part's rim edge fools the sign
                return True
        return False

    for name, grow in (('Grass', 0.0), ('Rocks', 0.0), ('Flowers', 0.8)):  # grow: a flower goes whole, not petal by petal
        bm = bmesh.new()
        bm.from_mesh(bpy.data.objects[name].data)
        islands = islands_of(bm)
        mid = [sum((u.co for u in isl), Vector()) / len(isl) for isl in islands]
        bad = {i for i, isl in enumerate(islands) if any(touches(u.co) for u in isl)}
        for _ in range(2 if grow else 0):
            bad |= {i for i, m in enumerate(mid) if any((m - mid[j]).xy.length < grow for j in bad)}
        bmesh.ops.delete(bm, geom=[u for i in bad for u in islands[i]], context='VERTS')
        # cap the blades' open bases (underground): open blades make the slot sampler's ray parity flip on rounding
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=3)
        assert not any(e.is_boundary for e in bm.edges), name
        bm.to_mesh(bpy.data.objects[name].data)
        bm.free()
        print('BUNNY pruned', len(bad), 'pieces of', name)


# lawn eggs: body colour, pattern, pattern colour; stripes and checks recolour the egg's own faces, so they sit flush
LAWN_EGGS = [(BLUE, 'stripes', WHITE), (PINK, 'dots', WHITE), (YELLOW, 'checks', LILAC), (MINT, 'stripes', PINK),
             (LILAC, 'dots', YELLOW), (BLUE, 'checks', YELLOW), (PINK, 'stripes', YELLOW), (YELLOW, 'dots', BLUE),
             (MINT, 'checks', WHITE), (LILAC, 'stripes', WHITE)]
EGG_SPOTS = [(-17, 0), (8, -13), (5, -21), (-12, -10), (-24, -18), (22, 2), (-30, 6), (-2, -36), (12, -30), (10, 30)]


def flush_egg(bm, M, col, kind, dc, order):
    # a latitude-longitude sphere built by hand (bmesh's create_uvsphere orders its faces differently run to run):
    # 11 rings 15 degrees apart, 20 segments, quads between rings and fans at the poles, wound outward
    U, rings = 20, [[bm.verts.new((math.sin(th) * math.cos(2 * math.pi * j / 20), math.sin(th) * math.sin(2 * math.pi * j / 20),
                                    math.cos(th))) for j in range(20)] for th in [math.radians(15 * i) for i in range(1, 12)]]
    top, bot = bm.verts.new((0, 0, 1)), bm.verts.new((0, 0, -1))
    faces = [(i, bm.faces.new((top, rings[0][j], rings[0][(j + 1) % U]))) for j in range(U)]
    faces += [(i + 1, bm.faces.new((r0[j], r1[j], r1[(j + 1) % U], r0[(j + 1) % U])))
              for i, (r0, r1) in enumerate(zip(rings, rings[1:])) for j in range(U)]
    faces += [(11, bm.faces.new((bot, rings[-1][(j + 1) % U], rings[-1][j]))) for j in range(U)]
    for k, (band, f) in enumerate(faces):  # band: which 15 degree latitude ring, from the top
        on = band in (4, 7) if kind == 'stripes' else kind == 'checks' and band in (5, 6) and (k + band) % 2 == 0
        f.material_index = order.index(dc if on else col)
    for v in [top, bot] + [v for r in rings for v in r]:
        v.co = M @ egg_shape(v.co)
    if kind == 'dots':  # thin discs barely proud of the shell
        Mn = M.to_3x3().inverted().transposed()
        for _ in range(9):
            u = D.rand_dir(0)
            u.z *= 0.8
            u.normalize()
            n = (Mn @ u).normalized()
            x = n.orthogonal().normalized()
            ell(bm, order.index(dc), D.frame(M @ egg_shape(u) - n * 0.02, x * 0.24, n.cross(x) * 0.24, n * 0.06), sub=1)


def meadow():
    mine = [burrow(), carrot_patch(), bulbs(), toadstools()]
    prune(shells + [trunk] + mine)
    near = [D.bvh_of(ob) for ob in shells + [trunk] + list(bpy.data.objects['Props'].children) if ob.data.polygons]
    bm, order = bmesh.new(), [BLUE, PINK, YELLOW, MINT, LILAC, WHITE]
    for (col, kind, dc), (l, d) in zip(LAWN_EGGS, EGG_SPOTS):  # tucked beside the burrow, carrots, bulbs, toadstools
        for tries in range(5000):  # the search widens until the spot is clear
            p = at(l, d) + horiz(rng.uniform(0, 2 * math.pi)) * rng.uniform(0, 2.5 + 0.02 * tries)
            p.z = 0.8
            if max(abs(p.x), abs(p.y)) < 33 and all(b.find_nearest(p)[3] > 1.45 for b in near):
                break
        else:
            raise AssertionError(('no room for an egg near', l, d))
        axis = horiz(rng.uniform(0, 2 * math.pi)) + Z * rng.uniform(0.05, 0.25)
        flush_egg(bm, Matrix.LocRotScale(p - Z * 0.05, Z.rotation_difference(axis), EGG), col, kind, dc, order)
    meadow_prop('Eggs', bm, [SHELLS[c][0] for c in order])


D.finish('bunny', COLOURS, trunk, shells, blossoms, [], Vector((0, 0, 0)), pebbles=14, clumps=6, extras=meadow,
         pond=False, bridge=False, lantern=False)
