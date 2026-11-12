"""Build the autumn diorama: public/models/autumn.glb + public/trees/autumn.json.

Run from the repo root: npm run tree:build (Blender 5.2, headless). Deterministic (fixed SEED).
This file is the season: a maple-viewing afternoon in a temple garden. A gnarled, leaning Japanese maple holds tiers of
flat foliage pads that run from deep crimson inside to gold on the sunlit tops; round it a plastered temple wall,
stepping stones that cross the pond, a red-felt bench under a red parasol, raked leaf piles with a bamboo rake, pampas
grass, a stone basin and fallen leaves. The base, pond, lantern, slot cloud, self-checks and export are shared with the
other seasons in diorama.py.
"""
import math, os, sys
sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh, bpy
from mathutils import Vector, Matrix, Euler, noise
import diorama as D
from diorama import Z, bez, lerp, horiz, wobbly, rng

SEED = 20261115
D.init(SEED)
COLOURS = {  # scenery material -> hex sRGB
    'Moss': 'b4a64e', 'Stone': 'bea58e', 'PondBed': '4b6f5c', 'StoneChunk': '8e7464',
    'PondBank': '877c42', 'RimStone': 'b3a69c', 'RimStoneLight': 'cfc3b8', 'Water': '9fd6ea',
    'FlowerCentre': 'f2c84b', 'LilyPad': '7f9443', 'Wood': '9c6b47', 'WoodDark': '6e4932',
    'LanternGlow': 'ffe2a0', 'LanternStone': 'b8ada3', 'RockGrey': '9d9690', 'RockPink': 'ad9a8c',
    'GrassDark': '9e923d', 'GrassLight': 'd0bb6a', 'MossDark': 'a69d47', 'MossLight': 'bbad55',
    'FlowerWhite': 'f7f3ea', 'FlowerLavender': '9d84d6', 'Stem': '7d8f3a',
}
# canopy, strictly dark to light: the slot palette takes the first, second and last
LEAVES = [('Crimson', '8e1c1b'), ('Red', 'b92a1f'), ('Vermilion', 'd4481f'), ('Orange', 'e5772c'), ('Gold', 'efab3c')]
FALLEN = [('Crimson', 'a8241c'), ('Red', 'cc3a22'), ('Orange', 'e0612b'), ('Amber', 'eb9a3a'), ('Brown', '9a5b2c')]

# ---------- trunk: a gnarled stem leaning right, turning upright near the top; tiers of branches carry the pads ----------
LEAN = horiz(math.radians(20))  # screen right and a little towards the camera


def axis(t):
    return bez(Vector((0, 0, -1.5)), LEAN * 4 + Z * 7.5, LEAN * 16 + Z * 18, LEAN * 15 + Z * 29, t)


def trunk_r(t):
    return lerp(3.0, 1.15, t ** 0.8)


splines, pads, tips = [], [], []  # pads: (centre, radius, thickness, yaw)
for s in range(4):  # strands twisting round the core: a fluted, muscular maple trunk
    pts, rad = [], []
    for k in range(41):
        t = k / 40
        q = axis(t) + horiz(math.pi * s / 2 + math.radians(220) * t) * trunk_r(t) * 0.72
        pts.append(q + noise.noise_vector(q * 0.3 + Vector((s * 3.7, 0, 0))) * 0.9 * math.sin(math.pi * t))
        rad.append(trunk_r(t) * (0.5 + 0.1 * noise.noise(q * 0.5)))  # strands swell and pinch
    splines.append((pts, rad))
splines.append(([axis(k / 40) for k in range(41)], [trunk_r(k / 40) * 0.62 for k in range(41)]))  # core: strands show as flutes
for t, az, size in ((0.18, 130, 2.1), (0.34, 290, 1.7), (0.5, 60, 1.5), (0.66, 230, 1.2)):  # burls
    a, d = axis(t), horiz(math.radians(az))
    splines.append(([a + d * trunk_r(t) * 0.5, a + d * (trunk_r(t) * 0.8 + size * 0.5), a + d * (trunk_r(t) * 0.8 + size)],
                    [size * 1.15, size, size * 0.6]))

