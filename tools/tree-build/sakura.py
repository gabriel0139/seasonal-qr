"""Build the sakura diorama: public/models/sakura.glb + public/trees/sakura.json.

Run from the repo root: npm run tree:build (Blender 5.2, headless). Deterministic (fixed SEED).
Units: 1 Blender unit = 1 QR module. Blender is Z up; the glTF exporter writes Y up,
so a Blender point (x, y, z) is (x, z, -y) in the GLB and in the slot file.
"""
import bpy, bmesh, json, math, os, random, sys, traceback
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

SEED = 20261102
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
GLB = os.path.join(ROOT, 'public', 'models', 'sakura.glb')
SLOTS = os.path.join(ROOT, 'public', 'trees', 'sakura.json')
N_SLOTS, TRUNK_SHARE = 4600, 0.07
MARGIN_TRUNK, MARGIN_BLOSSOM = 0.3, 0.6  # min distance from a slot to the surface

# Blender exits 0 when a -P script raises; make a failed build or self-check fail npm/CI
sys.excepthook = lambda *e: (traceback.print_exception(*e), sys.stdout.flush(), os._exit(1))
rng = random.Random(SEED)
noise.seed_set(SEED)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def srgb(h):  # hex sRGB -> linear RGBA (Principled base colour is linear)
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)


