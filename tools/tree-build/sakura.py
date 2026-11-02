"""Build the sakura diorama: public/models/sakura.glb + public/trees/sakura.json.

Run from the repo root: npm run tree:build (Blender 5.2, headless). Deterministic (fixed SEED).
Units: 1 Blender unit = 1 QR module. Blender is Z up; the glTF exporter writes Y up,
so a Blender point (x, y, z) is (x, z, -y) in the GLB and in the slot file.
GLB roots: Trunk, Blossoms, Base (top at y = 0, 72 x 72, 7 deep) and Props, an empty whose children are
the scenery meshes (Water is the only transparent one). Slots lie only inside Trunk and Blossoms.
"""
import bpy, bmesh, bisect, json, math, os, random, sys, traceback
from mathutils import Vector, Matrix, Euler, noise
from mathutils.bvhtree import BVHTree

SEED = 20261102
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
GLB = os.path.join(ROOT, 'public', 'models', 'sakura.glb')
SLOTS = os.path.join(ROOT, 'public', 'trees', 'sakura.json')
N_SLOTS, TRUNK_SHARE = 4600, 0.07
MARGIN_TRUNK, MARGIN_BLOSSOM = 0.3, 0.6  # min distance from a slot to the surface
Z = Vector((0, 0, 1))
TREE = Vector((-12.0, 8.0, 0.0))  # left rear, glTF (-12, 0, -8): the pond, bridge and lantern take the front right
POND, POND_A, POND_RX, POND_RY = Vector((13.0, -7.0, 0.0)), math.radians(-20), 10.0, 7.0

# Blender exits 0 when a -P script raises; make a failed build or self-check fail npm/CI
sys.excepthook = lambda *e: (traceback.print_exception(*e), sys.stdout.flush(), os._exit(1))
rng = random.Random(SEED)
noise.seed_set(SEED)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def srgb(h):  # hex sRGB -> linear RGBA (Principled base colour is linear)
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)


def material(name, hexrgb, rough=0.8):
    m = bpy.data.materials.new(name)
    m.diffuse_color = srgb(hexrgb)
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = srgb(hexrgb)
    bsdf.inputs['Roughness'].default_value = rough
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


def flat(p):
    return Vector((p.x, p.y))


# ---------- trunk and branches: one POLY spline per strand / branch / root / burl, bevelled ----------
# Built around the origin, then moved to TREE once meshed (the noise-driven shapes don't depend on the offset).
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


def wobbly(p0, p1, p2, p3, r0, r1, amp, key):
    n = max(8, int((p3 - p0).length / 0.5))
    pts, rad = [], []
    for k in range(1, n + 1):
        t = k / n
        q = bez(p0, p1, p2, p3, t)
        pts.append(q + noise.noise_vector(q * 0.15 + Vector((key * 7.31, 0, 0))) * amp * math.sin(math.pi * t))
        rad.append(lerp(r0, r1, t ** 0.8))
    return pts, rad


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
smooth_decimate(trunk, 6, 30000 / tris(trunk.data))
trunk.data.transform(Matrix.Translation(TREE))
trunk.data.materials.append(material('Bark', '40281f'))
tips = [t + TREE for t in tips]

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


def florets(ob, per_area, rmin, rmax):  # small sub-lobes over the shell so each puff reads as dense blossom
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    faces = list(bm.faces)
    areas = [f.calc_area() for f in faces]
    for f in rng.choices(faces, areas, k=int(per_area * sum(areas))):
        r = rng.uniform(rmin, rmax)
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r,
                                   matrix=Matrix.Translation(f.calc_center_median() + f.normal * r * 0.3))
    bm.to_mesh(ob.data)
    bm.free()


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
    florets(shells[-1], 0.5, 0.45, 1.05)
    voxel_union(shells[-1], 0.2)
ratio = 165000 / sum(tris(ob.data) for ob in shells)
bm = bmesh.new()
for lv, ob in enumerate(shells):
    smooth_decimate(ob, 2, ratio)
    ob.data.transform(Matrix.Translation(TREE))
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