for t, az, ln in ((0.26, 330, 2.6), (0.58, 140, 2.0)):  # sawn-off stubs of old limbs
    a, d = axis(t), (horiz(math.radians(az)) + Z * 0.35).normalized()
    splines.append(([a, a + d * (trunk_r(t) + ln * 0.5), a + d * (trunk_r(t) + ln)], [1.3, 1.0, 0.9]))

MAIN = [  # position on the trunk, azimuth deg, horizontal reach, tip rise, pad radius
    (0.30, 200, 18.0, 2.0, 8.0),  # the long low branch balancing the lean
    (0.38, 110, 12.5, 2.5, 6.6),
    (0.47, 0, 14.0, 2.0, 7.0),
    (0.55, 250, 13.0, 3.0, 6.6),
    (0.63, 45, 12.0, 2.5, 6.4),
    (0.70, 160, 11.5, 3.0, 6.2),
    (0.77, 300, 10.5, 2.5, 5.8),
    (0.85, 85, 9.5, 2.5, 5.6),
    (0.92, 215, 8.0, 3.0, 5.2),
]


def twigs(tip, c, R, yaw, key):  # fine branching fanning out under a pad, ending inside it
    for j in range(3):
        end = c + horiz(yaw + 2 * math.pi * j / 3 + 0.5) * R * 0.55 + Z * 0.2
        d = D.flat(end - tip).to_3d()
        pts, rad = wobbly(tip, tip + d * 0.4 - Z * 0.4, end - d * 0.3 - Z * 0.6, end, 0.5, 0.3, 0.3, key + j)
        splines.append(([tip] + pts, [0.5] + rad))


for i, (t, az_deg, reach, rise, R) in enumerate(MAIN):
    az = math.radians(az_deg)
    p0, d = axis(t), horiz(az)
    tip = p0 + d * reach + Z * rise
    pts, rad = wobbly(p0, p0 + d * reach * 0.4 - Z * 0.6, tip - d * reach * 0.25 - Z * 1.6, tip, trunk_r(t) * 0.72,
                      0.45, 1.0, i)
    splines.append(([p0] + pts, [trunk_r(t) * 0.72] + rad))
    R *= 1.08
    pads.append((tip - Z * 0.2, R, 3.2, az))
    tips.append(tip)
    twigs(tip, tip, R, az, 40 + 3 * i)
    for k, (at, off, scale, up) in enumerate(((0.5, 55, 0.62, 1.4), (0.78, -60, 0.5, 1.8))):  # side shoots
        j = int(at * (len(pts) - 1))
        q0, side = pts[j], az + math.radians(off if i % 2 else -off)
        stip = q0 + horiz(side) * R * 0.95 + Z * up
        sp, sr = wobbly(q0, q0 + horiz(side) * R * 0.4, stip - Z * 0.8, stip, rad[j] * 0.75, 0.35, 0.4, 10 + 2 * i + k)
        splines.append(([q0] + sp, [rad[j] * 0.75] + sr))
        pads.append((stip - Z * 0.2, R * scale, 3.0, side))
        tips.append(stip)
        twigs(stip, stip, R * scale, side, 80 + 4 * i + k)
    if R >= 6.4:  # a lower tier hanging off the branch end: layered clouds
        j = int(0.88 * (len(pts) - 1))
        q0 = pts[j]
        ltip = q0 + d * R * 0.55 + horiz(az + math.pi / 2) * R * 0.25 - Z * 2.6
        sp, sr = wobbly(q0, q0 + d * 1.5 - Z * 0.8, ltip - d * 1.0, ltip, rad[j] * 0.8, 0.4, 0.3, 60 + i)
        splines.append(([q0] + sp, [rad[j] * 0.8] + sr))
        pads.append((ltip - Z * 0.2, R * 0.55, 3.0, az + 0.6))
        tips.append(ltip)
