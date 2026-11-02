"""Shared diorama builder: base, props, slot cloud, self-checks and GLB export for every season.

A season script (sakura.py, autumn.py) calls init(seed), builds its trunk splines and canopy shells with the
helpers here, then finish(). Run from the repo root: npm run tree:build (Blender 5.2, headless). Deterministic
per seed: every random draw goes through `rng` in a fixed order, so moving code around changes the output.
Units: 1 Blender unit = 1 QR module. Blender is Z up; the glTF exporter writes Y up,
so a Blender point (x, y, z) is (x, z, -y) in the GLB and in the slot file.
GLB roots: Trunk, Blossoms (the canopy), Base (top at y = 0, 72 x 72, 7 deep) and Props, an empty whose children
are the scenery meshes (Water is the only transparent one). Slots lie inside the tree, the lawn, the bridge,
the stone props and the pond; the slot file contract is at the top of the slot-cloud section below.
"""
import bpy, bmesh, bisect, json, math, os, random, sys, traceback
from mathutils import Vector, Matrix, Euler, noise
from mathutils.bvhtree import BVHTree

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
MARGIN_TRUNK, MARGIN_BLOSSOM = 0.3, 0.6  # min distance from a slot to the surface
Z = Vector((0, 0, 1))
TREE = Vector((-12.0, 8.0, 0.0))  # left rear, glTF (-12, 0, -8): the pond, bridge and lantern take the front right
POND, POND_A, POND_RX, POND_RY = Vector((13.0, -7.0, 0.0)), math.radians(-20), 10.0, 7.0

# Blender exits 0 when a -P script raises; make a failed build or self-check fail npm/CI
sys.excepthook = lambda *e: (traceback.print_exception(*e), sys.stdout.flush(), os._exit(1))
rng = random.Random()


def init(seed):
    rng.seed(seed)
    noise.seed_set(seed)
    bpy.ops.wm.read_factory_settings(use_empty=True)


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
    bpy.context.scene.collection.objects.link(ob)
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


# ---------- tree: trunk splines -> Trunk; canopy shells -> Blossoms (built around the origin, moved to TREE) ----------
def wobbly(p0, p1, p2, p3, r0, r1, amp, key):  # a noisy bezier branch: points and radii, p0 left out
    n = max(8, int((p3 - p0).length / 0.5))
    pts, rad = [], []
    for k in range(1, n + 1):
        t = k / n
        q = bez(p0, p1, p2, p3, t)
        pts.append(q + noise.noise_vector(q * 0.15 + Vector((key * 7.31, 0, 0))) * amp * math.sin(math.pi * t))
        rad.append(lerp(r0, r1, t ** 0.8))
    return pts, rad


def trunk_mesh(splines, bark):  # one POLY spline per strand / branch / root, bevelled, unioned and decimated
    cu = bpy.data.curves.new('TrunkCurve', 'CURVE')
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution, cu.use_fill_caps = '3D', 1.0, 4, True
    for pts, rad in splines:
        sp = cu.splines.new('POLY')
        sp.points.add(len(pts) - 1)
        for p, co, r in zip(sp.points, pts, rad):
            p.co, p.radius = (co.x, co.y, co.z, 1.0), r
    cob = bpy.data.objects.new('TrunkCurve', cu)
    bpy.context.scene.collection.objects.link(cob)
    trunk = link('Trunk', bpy.data.meshes.new_from_object(cob.evaluated_get(bpy.context.evaluated_depsgraph_get())))
    bpy.data.objects.remove(cob)
    voxel_union(trunk, 0.25)
    smooth_decimate(trunk, 6, 30000 / tris(trunk.data))
    trunk.data.transform(Matrix.Translation(TREE))
    trunk.data.materials.append(material('Bark', bark))
    return trunk


def rand_dir(up_bias):
    while True:
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        if 0.01 < v.length <= 1:
            v.normalize()
            v.z = v.z * 0.7 + up_bias
            return v.normalized()