def material(name, hexrgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = srgb(hexrgb)
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = srgb(hexrgb)
    bsdf.inputs['Roughness'].default_value = 0.8
    return m


def link(name, me):
    me.name = name
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


def apply_modifiers(ob):
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    ob.modifiers.clear()
    old, ob.data = ob.data, me
    me.name = ob.name
    bpy.data.meshes.remove(old)


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def voxel_union(ob, voxel, displace=0.0):
    m = ob.modifiers.new('remesh', 'REMESH')
    m.mode, m.voxel_size, m.adaptivity = 'VOXEL', voxel, 0.0
    apply_modifiers(ob)  # one watertight shell: overlapping parts become a clean union
    if displace:  # lumpy "cauliflower" surface
        for v in ob.data.vertices:
            v.co += v.normal * displace * noise.noise(v.co * 0.45)


def smooth_decimate(ob, smooth, ratio):
    s = ob.modifiers.new('smooth', 'SMOOTH')
    s.factor, s.iterations = 0.6, smooth
    d = ob.modifiers.new('decimate', 'DECIMATE')
    d.ratio = min(1.0, ratio)
    apply_modifiers(ob)
    ob.data.shade_smooth()


def bez(p0, p1, p2, p3, t):
    u = 1 - t
    return p0 * u ** 3 + p1 * (3 * u * u * t) + p2 * (3 * u * t * t) + p3 * t ** 3


def lerp(a, b, t):
    return a + (b - a) * t


def horiz(az):
    return Vector((math.cos(az), math.sin(az), 0.0))


# ---------- trunk and branches: one POLY spline per strand / branch / root, bevelled ----------
SPLIT = Vector((3.0, -1.0, 11.5))
TWIST = math.radians(140)  # strands wind around each other up the trunk, then fork into the main branches


def axis(t):
    return bez(Vector((0, 0, -1.5)), Vector((-0.5, 0.3, 4.5)), Vector((1.0, -0.8, 8.0)), SPLIT, t)


MAIN = [  # azimuth deg, horizontal reach from the split, tip height, blossom cluster size
    (10, 16.0, 25, 8.0),
    (95, 13.0, 28, 7.5),
    (190, 16.5, 24, 8.0),
    (275, 12.5, 27, 7.5),
    (40, 3.0, 32, 9.0),  # leader
]
SECOND = [  # main branch, position along it, azimuth offset deg, length, rise, cluster size
    (0, 0.55, -55, 8, 4, 5.5),
    (1, 0.50, 50, 7, 5, 5.0),
    (2, 0.50, 50, 8, 3, 5.5),
    (2, 0.70, -45, 6, 5, 5.0),
    (3, 0.55, -50, 7, 4, 5.0),
]
splines, clusters, branches, tips = [], [], [], []


def wobbly(p0, p1, p2, p3, r0, r1, amp, key):
    n = max(8, int((p3 - p0).length / 0.5))
    pts, rad = [], []
    for k in range(1, n + 1):
        t = k / n
        q = bez(p0, p1, p2, p3, t)
        pts.append(q + noise.noise_vector(q * 0.15 + Vector((key * 7.31, 0, 0))) * amp * math.sin(math.pi * t))
        rad.append(lerp(r0, r1, t ** 0.8))
    return pts, rad


for i, (az_deg, reach, tip_z, size) in enumerate(MAIN):
    az = math.radians(az_deg)
    pts, rad = [], []
    for k in range(25):
        t = k / 24
        pts.append(axis(t) + horiz(az - TWIST + TWIST * t) * lerp(2.6, 1.2, t))
        rad.append(lerp(2.1, 1.65, t))
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

FILL = [((11, 7, 33), 6.5), ((-5, 6, 32), 6.5), ((-4, -8, 31), 6.5), ((11, -7, 31), 6.5)]  # close gaps in the dome
clusters += [(Vector(c), s) for c, s in FILL]

splines.append(([axis(k / 24) for k in range(25)], [lerp(2.3, 1.4, k / 24) for k in range(25)]))  # solid core

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

for k in range(5):  # root flare sinking into the soil
    phi = math.radians(k * 72 + 20 + rng.uniform(-15, 15))
    a = Vector((0, 0, 2.8)) + horiz(phi) * 1.0
    c = horiz(phi) * rng.uniform(5.5, 7.0) + Vector((0, 0, -1.0))
    pts, rad = wobbly(a, a + horiz(phi) * 1.5 - Vector((0, 0, 1.5)), c - horiz(phi) * 2 + Vector((0, 0, 0.6)), c,
                      1.6, 0.35, 0.3, 20 + k)
    splines.append(([a] + pts, [1.6] + rad))

cu = bpy.data.curves.new('TrunkCurve', 'CURVE')
cu.dimensions, cu.bevel_depth, cu.bevel_resolution, cu.use_fill_caps = '3D', 1.0, 4, True
for pts, rad in splines:
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for p, co, r in zip(sp.points, pts, rad):
        p.co, p.radius = (co.x, co.y, co.z, 1.0), r
cob = bpy.data.objects.new('TrunkCurve', cu)
scene.collection.objects.link(cob)
trunk = link('Trunk', bpy.data.meshes.new_from_object(cob.evaluated_get(bpy.context.evaluated_depsgraph_get())))
bpy.data.objects.remove(cob)
voxel_union(trunk, 0.25)
smooth_decimate(trunk, 6, 24000 / tris(trunk.data))
trunk.data.materials.append(material('Bark', '40281f'))

# ---------- blossoms: sphere puffs; one voxel-unioned shell per pink so colour seams sit in the creases ----------
PINKS = [material(n, h) for n, h in (('Blossom_Deep', 'e8879f'), ('Blossom_Mid', 'f2a3b7'),
                                     ('Blossom_Light', 'f7bccb'), ('Blossom_Pale', 'f9cbd7'))]


def rand_dir(up_bias):
    while True:
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        if 0.01 < v.length <= 1:
            v.normalize()
            v.z = v.z * 0.7 + up_bias
            return v.normalized()


def puff(bm, c, s):
    def ball(p, r):
        bmesh.ops.create_icosphere(bm, subdivisions=3 if r > 2 else 2, radius=r, matrix=Matrix.Translation(p))
    ball(c, s * 0.68)
    for _ in range(10):
        lc = c + rand_dir(0.15) * Vector((s * 0.55, s * 0.55, s * 0.4))
        lr = s * rng.uniform(0.42, 0.58)
        ball(lc, lr)
        for _ in range(6):  # small florets half-buried in each lobe
            ball(lc + rand_dir(0.3) * lr * 0.82, s * rng.uniform(0.18, 0.26))


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
    shells.append(link(f'BlossomShell{lv}', me))
    voxel_union(shells[-1], 0.32, displace=0.3)
ratio = 90000 / sum(tris(ob.data) for ob in shells)
bm = bmesh.new()
for lv, ob in enumerate(shells):
    smooth_decimate(ob, 5, ratio)
    for poly in ob.data.polygons:
        poly.material_index = lv
    bm.from_mesh(ob.data)  # appends
me = bpy.data.meshes.new('Blossoms')
bm.to_mesh(me)
bm.free()
assert len(me.polygons) == sum(len(ob.data.polygons) for ob in shells)
blossoms = link('Blossoms', me)
for m in PINKS:
    blossoms.data.materials.append(m)
blossoms.data.shade_smooth()

# ---------- base: two stacked slabs, soil top, stone sides ----------
bm = bmesh.new()
for half, z0, z1, bev in ((36.0, -4.0, 0.0, 0.9), (34.6, -7.0, -3.9, 0.4)):
    verts = bmesh.ops.create_cube(bm, size=1.0)['verts']
    for v in verts:
        v.co = Vector((v.co.x * 2 * half, v.co.y * 2 * half, z0 + (v.co.z + 0.5) * (z1 - z0)))
    edges = list({e for v in verts for e in v.link_edges})
    bmesh.ops.bevel(bm, geom=edges, offset=bev, segments=3, profile=0.5, affect='EDGES')
for f in bm.faces:
    f.material_index = 0 if f.normal.z > 0.6 else 1
me = bpy.data.meshes.new('Base')
bm.to_mesh(me)
bm.free()
base = link('Base', me)
base.data.materials.append(material('Soil', 'b38b62'))
base.data.materials.append(material('Stone', 'bdb2a0'))
base.data.shade_smooth()
base.data.set_sharp_from_angle(angle=math.radians(40))

# ---------- slot cloud: rejection-sample inside the volumes ----------
DIRS = [Vector(d).normalized() for d in ((1, 0.37, 0.21), (-0.29, 1, 0.43), (0.31, -0.17, 1))]


def bvh_of(ob):
    assert ob.matrix_world == Matrix.Identity(4)  # local space == world space
    me = ob.data
    return BVHTree.FromPolygons([v.co for v in me.vertices], [p.vertices for p in me.polygons])


def parity_inside(bvh, p):  # majority vote of ray-parity along three skewed directions
    votes = 0
    for d in DIRS:
        o, n = p, 0
        for _ in range(256):
            hit = bvh.ray_cast(o, d)[0]
            if hit is None:
                break
            n, o = n + 1, hit + d * 1e-4
        votes += n & 1
    return votes >= 2


def normal_inside(bvh, p, margin):  # independent check: closest point, normal sign, distance
    co, nor, _, dist = bvh.find_nearest(p)
    return co is not None and (co - p).dot(nor) > 0 and dist >= margin


def sample(ob, bvhs, count, margin, zmin):  # inside the union of the shells, at least margin deep in one
    vs = [v.co for v in ob.data.vertices]
    lo = Vector([min(v[i] for v in vs) for i in range(3)])
    hi = Vector([max(v[i] for v in vs) for i in range(3)])
    lo.z = max(lo.z, zmin)
    out = []
    while len(out) < count:
        p = Vector([rng.uniform(lo[i], hi[i]) for i in range(3)])
        if any(b.find_nearest(p)[3] >= margin and parity_inside(b, p) for b in bvhs):
            out.append(p)
    return out


bvh_t, bvh_b = [bvh_of(trunk)], [bvh_of(ob) for ob in shells]
for ob in shells:
    bpy.data.objects.remove(ob)
for t in tips:  # every branch must end buried in a blossom cluster
    assert any(parity_inside(b, t) and b.find_nearest(t)[3] > 1.0 for b in bvh_b), ('bare branch tip', t)
n_trunk = round(N_SLOTS * TRUNK_SHARE)
trunk_pts = sample(trunk, bvh_t, n_trunk, MARGIN_TRUNK, 0.3)  # only above the soil
bloom_pts = sample(blossoms, bvh_b, N_SLOTS - n_trunk, MARGIN_BLOSSOM, -1e9)

# shade: distance from the canopy's bottom centre, so 3 (palest) lands upper/outer and 1 (deepest) lower/inner
cx = sum(p.x for p in bloom_pts) / len(bloom_pts)
cy = sum(p.y for p in bloom_pts) / len(bloom_pts)
zlo, zhi = min(p.z for p in bloom_pts), max(p.z for p in bloom_pts)
rmax = max(math.hypot(p.x - cx, p.y - cy) for p in bloom_pts)
score = [math.hypot(math.hypot(p.x - cx, p.y - cy) / rmax, (p.z - zlo) / (zhi - zlo)) + rng.gauss(0, 0.08)
         for p in bloom_pts]
rank = sorted(range(len(bloom_pts)), key=score.__getitem__)
shade = [0] * len(bloom_pts)
for r, i in enumerate(rank):
    shade[i] = 1 if r < 0.3 * len(rank) else 2 if r < 0.7 * len(rank) else 3

slots = [(p, 0) for p in trunk_pts] + list(zip(bloom_pts, shade))
rng.shuffle(slots)  # any prefix covers the whole tree evenly (plan §3.2)
out = [[round(p.x, 2) + 0.0, round(p.z, 2) + 0.0, round(-p.y, 2) + 0.0, s] for p, s in slots]
os.makedirs(os.path.dirname(SLOTS), exist_ok=True)
with open(SLOTS, 'w') as f:
    json.dump({'name': 'sakura', 'slots': out}, f, separators=(',', ':'))

# self-check: re-test a random sample of the rounded slots with the independent closest-point test
for x, y, z, s in random.Random(1).sample(out, 600):
    p = Vector((x, -z, y))
    bvhs, margin = (bvh_t, MARGIN_TRUNK) if s == 0 else (bvh_b, MARGIN_BLOSSOM)
    assert any(normal_inside(b, p, margin - 0.02) for b in bvhs), (x, y, z, s)
assert len(out) >= 4400 and sum(s == 0 for *_, s in out) == n_trunk

# ---------- export ----------
for ob in scene.objects:
    ob.select_set(ob.name in ('Trunk', 'Blossoms', 'Base'))
os.makedirs(os.path.dirname(GLB), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format='GLB', export_apply=True, export_yup=True,
                          use_selection=True, export_materials='EXPORT', export_normals=True,
                          export_texcoords=False, export_extras=False)

counts = {ob.name: tris(ob.data) for ob in (trunk, blossoms, base)}
print('SAKURA tris', counts, 'total', sum(counts.values()))
print('SAKURA glb bytes', os.path.getsize(GLB))
print('SAKURA slots', len(out), {p: sum(s == p for *_, s in out) for p in range(4)})