for i, (t, az_deg) in enumerate(((0.48, 120), (0.62, 215), (0.74, 20), (0.86, 260))):  # inner pads in the trunk's lee
    p0, d = axis(t), horiz(math.radians(az_deg))
    itip = p0 + d * 4.0 + Z * 1.5
    sp, sr = wobbly(p0, p0 + d * 1.5, itip - Z * 0.8, itip, trunk_r(t) * 0.55, 0.4, 0.3, 70 + i)
    splines.append(([p0] + sp, [trunk_r(t) * 0.55] + sr))
    pads.append((itip - Z * 0.2, 4.2, 3.0, math.radians(az_deg)))
    tips.append(itip)
top = axis(1) - LEAN * 2.5 + Z * 6.0  # apex
sp, sr = wobbly(axis(1), axis(1) + Z * 2, top - Z * 1.5, top, trunk_r(1), 0.45, 0.4, 30)
splines.append(([axis(1)] + sp, [trunk_r(1)] + sr))
pads.append((top - Z * 0.2, 6.4, 3.4, 0.0))
tips.append(top)
twigs(top, top, 6.4, 0.0, 99)

a0 = axis(0.12)
for k in range(7):  # nebari: a wide, knotty root flare sinking into the soil
    phi = math.radians(k * 360 / 7 + 10 + rng.uniform(-12, 12))
    a = a0 + horiz(phi) * 1.0
    c = Vector((a0.x, a0.y, -1.0)) + horiz(phi) * rng.uniform(5.5, 7.2)
    pts, rad = wobbly(a, a + horiz(phi) * 1.5 - Z * 1.0, c - horiz(phi) * 2 + Z * 0.6, c, 1.7, 0.35, 0.5, 20 + k)
    splines.append(([a] + pts, [1.7] + rad))

def bark_mesh(splines, bark):  # D.trunk_mesh with lighter smoothing, so the strands' twist and burls survive
    cu = bpy.data.curves.new('TrunkCurve', 'CURVE')
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution, cu.use_fill_caps = '3D', 1.0, 4, True
    for pts, rad in splines:
        sp = cu.splines.new('POLY')
        sp.points.add(len(pts) - 1)
        for p, co, r in zip(sp.points, pts, rad):
            p.co, p.radius = (co.x, co.y, co.z, 1.0), r
    cob = bpy.data.objects.new('TrunkCurve', cu)
    bpy.context.scene.collection.objects.link(cob)
    ob = D.link('Trunk', bpy.data.meshes.new_from_object(cob.evaluated_get(bpy.context.evaluated_depsgraph_get())))
    bpy.data.objects.remove(cob)
    D.voxel_union(ob, 0.22)
    D.smooth_decimate(ob, 2, 22500 / D.tris(ob.data))  # 22.5k: the GLB stays under ~3.5 MB
    ob.data.transform(Matrix.Translation(D.TREE))
    ob.data.materials.append(D.material('Bark', bark))
    return ob


trunk = bark_mesh(splines, '4a3329')

# ---------- canopy: flat cloud pads (soft flat underside, low dome, scalloped rim), crusted with fine leaf lobes ----------
MATS = [D.material('Leaf_' + n, h) for n, h in LEAVES]
zs = [c.z for c, *_ in pads]
zmin, zmax = min(zs), max(zs)
mid = sum((D.flat(c) for c, *_ in pads), Vector((0, 0))) / len(pads)
reach = max(D.flat(c - mid.to_3d()).length for c, *_ in pads)


def pad(bm, c, R, H, yaw):
    zb = c.z - H * 0.38  # the underside plane

    def lobe(p, r, sq):
        for v in bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r,
                                            matrix=Matrix.LocRotScale(p, Euler((0, 0, yaw)), (1, 0.85, sq)))['verts']:
            if v.co.z < zb:
                v.co.z = zb - (zb - v.co.z) * 0.25
    lobe(c, R * 0.8, H * 0.5 / (R * 0.8))
    for k in range(9):  # scalloped rim
        a = yaw + 2 * math.pi * (k + rng.uniform(-0.3, 0.3)) / 9
        r = R * rng.uniform(0.32, 0.45)
        lobe(c + horiz(a) * Vector((R * 0.7, R * 0.6, 0)) + Z * rng.uniform(-0.3, 0.2), r, H * 0.42 / r)
    for _ in range(3):  # a low dome
        r = R * rng.uniform(0.3, 0.4)
        lobe(c + horiz(rng.uniform(0, 2 * math.pi)) * R * 0.3 + Z * H * 0.25, r, H * 0.45 / r)