def florets(ob, per_area, rmin, rmax, up=None):  # small sub-lobes over the shell; up: only faces facing up this much
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    faces = list(bm.faces) if up is None else [f for f in bm.faces if f.normal.z > up]
    areas = [f.calc_area() for f in faces]
    for f in rng.choices(faces, areas, k=int(per_area * sum(areas))):
        r = rng.uniform(rmin, rmax)
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r,
                                   matrix=Matrix.Translation(f.calc_center_median() + f.normal * r * 0.3))
    bm.to_mesh(ob.data)
    bm.free()


def canopy_mesh(shells, mats, budget, smooth=2):  # decimate the shells to the budget, merge: one material each
    ratio = budget / sum(tris(ob.data) for ob in shells)
    bm = bmesh.new()
    for lv, ob in enumerate(shells):
        smooth_decimate(ob, smooth, ratio)
        ob.data.transform(Matrix.Translation(TREE))
        for poly in ob.data.polygons:
            poly.material_index = lv
        bm.from_mesh(ob.data)  # appends
    me = bpy.data.meshes.new('Blossoms')
    bm.to_mesh(me)
    bm.free()
    assert len(me.polygons) == sum(len(ob.data.polygons) for ob in shells)
    blossoms = link('Blossoms', me)
    for m in mats:
        blossoms.data.materials.append(m)
    blossoms.data.shade_smooth()
    return blossoms


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


def slab(bm, half, z0, z1, bev):
    verts = bmesh.ops.create_cube(bm, size=1.0)['verts']
    for v in verts:
        v.co = Vector((v.co.x * 2 * half, v.co.y * 2 * half, z0 + (v.co.z + 0.5) * (z1 - z0)))
    bmesh.ops.bevel(bm, geom=list({e for v in verts for e in v.link_edges}), offset=bev, segments=3, profile=0.5,
                    affect='EDGES')


L_BR, W_BR, H_BR = 20.0, 4.2, 4.5  # bridge length, deck width, arch rise
BDIR = horiz(math.radians(55))  # crosses the pond's short axis, diagonal to the base
BSIDE = Z.cross(BDIR)
B0 = POND - BDIR * (L_BR / 2)
LANTERN = Vector((10.5, -19.0, 0.0))  # just off the bridge's front-right foot
FOOT = None  # centre of the root flare, set by finish()


def bridge_dist(p):  # horizontal distance from the bridge's centre line
    d = flat(p - B0)
    return (d - flat(BDIR) * max(0.0, min(L_BR, d.dot(flat(BDIR))))).length


def open_ground(p, pad):  # off the pond, bridge, lantern and trunk, inside the base
    return (max(abs(p.x), abs(p.y)) < 34 - pad and pond_gap(p) > 1.5 + pad and bridge_dist(p) > 2.8 + pad
            and (flat(p - LANTERN)).length > 2.5 + pad and flat(p - FOOT).length > 8.5 + pad)


def ground_pt(near_pond):  # a candidate spot, biased to the pond rim, the tree's feet or anywhere
    roll = rng.random()
    if roll < near_pond:
        a = rng.uniform(0, 2 * math.pi)
        return pond_pt(a) + horiz(a) * rng.uniform(1.8, 4.5)
    if roll < near_pond + 0.2:
        return FOOT + horiz(rng.uniform(0, 2 * math.pi)) * rng.uniform(8.6, 14)
    return Vector((rng.uniform(-33, 33), rng.uniform(-33, 33), 0))


def prop(name, bm, *mats, sharp=None):  # a scenery mesh under the Props empty
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(name, me)
    ob.parent = bpy.data.objects['Props']
    for m in mats:
        me.materials.append(m)
    me.shade_smooth()
    if sharp:
        me.set_sharp_from_angle(angle=math.radians(sharp))
    return ob