# ---------- geometry helpers for the base and props ----------
def pond_r(a):  # pond outline radius at world polar angle a around POND: a wobbly ellipse
    b = a - POND_A
    return (1 + 0.08 * math.sin(3 * b + 1) + 0.05 * math.sin(5 * b + 2)) / math.hypot(math.cos(b) / POND_RX,
                                                                                  math.sin(b) / POND_RY)


def pond_pt(a, scale=1.0, z=0.0):
    return POND + horiz(a) * pond_r(a) * scale + Z * z


def pond_gap(p):  # horizontal distance outside the pond outline (negative inside)
    d = flat(p - POND)
    return d.length - pond_r(math.atan2(d.y, d.x))


def frame(p, x, y, z):  # matrix taking the unit primitive's axes to x, y, z at p (keep x, y, z right-handed)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = p
    return m


def prim(bm, kind, mi, matrix, **kw):
    verts = getattr(bmesh.ops, 'create_' + kind)(bm, matrix=matrix, **kw)['verts']
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mi
    return verts


def rod(bm, mi, a, b, r1, r2, seg=6, cap=True):  # cylinder or cone from a to b
    z = (b - a).normalized()
    x = z.orthogonal().normalized()
    prim(bm, 'cone', mi, frame((a + b) / 2, x, z.cross(x), z), segments=seg, radius1=r1, radius2=r2,
         depth=(b - a).length, cap_ends=cap)


def blob(bm, mi, c, r, scale=(1, 1, 1), sub=2, rough=0.0, yaw=0.0):  # (lumpy) ellipsoid
    for v in prim(bm, 'icosphere', mi, Matrix.LocRotScale(c, Euler((0, 0, yaw)), scale), subdivisions=sub, radius=r):
        v.co += (v.co - c).normalized() * r * rough * noise.noise(v.co * 0.9)


def tube(bm, mi, pts, r, side=Z, sides=6, closed=False):  # ring frames keep `side` in plane, so no twisting
    n, rings = len(pts), []
    for i, p in enumerate(pts):
        t = (pts[(i + 1) % n if closed else min(i + 1, n - 1)] - pts[(i - 1) % n if closed else max(i - 1, 0)]).normalized()
        a = (side - t * side.dot(t)).normalized()
        b = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / sides) + b * math.sin(2 * math.pi * k / sides)) * r)
                      for k in range(sides)])
    faces = [bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
             for r0, r1 in zip(rings, rings[1:] + rings[:1] if closed else rings[1:]) for k in range(sides)]
    if not closed:
        faces += [bm.faces.new(rings[0][::-1]), bm.faces.new(rings[-1])]
    for f in faces:
        f.material_index = mi


def fan(bm, mi, c, ring):  # flat disc, wound counter-clockwise from above so it faces up
    cv = bm.verts.new(c)
    vs = [bm.verts.new(p) for p in ring]
    for v0, v1 in zip(vs, vs[1:]):
        bm.faces.new((cv, v0, v1)).material_index = mi


# ---------- base: moss-topped slab over an inset stone tier, pond basin cut into the top ----------
def slab(bm, half, z0, z1, bev):
    verts = bmesh.ops.create_cube(bm, size=1.0)['verts']
    for v in verts:
        v.co = Vector((v.co.x * 2 * half, v.co.y * 2 * half, z0 + (v.co.z + 0.5) * (z1 - z0)))
    bmesh.ops.bevel(bm, geom=list({e for v in verts for e in v.link_edges}), offset=bev, segments=3, profile=0.5,
                    affect='EDGES')


bm = bmesh.new()
slab(bm, 36.0, -3.2, 0.0, 1.0)
me = bpy.data.meshes.new('Base')
bm.to_mesh(me)
bm.free()
base = link('Base', me)
bm = bmesh.new()  # bowl-shaped cutter: rings of the outline, shrinking with depth
K = 96
rings = [[bm.verts.new(pond_pt(2 * math.pi * k / K, 0.98 * s, z)) for k in range(K)]
         for s, z in ((1.0, 1.0), (1.0, -0.3), (0.85, -0.9), (0.6, -1.35), (0.3, -1.6))]