# tone, ranked so the whole range is used: crimson low and inside, orange high and out; the crust adds sunlight on
# top, so the outer tops go gold
score = [(c.z - zmin) / (zmax - zmin) + 0.5 * D.flat(c - mid.to_3d()).length / reach + rng.uniform(-0.15, 0.15)
         for c, *_ in pads]
rank = sorted(range(len(pads)), key=score.__getitem__)
TONE = [0.0] * len(pads)
for r, i in enumerate(rank):
    TONE[i] = 0.15 + 3.6 * r / (len(pads) - 1)
bms = [bmesh.new() for _ in LEAVES]
for (c, R, H, yaw), tone in zip(pads, TONE):
    pad(bms[max(0, min(3, int(tone)))], c, R, H, yaw)


def pad_of(p):  # the pad a canopy point belongs to
    return min(range(len(pads)),
               key=lambda j: D.flat(p - pads[j][0]).length / pads[j][1] + abs(p.z - pads[j][0].z) / pads[j][2])


shells = []
for i, bm in enumerate(bms):
    me = bpy.data.meshes.new('shell')
    bm.to_mesh(me)
    bm.free()
    shells.append(D.link(f'LeafShell{i}', me))
    if me.vertices:  # no pad is gold at its core: that shell is crust only
        D.voxel_union(shells[-1], 0.3, displace=0.15)

crust = [bmesh.new() for _ in LEAVES]
for ob in shells:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    faces = [f for f in bm.faces if f.normal.z > -0.25]
    areas = [f.calc_area() for f in faces]
    for f in (rng.choices(faces, areas, k=int(2.2 * sum(areas))) if faces else []):
        p, nz = f.calc_center_median(), f.normal.z
        val = TONE[pad_of(p)] + 1.0 * max(0.0, nz) ** 2 + 0.3 * noise.noise(p * 0.2) + rng.gauss(0, 0.1)
        r = rng.uniform(0.28, 0.55)
        bmesh.ops.create_icosphere(crust[max(0, min(4, int(val)))], subdivisions=1, radius=r,
                                   matrix=Matrix.Translation(p + f.normal * r * 0.2))
    bm.free()
for ob, cb in zip(shells, crust):
    cb.from_mesh(ob.data)  # appends the shell to its crust
    cb.to_mesh(ob.data)
    cb.free()
    D.voxel_union(ob, 0.15)
assert all(ob.data.polygons for ob in shells), 'a canopy shade got no foliage'
blossoms = D.canopy_mesh(shells, MATS, 95000, smooth=1)

# ---------- the temple garden: layout first (keep_clear needs it before finish scatters the lawn) ----------
WALL = 32.5  # centre line of the plastered wall along the two back edges
BENCH, BENCH_YAW = Vector((-17.0, -15.0, 0.0)), math.radians(43)  # red-felt bench, broadside to the camera
PILES = [(Vector((-4.0, -18.0, 0.0)), 2.7), (Vector((-8.5, -22.5, 0.0)), 2.1), (Vector((-1.5, -23.5, 0.0)), 1.8)]
PAMPAS = [Vector(p) for p in ((24.0, 1.5, 0), (27.0, 19.0, 0), (-28.5, -27.5, 0), (27.0, -23.0, 0), (-27.0, -16.0, 0))]
BASIN = Vector((5.0, -23.0, 0.0))
PATH = [Vector(p) for p in ((3.5, -31.5, 0), (4.5, -26.0, 0), (6.0, -20.5, 0))]  # front edge to the pond
PATH += [D.POND - D.BDIR * (D.L_BR / 2 - s) for s in (0, 5, 10, 15, 20)]  # across the pond where the bridge was
PATH += [Vector(p) for p in ((17.0, 6.5, 0), (11.0, 8.0, 0), (5.0, 7.0, 0), (-0.5, 5.0, 0))]  # on to the maple
STONES = []  # (centre, radius, in the water)
for p, q in zip(PATH, PATH[1:]):
    n = max(1, round((q - p).length / 3.1))
    for k in range(n):
        c = p.lerp(q, k / n) + horiz(rng.uniform(0, 2 * math.pi)) * 0.35
        gap = D.pond_gap(c)
        if not -1.0 <= gap <= 1.4:  # the bank itself is left to the rim stones
            STONES.append((c, rng.uniform(1.25, 1.6), gap < 0))