# ---------- slot-cloud helpers ----------
DIRS = [Vector(d).normalized() for d in ((1, 0.37, 0.21), (-0.29, 1, 0.43), (0.31, -0.17, 1))]


def bvh_of(*obs, keep=None):  # keep: optional polygon filter
    vs, polys = [], []
    for ob in obs:
        assert ob.matrix_world == Matrix.Identity(4)  # local space == world space
        polys += [[i + len(vs) for i in p.vertices] for p in ob.data.polygons if keep is None or keep(p)]
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


def inside(p, bvhs, margin):  # in one of the closed meshes, at least margin deep
    # both tests must agree: decimating the floret-covered shells folds a few triangles, fooling either alone
    return any(normal_inside(b, p, margin) and parity_inside(b, p) for b in bvhs)


def clear(p, bvhs, margin):  # outside every mesh, at least margin from its surface
    return all(b.find_nearest(p)[3] >= margin and not parity_inside(b, p) for b in bvhs)


def sample(obs, count, ok, zlo=None, zhi=None, tries=None):  # uniform rejection sampling in the objects' box
    vs = [v.co for ob in obs for v in ob.data.vertices]
    lo = Vector([min(v[i] for v in vs) for i in range(3)])
    hi = Vector([max(v[i] for v in vs) for i in range(3)])
    lo.z, hi.z = lo.z if zlo is None else zlo, hi.z if zhi is None else zhi
    out, n = [], 0
    while len(out) < count and n != tries:
        n += 1
        p = Vector([rng.uniform(lo[i], hi[i]) for i in range(3)])
        if ok(p):
            out.append(p)
    return out