bm.faces.new(rings[0])
for r0, r1 in zip(rings, rings[1:]):
    for k in range(K):
        bm.faces.new((r0[k], r1[k], r1[(k + 1) % K], r0[(k + 1) % K]))
bottom = bm.verts.new(POND + Z * -1.7)
for k in range(K):
    bm.faces.new((rings[-1][k], bottom, rings[-1][(k + 1) % K]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new('PondCut')
bm.to_mesh(me)
bm.free()
cutter = link('PondCut', me)
mod = base.modifiers.new('pond', 'BOOLEAN')
mod.operation, mod.solver, mod.object = 'DIFFERENCE', 'EXACT', cutter
apply_modifiers(base)
bpy.data.objects.remove(cutter)
bm = bmesh.new()
bm.from_mesh(base.data)
slab(bm, 34.0, -7.0, -3.1, 0.4)
for f in bm.faces:  # 0 moss top (wraps over the bevel), 1 stone sides, 2 pond bed
    c = f.calc_center_median()
    f.material_index = 2 if c.z < -0.02 and pond_gap(c) < 0.5 else 0 if f.normal.z > 0.6 else 1
for side in range(4):  # rock chunks poking out of the lower tier, staying inside the 72 x 72 footprint
    n, t = horiz(side * math.pi / 2), horiz(side * math.pi / 2 + math.pi / 2)
    for _ in range(3):
        r = rng.uniform(1.3, 2.0)
        c = n * (35.9 - 0.9 * r) + t * rng.uniform(-29, 29) + Z * rng.uniform(-5.6, -4.6)
        for v in prim(bm, 'icosphere', 3, frame(c, n * 0.9, t * 1.3, Z * 0.75), subdivisions=2, radius=r):
            v.co += (v.co - c).normalized() * r * 0.15 * noise.noise(v.co * 0.8)
            v.co.z = max(-7.0, min(-3.2, v.co.z))
            v.co.x, v.co.y = (max(-35.95, min(35.95, w)) for w in (v.co.x, v.co.y))
base.data.materials.clear()  # the boolean leaves an empty slot; clear before writing indices (clearing remaps them)
bm.to_mesh(base.data)
bm.free()
for m in (material('Moss', 'a7b950'), material('Stone', 'c6a9a2'), material('PondBed', '4e7a68'),
          material('StoneChunk', '9a7f79')):
    base.data.materials.append(m)
base.data.shade_smooth()
base.data.set_sharp_from_angle(angle=math.radians(40))

# ---------- props: everything under one Props empty, merged into a few meshes ----------
props = bpy.data.objects.new('Props', None)
scene.collection.objects.link(props)
L_BR, W_BR, H_BR = 20.0, 4.2, 4.5  # bridge length, deck width, arch rise
BDIR = horiz(math.radians(55))  # crosses the pond's short axis, diagonal to the base
BSIDE = Z.cross(BDIR)
B0 = POND - BDIR * (L_BR / 2)
LANTERN = Vector((10.5, -19.0, 0.0))  # just off the bridge's front-right foot
FOOT = TREE + Vector((a0.x, a0.y, 0))  # centre of the root flare


def bridge_dist(p):  # horizontal distance from the bridge's centre line
    d = flat(p - B0)
    return (d - flat(BDIR) * max(0.0, min(L_BR, d.dot(flat(BDIR))))).length


def open_ground(p, pad):  # off the pond, bridge, lantern and trunk, inside the base
    return (max(abs(p.x), abs(p.y)) < 34 - pad and pond_gap(p) > 1.5 + pad and bridge_dist(p) > 2.8 + pad
            and (flat(p - LANTERN)).length > 2.5 + pad and flat(p - FOOT).length > 8.5 + pad)


def prop(name, bm, *mats, sharp=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(name, me)
    ob.parent = props
    for m in mats:
        me.materials.append(m)
    me.shade_smooth()
    if sharp:
        me.set_sharp_from_angle(angle=math.radians(sharp))
    return ob


def ground_pt(near_pond):  # a candidate spot, biased to the pond rim, the tree's feet or anywhere
    roll = rng.random()
    if roll < near_pond:
        a = rng.uniform(0, 2 * math.pi)
        return pond_pt(a) + horiz(a) * rng.uniform(1.8, 4.5)
    if roll < near_pond + 0.2:
        return FOOT + horiz(rng.uniform(0, 2 * math.pi)) * rng.uniform(8.6, 14)
    return Vector((rng.uniform(-33, 33), rng.uniform(-33, 33), 0))


# pond: earthen rim bank and rim stones; the hole's edge hides under the water and the bank
bm = bmesh.new()
tube(bm, 0, [pond_pt(2 * math.pi * k / 96, 1.02, -0.25) for k in range(96)], 0.7, sides=8, closed=True)
for k in range(30):
    a = 2 * math.pi * (k + rng.uniform(-0.3, 0.3)) / 30
    p = pond_pt(a, 1.0, 0.1) + horiz(a) * 0.5
    if bridge_dist(p) > 3.0:
        blob(bm, 1 + rng.randrange(2), p, rng.uniform(0.5, 0.95), (1.3, 1.0, 0.6), rough=0.25,
             yaw=rng.uniform(0, 6.3))
prop('Pond', bm, material('PondBank', '7f8d45'), material('RimStone', 'b9a7a1'), material('RimStoneLight', 'd3c3bc'))

bm = bmesh.new()
fan(bm, 0, POND + Z * 0.04, [pond_pt(2 * math.pi * k / 96, 1.04, 0.04) for k in range(97)])
water_mat = material('Water', '9fd6ea', rough=0.1)
water_mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.7
water_mat.surface_render_method = 'BLENDED'
water = prop('Water', bm, water_mat)

# lily pads with a notch, two carrying a lotus; above the water's bob (+-0.05)
centre_mat = material('FlowerCentre', 'f2c84b')
bm, pads = bmesh.new(), []
while len(pads) < 4:
    p = POND + Vector((rng.uniform(-8, 8), rng.uniform(-6, 6), 0))
    if pond_gap(p) < -1.8 and bridge_dist(p) > 3.6 and all((p - q).length > 3 for q in pads):
        pads.append(p)
for i, p in enumerate(pads):
    r, notch, a0 = rng.uniform(1.0, 1.5), math.radians(rng.uniform(25, 45)), rng.uniform(0, 2 * math.pi)
    fan(bm, 0, p + Z * 0.18, [p + horiz(a0 + notch / 2 + (2 * math.pi - notch) * k / 16) * r + Z * 0.14 for k in range(17)])
    if i < 2:  # lotus: two rings of petals round a yellow seed head
        c = p + Z * 0.15 + horiz(a0 + math.pi) * r * 0.2
        for n, tilt, ln, off in ((8, 62, 0.95, 0.15), (6, 28, 0.85, 0.08)):
            for k in range(n):
                th = 2 * math.pi * (k + 0.5 * (n == 6)) / n
                d = horiz(th) * math.sin(math.radians(tilt)) + Z * math.cos(math.radians(tilt))
                w = horiz(th + math.pi / 2)
                prim(bm, 'icosphere', 1, frame(c + horiz(th) * off + d * ln * 0.5, w * 0.3, d.cross(w) * 0.12, d * ln * 0.5),
                     subdivisions=2, radius=1.0)
        blob(bm, 2, c + Z * 0.25, 1.0, (0.22, 0.22, 0.14), sub=1)
prop('LilyPads', bm, material('LilyPad', '5f9b48'), material('Lotus', 'f3a2c0'), centre_mat)


# arched footbridge: planks on a sine arch, side stringers, posts with knobbed ends, two rails, four piers
def deck_pt(s):
    return B0 + BDIR * s + Z * (0.25 + H_BR * math.sin(math.pi * s / L_BR))


def deck_t(s):
    return (deck_pt(s + 0.01) - deck_pt(s - 0.01)).normalized()


ss = [L_BR * k / 400 for k in range(401)]
arc = [0.0]
for s0, s1 in zip(ss, ss[1:]):
    arc.append(arc[-1] + (deck_pt(s1) - deck_pt(s0)).length)


def s_at(frac):  # bridge parameter at a fraction of the arch's length
    return ss[min(bisect.bisect(arc, frac * arc[-1]), 400)]


bm = bmesh.new()
n = int(arc[-1] / 0.8)
for j in range(n):
    s = s_at((j + 0.5) / n)
    t = deck_t(s)
    up = t.cross(BSIDE)
    prim(bm, 'cube', 0, frame(deck_pt(s) - up * 0.15, t * 0.68, BSIDE * (W_BR + rng.uniform(-0.15, 0.15)), up * 0.3),
         size=1.0)
line = [s_at(k / 40) for k in range(41)]
for side in (-1, 1):
    tube(bm, 0, [deck_pt(s) + BSIDE * side * (W_BR / 2 - 0.3) - deck_t(s).cross(BSIDE) * 0.45 for s in line], 0.3,
         side=BSIDE)
    rail = BSIDE * side * (W_BR / 2 - 0.15)
    tube(bm, 1, [deck_pt(s) + rail + Z * 2.0 for s in line], 0.17, side=BSIDE)
    tube(bm, 1, [deck_pt(s) + rail + Z * 1.05 for s in line], 0.11, side=BSIDE)
    for i in range(9):
        b = deck_pt(s_at(i / 8)) + rail
        end = i in (0, 8)
        rod(bm, 1, b - Z * 0.3, b + Z * (2.3 if end else 2.05), 0.3 if end else 0.18, 0.3 if end else 0.18,
            seg=8 if end else 4)
        if end:
            blob(bm, 1, b + Z * 2.65, 0.4)
    for s in (L_BR * 0.3, L_BR * 0.7):
        p = deck_pt(s) + BSIDE * side * (W_BR / 2 - 0.3)
        rod(bm, 0, Vector((p.x, p.y, -1.3)), p - Z * 0.4, 0.26, 0.26, seg=8)
prop('Bridge', bm, material('Wood', '9c6b47'), material('WoodDark', '6e4932'), sharp=65)

# stone lantern (toro): foot, post, platform, glowing firebox between six pillars, eaves, roof, finial
bm = bmesh.new()
for z0, z1, r0, r1, seg, mi in ((0, 0.9, 2.0, 1.75, 6, 0), (0.9, 4.4, 0.75, 0.62, 10, 0), (4.4, 5.2, 1.35, 1.9, 6, 0),
                                (5.2, 7.0, 1.0, 1.0, 12, 1), (7.0, 7.35, 2.75, 2.9, 6, 0), (7.35, 8.7, 2.9, 0.4, 6, 0)):
    prim(bm, 'cone', mi, Matrix.Translation(LANTERN + Z * ((z0 + z1) / 2)), segments=seg, radius1=r0, radius2=r1,
         depth=z1 - z0, cap_ends=True)
for k in range(6):
    c = LANTERN + horiz(k * math.pi / 3 + math.pi / 6) * 1.2
    rod(bm, 0, c + Z * 5.2, c + Z * 7.0, 0.24, 0.24, seg=4)
blob(bm, 0, LANTERN + Z * 9.05, 0.5)
rod(bm, 0, LANTERN + Z * 9.4, LANTERN + Z * 10.1, 0.28, 0.0, seg=8)
glow = material('LanternGlow', 'ffe2a0')
glow.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = srgb('ffcf7a')
glow.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.6
prop('Lantern', bm, material('LanternStone', 'bdb0a8'), glow, sharp=40)

# rocks round the pond and in the corners, plus pebbles
ROCKS = [(pond_pt(math.radians(a)) + horiz(math.radians(a)) * gap, r) for a, gap, r in
         ((10, 2.6, 2.6), (120, 2.2, 1.8), (165, 2.0, 1.4), (290, 2.4, 1.9))]
ROCKS += [(Vector(p), r) for p, r in (((29, -29, 0), 2.4), ((-28, -29, 0), 1.7), ((28, 28, 0), 2.0),
                                       ((-30, 27, 0), 2.8), ((-3.5, 15, 0), 1.5), ((-22, -2, 0), 1.2),
                                       ((20, 17, 0), 1.8), ((23.5, 15, 0), 1.0))]
bm = bmesh.new()
for p, r in ROCKS:
    blob(bm, rng.randrange(2), p + Z * r * 0.15, r, (1.2, 0.95, 0.65), sub=3, rough=0.18, yaw=rng.uniform(0, 6.3))
pebbles = 0
while pebbles < 22:
    p = ground_pt(0.5)
    if open_ground(p, -0.5):
        pebbles += 1
        r = rng.uniform(0.25, 0.5)
        blob(bm, rng.randrange(2), p + Z * r * 0.1, r, (1.2, 1.0, 0.6), sub=2, rough=0.2, yaw=rng.uniform(0, 6.3))
prop('Rocks', bm, material('RockGrey', 'a39b98'), material('RockPink', 'bba7a1'))

# grass tufts: fans of three-sided blades, over low moss mounds that break up the flat lawn
bm, tufts, mounds = bmesh.new(), 0, 0
while mounds < 16:
    p, r = ground_pt(0.2), rng.uniform(1.5, 3.5)
    if open_ground(p, r):
        mounds += 1
        blob(bm, 2 + mounds % 2, p, r, (1.0, 0.8, 0.3), sub=3, rough=0.1, yaw=rng.uniform(0, 6.3))
while tufts < 60:
    p = ground_pt(0.3)
    if not open_ground(p, 0):
        continue
    tufts += 1
    mi = rng.randrange(2)
    for _ in range(rng.randint(7, 11)):
        phi, tilt, h = rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(5, 38)), rng.uniform(1.4, 2.8)
        b = p + horiz(phi) * rng.uniform(0, 0.6) - Z * 0.1
        rod(bm, mi, b, b + (horiz(phi) * math.sin(tilt) + Z * math.cos(tilt)) * h, 0.24, 0.0, seg=3, cap=False)
prop('Grass', bm, material('GrassDark', '7f9c3c'), material('GrassLight', 'b8cc5c'), material('MossDark', '9db14a'),
     material('MossLight', 'b0c156'))

# flowers in small clumps: five-petal heads on stems, white or lavender
bm, clumps = bmesh.new(), 0
while clumps < 10:
    p = ground_pt(0.4)
    if not open_ground(p, 0.8):
        continue
    clumps += 1
    for _ in range(rng.randint(3, 4)):
        b = p + horiz(rng.uniform(0, 2 * math.pi)) * rng.uniform(0, 1.2)
        top = b + Z * rng.uniform(1.0, 1.8) + horiz(rng.uniform(0, 2 * math.pi)) * 0.15
        rod(bm, 2, b - Z * 0.05, top, 0.07, 0.05, seg=4)
        a0 = rng.uniform(0, 2 * math.pi)
        for k in range(5):
            blob(bm, clumps % 2, top + horiz(a0 + k * 2 * math.pi / 5) * 0.3, 0.26, (1, 1, 0.6), sub=1)
        blob(bm, 3, top + Z * 0.08, 0.15, sub=1)
prop('Flowers', bm, material('FlowerWhite', 'faf7f0'), material('FlowerLavender', 'b7a2e4'), material('Stem', '6c9a3a'),
     centre_mat)

# ---------- slot cloud: rejection-sample inside the volumes ----------
DIRS = [Vector(d).normalized() for d in ((1, 0.37, 0.21), (-0.29, 1, 0.43), (0.31, -0.17, 1))]


def bvh_of(*obs):
    vs, polys = [], []
    for ob in obs:
        assert ob.matrix_world == Matrix.Identity(4)  # local space == world space
        polys += [[i + len(vs) for i in p.vertices] for p in ob.data.polygons]
        vs += [v.co.copy() for v in ob.data.vertices]
    return BVHTree.FromPolygons(vs, polys)


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
    # both inside tests must agree: decimating the floret-covered shells folds a few triangles, fooling either alone
    vs = [v.co for v in ob.data.vertices]
    lo = Vector([min(v[i] for v in vs) for i in range(3)])
    hi = Vector([max(v[i] for v in vs) for i in range(3)])
    lo.z = max(lo.z, zmin)
    out = []
    while len(out) < count:
        p = Vector([rng.uniform(lo[i], hi[i]) for i in range(3)])
        if any(normal_inside(b, p, margin) and parity_inside(b, p) for b in bvhs):
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

# self-check: the props and base contracts
prop_obs = list(props.children)
for ob in prop_obs:
    vs = [v.co for v in ob.data.vertices]
    assert all(max(abs(v.x), abs(v.y)) <= 36 and -2 <= v.z <= 14 for v in vs), ('prop outside the base', ob.name)
    assert min((flat(v) - flat(FOOT)).length for v in vs) > 7, ('prop in the trunk area', ob.name)
assert [m.name for m in water.data.materials] == ['Water'] and all(0 <= v.co.z <= 0.1 for v in water.data.vertices)
bvh_p = bvh_of(*prop_obs)
assert not any(parity_inside(bvh_p, Vector((x, -z, y))) or bvh_p.find_nearest(Vector((x, -z, y)))[3] < 0.3
               for x, y, z, _ in out), 'a slot lies inside a prop'
bv = [v.co for v in base.data.vertices]
assert max(v.z for v in bv) <= 1e-4 and min(v.z for v in bv) >= -8 and max(max(abs(v.x), abs(v.y)) for v in bv) <= 36

# ---------- export ----------
for ob in scene.objects:
    ob.select_set(ob.name in ('Trunk', 'Blossoms', 'Base', 'Props') or ob.parent == props)
os.makedirs(os.path.dirname(GLB), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format='GLB', export_apply=True, export_yup=True,
                          use_selection=True, export_materials='EXPORT', export_normals=True,
                          export_texcoords=False, export_extras=False)

# self-check the exported file: Props subtree, Water the only blended material, size and triangle budgets
with open(GLB, 'rb') as f:
    glb = f.read()
gj = json.loads(glb[20:20 + int.from_bytes(glb[12:16], 'little')])
nodes = {nd['name']: nd for nd in gj['nodes']}
assert {gj['nodes'][i]['name'] for i in gj['scenes'][0]['nodes']} == {'Trunk', 'Blossoms', 'Base', 'Props'}
assert {gj['nodes'][i]['name'] for i in nodes['Props']['children']} == {ob.name for ob in prop_obs}
mats = {m['name']: m for m in gj['materials']}
assert mats['Water'].get('alphaMode') == 'BLEND' and abs(mats['Water']['pbrMetallicRoughness']['baseColorFactor'][3] - 0.7) < 1e-3
assert all(m.get('alphaMode', 'OPAQUE') == 'OPAQUE' for k, m in mats.items() if k != 'Water'), 'only Water is transparent'
counts = {ob.name: tris(ob.data) for ob in [trunk, blossoms, base] + prop_obs}
assert sum(counts.values()) < 250000 and len(glb) < 5e6, (sum(counts.values()), len(glb))

print('SAKURA tris', counts, 'total', sum(counts.values()))
print('SAKURA glb bytes', len(glb))
print('SAKURA slots', len(out), {p: sum(s == p for *_, s in out) for p in range(4)})