CLEAR = ([(c, r + 0.4) for c, r, _ in STONES] + [(BENCH, 6.0), (BASIN, 2.6)] + [(c, r + 2.5) for c, r in PILES]
         + [(c, 2.5) for c in PAMPAS])


def keep_clear(p, pad):  # where the garden's own props stand
    return (p.x < -WALL + 1.6 + pad or p.y > WALL - 1.6 - pad
            or any(D.flat(p - c).length < r + pad for c, r in CLEAR))


def box(bm, mi, c, size, rot=Matrix.Identity(3), bevel=0.0):  # c: centre of the bottom face
    tmp = bmesh.new()
    for v in bmesh.ops.create_cube(tmp, size=1.0)['verts']:
        v.co = c + rot @ Vector((v.co.x * size[0], v.co.y * size[1], (v.co.z + 0.5) * size[2]))
    if bevel:
        bmesh.ops.bevel(tmp, geom=list(tmp.edges), offset=bevel, segments=2, profile=0.6, affect='EDGES')
    for f in tmp.faces:
        f.material_index = mi
    me = bpy.data.meshes.new('tmp')
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)  # appends, material indices kept
    bpy.data.meshes.remove(me)


def dome(bm, mi, c, r, scale, rough=0.12):  # a lumpy ellipsoid cut flat just under the lawn: lawn slots keep clear
    for v in D.prim(bm, 'icosphere', mi, Matrix.LocRotScale(c, Euler((0, 0, rng.uniform(0, 6.3))), scale),
                    subdivisions=3, radius=r):
        v.co += (v.co - c).normalized() * r * rough * noise.noise(v.co * 0.9)
        v.co.z = max(v.co.z, -0.05)


def star_leaf(bm, mi, p, z, r=None, tilt=0.08):  # a five-lobed star, cupped: top and bottom fans share the rim (closed)
    r, a0, tx, ty = r or rng.uniform(0.5, 0.8), rng.uniform(0, 2 * math.pi), rng.gauss(0, tilt), rng.gauss(0, tilt)
    rim = [bm.verts.new(Vector((p.x, p.y, z))
                        + (horiz(a) * (1 if k % 2 == 0 else 0.5) + Z * (tx * math.cos(a) + ty * math.sin(a))) * r)
           for k, a in ((k, a0 + math.pi * k / 5) for k in range(10))]
    cu, cd = bm.verts.new(Vector((p.x, p.y, z + 0.08))), bm.verts.new(Vector((p.x, p.y, z - 0.02)))
    for k in range(10):
        bm.faces.new((cu, rim[k], rim[(k + 1) % 10])).material_index = mi
        bm.faces.new((cd, rim[(k + 1) % 10], rim[k])).material_index = mi


def wall():  # plastered temple wall on a stone footing under a dark tiled cap, along the two back edges
    bm, L = bmesh.new(), 2 * WALL + 1.3
    for c, rot in ((Vector((0, WALL, 0)), Matrix.Identity(3)), (Vector((-WALL, 0, 0)), Matrix.Rotation(math.pi / 2, 3, 'Z'))):
        box(bm, 0, c, (L, 1.6, 0.9), rot, bevel=0.15)
        box(bm, 1, c + Z * 0.85, (L - 0.4, 1.2, 3.7), rot, bevel=0.08)
        box(bm, 2, c + Z * 4.45, (L + 0.4, 2.4, 0.35), rot, bevel=0.1)  # eaves
        box(bm, 2, c + Z * 4.75, (L + 0.4, 1.4, 0.55), rot, bevel=0.15)  # roof
        box(bm, 2, c + Z * 5.2, (L + 0.6, 0.6, 0.45), rot, bevel=0.12)  # ridge
    D.prop('Wall', bm, *[D.material(n, h) for n, h in (('WallStone', 'a49a8c'), ('Plaster', 'efe7d8'),
                                                      ('RoofTile', '4b505a'))], sharp=50)