def finish(name, colours, trunk, shells, blossoms, tips, root, rocks=(), pebbles=22, mounds=16, tufts=60, clumps=10,
           lotus=2, extras=None):
    """Base, props, slot cloud, self-checks and export. tips / root (centre of the root flare) are tree-local;
    colours maps every scenery material name to hex sRGB; rocks are extra (centre, radius) boulders; extras() adds
    season props (closed meshes only: open ones fool the lawn's parity test) after the flowers."""
    global FOOT
    glb_path = os.path.join(ROOT, 'public', 'models', name + '.glb')
    slots_path = os.path.join(ROOT, 'public', 'trees', name + '.json')
    tag = name.upper()
    tips = [t + TREE for t in tips]

    def mat(n, rough=0.8):
        return material(n, colours[n], rough)

    # ---------- base: moss-topped slab over an inset stone tier, pond basin cut into the top ----------
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
    for m in (mat('Moss'), mat('Stone'), mat('PondBed'), mat('StoneChunk')):
        base.data.materials.append(m)
    base.data.shade_smooth()
    base.data.set_sharp_from_angle(angle=math.radians(40))

    # ---------- props: everything under one Props empty, merged into a few meshes ----------
    props = bpy.data.objects.new('Props', None)
    bpy.context.scene.collection.objects.link(props)
    FOOT = TREE + Vector((root.x, root.y, 0))

    # pond: earthen rim bank and rim stones; the hole's edge hides under the water and the bank
    bm = bmesh.new()
    tube(bm, 0, [pond_pt(2 * math.pi * k / 96, 1.02, -0.25) for k in range(96)], 0.7, sides=8, closed=True)
    for k in range(30):
        a = 2 * math.pi * (k + rng.uniform(-0.3, 0.3)) / 30
        p = pond_pt(a, 1.0, 0.1) + horiz(a) * 0.5
        if bridge_dist(p) > 3.0:
            blob(bm, 1 + rng.randrange(2), p, rng.uniform(0.5, 0.95), (1.3, 1.0, 0.6), rough=0.25,
                 yaw=rng.uniform(0, 6.3))
    prop('Pond', bm, mat('PondBank'), mat('RimStone'), mat('RimStoneLight'))

    bm = bmesh.new()
    fan(bm, 0, POND + Z * 0.04, [pond_pt(2 * math.pi * k / 96, 1.04, 0.04) for k in range(97)])
    water_mat = mat('Water', rough=0.1)
    water_mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.7
    water_mat.surface_render_method = 'BLENDED'
    water = prop('Water', bm, water_mat)

    # lily pads with a notch, the first `lotus` carrying a lotus; above the water's bob (+-0.05)
    centre_mat = mat('FlowerCentre')
    bm, pads = bmesh.new(), []
    while len(pads) < 4:
        p = POND + Vector((rng.uniform(-8, 8), rng.uniform(-6, 6), 0))
        if pond_gap(p) < -1.8 and bridge_dist(p) > 3.6 and all((p - q).length > 3 for q in pads):
            pads.append(p)
    for i, p in enumerate(pads):
        r, notch, a0 = rng.uniform(1.0, 1.5), math.radians(rng.uniform(25, 45)), rng.uniform(0, 2 * math.pi)
        fan(bm, 0, p + Z * 0.18, [p + horiz(a0 + notch / 2 + (2 * math.pi - notch) * k / 16) * r + Z * 0.14
                                  for k in range(17)])
        if i < lotus:  # lotus: two rings of petals round a yellow seed head
            c = p + Z * 0.15 + horiz(a0 + math.pi) * r * 0.2
            for n, tilt, ln, off in ((8, 62, 0.95, 0.15), (6, 28, 0.85, 0.08)):
                for k in range(n):
                    th = 2 * math.pi * (k + 0.5 * (n == 6)) / n
                    d = horiz(th) * math.sin(math.radians(tilt)) + Z * math.cos(math.radians(tilt))
                    w = horiz(th + math.pi / 2)
                    prim(bm, 'icosphere', 1, frame(c + horiz(th) * off + d * ln * 0.5, w * 0.3, d.cross(w) * 0.12,
                                                   d * ln * 0.5), subdivisions=2, radius=1.0)
            blob(bm, 2, c + Z * 0.25, 1.0, (0.22, 0.22, 0.14), sub=1)
    prop('LilyPads', bm, *((mat('LilyPad'), mat('Lotus'), centre_mat) if lotus else (mat('LilyPad'),)))

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
    prop('Bridge', bm, mat('Wood'), mat('WoodDark'), sharp=65)

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
    glow = mat('LanternGlow')
    glow.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = srgb('ffcf7a')
    glow.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.6
    prop('Lantern', bm, mat('LanternStone'), glow, sharp=40)

    # rocks round the pond and in the corners, plus pebbles
    ROCKS = [(pond_pt(math.radians(a)) + horiz(math.radians(a)) * gap, r) for a, gap, r in
             ((10, 2.6, 2.6), (120, 2.2, 1.8), (165, 2.0, 1.4), (290, 2.4, 1.9))]
    ROCKS += [(Vector(p), r) for p, r in (((29, -29, 0), 2.4), ((-28, -29, 0), 1.7), ((28, 28, 0), 2.0),
                                           ((-30, 27, 0), 2.8), ((-3.5, 15, 0), 1.5), ((-22, -2, 0), 1.2),
                                           ((20, 17, 0), 1.8), ((23.5, 15, 0), 1.0)) + tuple(rocks)]
    bm = bmesh.new()
    for p, r in ROCKS:
        blob(bm, rng.randrange(2), p + Z * r * 0.15, r, (1.2, 0.95, 0.65), sub=3, rough=0.18, yaw=rng.uniform(0, 6.3))
    count = 0
    while count < pebbles:
        p = ground_pt(0.5)
        if open_ground(p, -0.5):
            count += 1
            r = rng.uniform(0.25, 0.5)
            blob(bm, rng.randrange(2), p + Z * r * 0.1, r, (1.2, 1.0, 0.6), sub=2, rough=0.2, yaw=rng.uniform(0, 6.3))
    prop('Rocks', bm, mat('RockGrey'), mat('RockPink'))

    # grass tufts: fans of three-sided blades, over low moss mounds that break up the flat lawn
    bm, n_tufts, n_mounds = bmesh.new(), 0, 0
    while n_mounds < mounds:
        p, r = ground_pt(0.2), rng.uniform(1.5, 3.5)
        if open_ground(p, r):
            n_mounds += 1
            blob(bm, 2 + n_mounds % 2, p, r, (1.0, 0.8, 0.3), sub=3, rough=0.1, yaw=rng.uniform(0, 6.3))
    while n_tufts < tufts:
        p = ground_pt(0.3)
        if not open_ground(p, 0):
            continue
        n_tufts += 1
        mi = rng.randrange(2)
        for _ in range(rng.randint(7, 11)):
            phi, tilt, h = rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(5, 38)), rng.uniform(1.4, 2.8)
            b = p + horiz(phi) * rng.uniform(0, 0.6) - Z * 0.1
            rod(bm, mi, b, b + (horiz(phi) * math.sin(tilt) + Z * math.cos(tilt)) * h, 0.24, 0.0, seg=3, cap=False)
    prop('Grass', bm, mat('GrassDark'), mat('GrassLight'), mat('MossDark'), mat('MossLight'))

    # flowers in small clumps: five-petal heads on stems, in two colours
    bm, n_clumps = bmesh.new(), 0
    while n_clumps < clumps:
        p = ground_pt(0.4)
        if not open_ground(p, 0.8):
            continue
        n_clumps += 1
        for _ in range(rng.randint(3, 4)):
            b = p + horiz(rng.uniform(0, 2 * math.pi)) * rng.uniform(0, 1.2)
            top = b + Z * rng.uniform(1.0, 1.8) + horiz(rng.uniform(0, 2 * math.pi)) * 0.15
            rod(bm, 2, b - Z * 0.05, top, 0.07, 0.05, seg=4)
            a0 = rng.uniform(0, 2 * math.pi)
            for k in range(5):
                blob(bm, n_clumps % 2, top + horiz(a0 + k * 2 * math.pi / 5) * 0.3, 0.26, (1, 1, 0.6), sub=1)
            blob(bm, 3, top + Z * 0.08, 0.15, sub=1)
    prop('Flowers', bm, mat('FlowerWhite'), mat('FlowerLavender'), mat('Stem'), centre_mat)
    if extras:
        extras()

    # ---------- slot cloud: rejection-sample inside the volumes ----------
    # public/trees/<name>.json: {"name": name, "slots": [[x, y, z, p], ...]}, GLB space (Y up), 2 decimals.
    # The final QR is a mosaic of the scene: light modules and the quiet zone take lawn slots (p = 4), dark modules
    # take the rest and keep a deep version of their source colour. Classes p:
    #   0 trunk/branches          (inside Trunk, >= 0.3 deep, above the soil)
    #   1-3 canopy deep..pale     (inside a canopy shell, >= 0.6 deep; 1 lower/inner, 3 upper/outer)
    #   4 lawn                    (inside Base, y in [-2.2, -0.6], >= 0.6 deep, >= 1.0 from the pond basin,
    #                              >= 0.5 clear of the trunk and every prop)
    #   5 wood                    (inside Bridge, >= 0.5 deep, y >= 0.5)
    #   6 stone                   (inside Lantern or Rocks, >= 0.5 deep, y >= 0.5)
    #   7 pond water              (in the basin under Water, >= 0.5 from the surface, the bed and every prop)
    # A prop class with no room at its margin gets no slots and its share goes to the canopy (the bridge's
    # planks, rails and posts are all under 0.5 thick, so p = 5 is empty today). One seeded shuffle over all
    # slots, stratified by class, so every prefix keeps the class proportions.
    N_LAWN, N_SOLID = 3000, 2000
    SHARES = {0: 0.08, 5: 0.08, 6: 0.10, 7: 0.04}  # of N_SOLID; the canopy (~70%) takes the rest
    MARGIN_PROP, MARGIN_LAWN, POND_CLEAR = 0.5, 0.6, 1.0

    bvh_t, bvh_b = [bvh_of(trunk)], [bvh_of(ob) for ob in shells]
    for ob in shells:
        bpy.data.objects.remove(ob)
    for t in tips:  # every branch must end buried in a canopy cluster
        assert any(parity_inside(b, t) and b.find_nearest(t)[3] > 1.0 for b in bvh_b), ('bare branch tip', t)
    prop_obs = list(props.children)
    solid = [bvh_of(*[ob for ob in prop_obs if ob != water])]
    bvh_bed, bvh_chunk, bvh_water = (bvh_of(base, keep=lambda f: f.material_index == 2),
                                     bvh_of(base, keep=lambda f: f.material_index == 3), bvh_of(water))
    # the upper slab only: the lower tier's top (z = -3.1) and the chunks sit inside it, and those hidden faces would
    # be the nearest surface for lawn slots below z = -1.55, fooling the closest-point test (rays all point up, so
    # parity never sees the dropped faces)
    bvh_base = bvh_of(base, keep=lambda f: f.center.z > -3.0)
    WOOD, STONE = [bpy.data.objects['Bridge']], [bpy.data.objects['Lantern'], bpy.data.objects['Rocks']]
    bvh_wood, bvh_stone = [bvh_of(ob) for ob in WOOD], [bvh_of(ob) for ob in STONE]

    def rules(e):  # class -> slot test; e loosens the margins to re-test the rounded slots
        r = {0: lambda p: p.z >= 0.3 - e and inside(p, bvh_t, MARGIN_TRUNK - e),  # only above the soil
             1: lambda p: inside(p, bvh_b, MARGIN_BLOSSOM - e),
             4: lambda p: (-2.2 - e <= p.z <= -0.6 + e and pond_gap(p) > POND_CLEAR - e  # not under the basin
                           and bvh_bed.find_nearest(p)[3] >= POND_CLEAR - e and inside(p, [bvh_base], MARGIN_LAWN - e)
                           and clear(p, solid + bvh_t, MARGIN_PROP - e)),
             5: lambda p: p.z >= 0.5 - e and inside(p, bvh_wood, MARGIN_PROP - e),  # tile clear of the lawn
             6: lambda p: p.z >= 0.5 - e and inside(p, bvh_stone, MARGIN_PROP - e),
             7: lambda p: (pond_gap(p) < 0 and bvh_water.ray_cast(p, Z)[0] is not None  # under the surface
                           and bvh_water.find_nearest(p)[3] >= MARGIN_PROP - e
                           and clear(p, [bvh_base] + solid, MARGIN_PROP - e))}  # above the bed, off piers and bank
        r[2] = r[3] = r[1]
        return r

    RULE, want = rules(0.0), {c: round(N_SOLID * s) for c, s in SHARES.items()}
    # shortcut: a prop class with nothing found in 1e6 tries counts as having no room; partial fills fail the check below
    pts = {0: sample([trunk], want[0], RULE[0], zlo=0.3),
           5: sample(WOOD, want[5], RULE[5], zlo=0.5, tries=10 ** 6),
           6: sample(STONE, want[6], RULE[6], zlo=0.5, tries=10 ** 6),
           7: sample([water], want[7], RULE[7], zlo=-1.7, zhi=0.0, tries=10 ** 6)}
    bloom_pts = sample([blossoms], N_SOLID - sum(map(len, pts.values())), RULE[1])
    pts[4] = sample([base], N_LAWN, RULE[4], zlo=-2.2, zhi=-0.6)

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
    for p, s in zip(bloom_pts, shade):
        pts.setdefault(s, []).append(p)

    # one seeded shuffle, stratified: class c's i-th slot (already in random order) gets key (i + u) / n_c, so any
    # prefix keeps the class proportions and covers each volume evenly (plan §3.2)
    keyed = sorted(((i + rng.random()) / len(ps), c, p) for c, ps in pts.items() for i, p in enumerate(ps))
    out = [[round(p.x, 2) + 0.0, round(p.z, 2) + 0.0, round(-p.y, 2) + 0.0, c] for _, c, p in keyed]
    os.makedirs(os.path.dirname(slots_path), exist_ok=True)
    with open(slots_path, 'w') as f:
        json.dump({'name': name, 'slots': out}, f, separators=(',', ':'))

    # self-check: every rounded slot passes its class test again, plus the cross-mesh exclusions
    R, tree = rules(0.02), bvh_t + bvh_b
    for x, y, z, c in out:
        p = Vector((x, -z, y))
        assert R[c](p), ('slot fails its class test', x, y, z, c)
        # not bvh_of(all props): Water is an open disc, and slanted rays from the lawn beside the pond cross it
        assert clear(p, solid, 0.3) if c <= 4 else clear(p, tree, 0.0), ('slot inside another mesh', x, y, z, c)
        assert c != 4 or clear(p, [bvh_chunk], MARGIN_PROP), ('lawn slot in a rock chunk', x, y, z)

    # self-check: counts, shares and prefixes (the v10 grid needs about 1,650 dark and 2,575 light cells)
    P = [c for *_, c in out]
    n = {c: P.count(c) for c in range(8)}
    dark = len(P) - n[4]
    assert n[4] >= N_LAWN >= 2700 and dark >= N_SOLID >= 1700, n
    assert n[0] == want[0] and n[6] == want[6] and n[5] in (0, want[5]) and n[7] in (0, want[7]), (n, want)
    assert all(abs(n[s] - share * (n[1] + n[2] + n[3])) <= 1 for s, share in ((1, 0.3), (2, 0.4), (3, 0.3))), n
    for T in (1089, 2025, 4225):
        for c in range(8):
            assert abs(P[:T].count(c) / T - n[c] / len(P)) < 0.02, ('prefix loses the class mix', T, c)
    for c in range(8):
        ys = [y for _, y, _, s in out if s == c]
        print(tag, 'class', c, n[c], f'{100 * n[c] / len(P):.1f}% of all',
              '' if c == 4 else f'{100 * n[c] / dark:.1f}% of non-lawn', (min(ys), max(ys)) if ys else 'empty')

    # self-check: the props and base contracts
    for ob in prop_obs:
        vs = [v.co for v in ob.data.vertices]
        assert all(max(abs(v.x), abs(v.y)) <= 36 and -2 <= v.z <= 14 for v in vs), ('prop outside the base', ob.name)
        assert min((flat(v) - flat(FOOT)).length for v in vs) > 7, ('prop in the trunk area', ob.name)
    assert [m.name for m in water.data.materials] == ['Water'] and all(0 <= v.co.z <= 0.1 for v in water.data.vertices)
    bv = [v.co for v in base.data.vertices]
    assert max(v.z for v in bv) <= 1e-4 and min(v.z for v in bv) >= -8 and max(max(abs(v.x), abs(v.y)) for v in bv) <= 36

    # ---------- export ----------
    for ob in bpy.context.scene.objects:
        ob.select_set(ob.name in ('Trunk', 'Blossoms', 'Base', 'Props') or ob.parent == props)
    os.makedirs(os.path.dirname(glb_path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB', export_apply=True, export_yup=True,
                              use_selection=True, export_materials='EXPORT', export_normals=True,
                              export_texcoords=False, export_extras=False)

    # self-check the exported file: Props subtree, Water the only blended material, size and triangle budgets
    with open(glb_path, 'rb') as f:
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

    print(tag, 'tris', counts, 'total', sum(counts.values()))
    print(tag, 'glb bytes', len(glb))
    print(tag, 'slots', len(out), n)