def path():  # stepping stones from the front edge, across the pond, to the maple's feet
    bm = bmesh.new()
    for c, r, wet in STONES:
        if wet:  # water stones stand up from the bed
            D.blob(bm, rng.randrange(2), Vector((c.x, c.y, 0.45 - r * 0.65)), r, (1.0, 0.88, 0.65), sub=3, rough=0.12,
                   yaw=rng.uniform(0, 6.3))
        else:  # lawn stones barely break the moss
            dome(bm, rng.randrange(2), Vector((c.x, c.y, 0.1)), r, (1.0, 0.88, 0.25))
    D.prop('Path', bm, D.material('PathStone', 'a8a097'), D.material('PathStoneDark', '8f877d'))


def nodate():  # a red-felt bench under a big red parasol: a maple-viewing tea set
    bm, rot = bmesh.new(), Matrix.Rotation(BENCH_YAW, 3, 'Z')
    x, y = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0))
    for sx in (-3.0, 3.0):
        for sy in (-0.85, 0.85):
            box(bm, 0, BENCH + x * sx + y * sy, (0.45, 0.45, 1.5), rot)
    box(bm, 0, BENCH + Z * 1.45, (7.2, 2.3, 0.3), rot, bevel=0.05)
    box(bm, 1, BENCH + Z * 1.72, (7.5, 2.7, 0.14), rot, bevel=0.04)  # the felt, draping over front and back
    for sy in (-1.33, 1.33):
        box(bm, 1, BENCH + y * sy + Z * 1.05, (7.5, 0.1, 0.8), rot)
    pole = BENCH + x * 2.6 + y * 1.9
    lean = (Z + y * 0.12 - x * 0.05).normalized()
    D.rod(bm, 0, pole, pole + lean * 8.8, 0.13, 0.11, seg=8)
    hub = pole + lean * 8.0
    m = Z.rotation_difference(lean).to_matrix().to_4x4()
    m.translation = hub + lean * 0.6
    D.prim(bm, 'cone', 2, m, segments=28, radius1=4.8, radius2=0.3, depth=1.2, cap_ends=True)  # canopy
    D.blob(bm, 0, hub + lean * 1.35, 0.28, sub=2)  # finial
    for k in range(10):  # ribs under the canopy, from the runner on the pole
        rim = hub + lean * 0.05 + (Matrix.Rotation(2 * math.pi * k / 10, 3, lean) @ lean.orthogonal().normalized()) * 4.6
        D.rod(bm, 0, pole + lean * 6.6, rim, 0.06, 0.05, seg=4)
    D.prop('Nodate', bm, *[D.material(n, h) for n, h in (('BenchWood', '5a3a28'), ('Felt', 'c4302a'),
                                                        ('Parasol', 'd8462c'))], sharp=45)


def leaf_piles():  # raked heaps of fallen leaves, a bamboo rake leaning on the biggest
    bm = bmesh.new()
    for c, R in PILES:
        dome(bm, 0, c, R, (1.0, 0.85, 0.62), rough=0.15)
        for _ in range(int(9 * R * R)):  # leaves over the heap
            q = c + horiz(rng.uniform(0, 2 * math.pi)) * R * 0.9 * math.sqrt(rng.random())
            e = D.flat(q - c)
            h = 0.62 * R * math.sqrt(max(0.0, 1 - (e.x / R) ** 2 - (e.y / (0.85 * R)) ** 2))
            star_leaf(bm, rng.choices(range(1, 5), (3, 3, 2, 1))[0], q, h + 0.02, tilt=0.25)
    c, R = PILES[0]
    d = horiz(math.radians(-30))
    head, rest = c + d * (R + 1.6) + Z * 0.2, c + Z * (0.62 * R + 0.15)
    end = head + (rest - head) * 1.45
    D.rod(bm, 5, head, end, 0.13, 0.13, seg=6)  # handle
    w = Z.cross(d).normalized()
    for k in range(11):  # the fan of tines
        a = math.radians(-38 + 76 * k / 10)
        D.rod(bm, 5, head + Z * 0.05, head + (d * math.cos(a) + w * math.sin(a)) * 2.0 + Z * 0.02, 0.06, 0.04, seg=4)
    D.rod(bm, 5, head + d * 0.9 - w * 0.6 + Z * 0.08, head + d * 0.9 + w * 0.6 + Z * 0.08, 0.07, 0.07, seg=4)
    D.prop('LeafPiles', bm, *[D.material(n, h) for n, h in (('PileBody', 'c4471f'), ('PileCrimson', 'a8241c'),
                                                           ('PileRed', 'cc3a22'), ('PileOrange', 'e0612b'),
                                                           ('PileAmber', 'eb9a3a'), ('Bamboo', 'cdb57a'))], sharp=30)


def pampas():  # susuki: a fountain of dry blades and tall silver plumes
    bm = bmesh.new()
    for c in PAMPAS:
        for k in range(22):
            a, tilt, h = rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(12, 48)), rng.uniform(3.0, 5.0)
            b = c + horiz(a) * rng.uniform(0, 0.6) - Z * 0.05
            D.rod(bm, k % 2, b, b + (horiz(a) * math.sin(tilt) + Z * math.cos(tilt)) * h, 0.14, 0.0, seg=3)
        for k in range(7):
            a, tilt, h = rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(4, 22)), rng.uniform(6.5, 8.5)
            b = c + horiz(a) * rng.uniform(0, 0.4) - Z * 0.05
            d = horiz(a) * math.sin(tilt) + Z * math.cos(tilt)
            D.rod(bm, 1, b, b + d * h, 0.08, 0.06, seg=4)
            pd = (d + horiz(a) * 0.35).normalized()  # the plume nods outward
            w = Z.cross(pd).normalized()
            D.prim(bm, 'icosphere', 2, D.frame(b + d * h + pd * 1.2, w * 0.45, pd.cross(w) * 0.45, pd * 1.6),
                   subdivisions=2, radius=1.0)
    D.prop('Pampas', bm, *[D.material(n, h) for n, h in (('PampasLeaf', 'a59a58'), ('PampasDry', 'c9b37a'),
                                                        ('PampasPlume', 'ece1c8'))])


def basin():  # tsukubai: a squat stone water basin with a bamboo ladle, stones round its foot
    bm = bmesh.new()
    D.blob(bm, 0, BASIN + Z * 0.95, 1.5, (1.0, 1.0, 0.68), sub=3, rough=0.1)
    D.prim(bm, 'cone', 1, Matrix.Translation(BASIN + Z * 1.9), segments=20, radius1=0.95, radius2=0.95, depth=0.12,
           cap_ends=True)  # the water
    D.blob(bm, 2, BASIN + Z * 1.05 + horiz(2.3) * 1.15, 0.7, (1.0, 0.8, 0.6), sub=2)  # moss on its side
    d = horiz(0.6)
    D.rod(bm, 3, BASIN + Z * 2.05 - d * 1.6, BASIN + Z * 2.05 + d * 1.1, 0.07, 0.07, seg=5)
    D.prim(bm, 'cone', 3, Matrix.Translation(BASIN + Z * 2.15 + d * 1.25), segments=10, radius1=0.25, radius2=0.25,
           depth=0.35, cap_ends=True)
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.4
        dome(bm, 0, BASIN + horiz(a) * 2.0 + Z * 0.15, rng.uniform(0.5, 0.7), (1.2, 1.0, 0.55), rough=0.2)
    D.prop('Basin', bm, *[D.material(n, h) for n, h in (('BasinStone', '9c958b'), ('BasinWater', '557f86'),
                                                       ('BasinMoss', '7d8b46'), ('Ladle', 'cdb57a'))])


def prune_rocks(obstacles):  # boulders the shared scatter dropped onto the wall or the path
    out = [D.bvh_of(ob) for ob in obstacles]
    rocks = bpy.data.objects['Rocks']
    bm = bmesh.new()
    bm.from_mesh(rocks.data)
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
    bad = [u for isl in islands if any(b.find_nearest(u.co)[3] < 0.3 or D.parity_inside(b, u.co)
                                       for u in isl for b in out) for u in isl]
    bmesh.ops.delete(bm, geom=bad, context='VERTS')
    bm.to_mesh(rocks.data)
    bm.free()


def fallen():  # fallen leaves, thickest under the pads, plenty afloat on the pond
    bm = bmesh.new()
    grass = bpy.data.objects['Grass']
    mounds = D.bvh_of(grass, keep=lambda f: f.material_index >= 2)
    lily_pts = [v.co for v in bpy.data.objects['LilyPads'].data.vertices]
    n = 0
    while n < 380:
        if rng.random() < 0.7:  # under a pad
            c, R, *_ = pads[rng.randrange(len(pads))]
            p = D.TREE + Vector((c.x, c.y, 0)) + horiz(rng.uniform(0, 2 * math.pi)) * R * 1.2 * math.sqrt(rng.random())
        else:
            p = Vector((rng.uniform(-34, 34), rng.uniform(-34, 34), 0))
        if not D.open_ground(p, -0.5):
            continue
        hit = mounds.ray_cast(p + Z * 5, -Z)[0]
        star_leaf(bm, rng.choices(range(5), (2, 3, 3, 2, 1))[0], p, (hit.z if hit else 0.0) + 0.05)
        n += 1
    n = 0
    while n < 30:  # afloat, clear of the lily pads and the stepping stones
        p = D.POND + Vector((rng.uniform(-9, 9), rng.uniform(-7, 7), 0))
        if (D.pond_gap(p) < -1.2 and min((D.flat(p) - D.flat(q)).length for q in lily_pts) > 0.9
                and all(D.flat(p - c).length > r + 0.6 for c, r, _ in STONES)):
            star_leaf(bm, rng.choices(range(5), (2, 3, 3, 2, 1))[0], p, 0.13)
            n += 1
    D.prop('Leaves', bm, *[D.material('Fallen' + n, h) for n, h in FALLEN], sharp=30)


def garden():
    # the shared lily pads are open fans; a slanted ray from a lawn slot crossing one counts a single hit and flips the
    # slot's parity vote, so close them into thin slabs
    pads_ob = bpy.data.objects['LilyPads']
    m = pads_ob.modifiers.new('solid', 'SOLIDIFY')
    m.thickness, m.use_rim = 0.05, True
    D.apply_modifiers(pads_ob)
    wall()
    path()
    nodate()
    leaf_piles()
    pampas()
    basin()
    prune_rocks([bpy.data.objects[n] for n in ('Wall', 'Path', 'Nodate', 'LeafPiles', 'Basin')])
    fallen()
    canopy = [D.bvh_of(ob) for ob in shells]  # self-check: no garden prop reaches into the foliage (or its slots)
    for n in ('Wall', 'Nodate', 'Pampas', 'Basin', 'LeafPiles'):
        for v in bpy.data.objects[n].data.vertices:
            assert all(b.find_nearest(v.co)[3] > 0.6 and not D.parity_inside(b, v.co) for b in canopy), ('prop in the crown', n)


D.finish('autumn', COLOURS, trunk, shells, blossoms, tips, a0, rocks=(((6, 25, 0), 1.6), ((-26, -24, 0), 2.1),
         ((31, 1, 0), 1.4), ((-12, -27, 0), 1.9), ((-29, 10, 0), 1.3)), pebbles=10, mounds=10, tufts=40, clumps=4,
         lotus=0, extras=garden, bridge=False, keep_clear=keep_clear)
