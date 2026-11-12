"""Build the winter diorama: public/models/winter.glb + public/trees/winter.json.

Run from the repo root: npm run tree:build (Blender 5.2, headless). Deterministic (fixed SEED).
This file is the season: a bare old zelkova under fresh snow (ridges along the tops of its limbs, piles in the forks,
loads caught in the twig brooms at the branch ends, a few icicles) in a quiet Japanese garden: a half-frozen pond
with dark open water under the vermilion bridge, a snow-viewing lantern (yukimi-doro) glowing by the water, a kamakura
snow hut lit from inside, a niwaki pine under its yukitsuri rope tent, a bamboo fence, stepping stones and red
camellias. The base, props, slot cloud, self-checks and export are shared with the other seasons in diorama.py.
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
    'Moss': 'eef2f7', 'Stone': '8a8f99', 'PondBed': '1f3341', 'StoneChunk': '6c717b',
    'PondBank': 'dde4ed', 'RimStone': '7f848c', 'RimStoneLight': 'a3a8b0', 'Water': '2b4658',
    'FlowerCentre': 'f2c84b', 'LilyPad': 'e1ecf2', 'Wood': 'a8432f', 'WoodDark': '742c20',
    'RockGrey': '6f747c', 'RockPink': '8a8f97',
    'GrassDark': 'a49c7e', 'GrassLight': 'c8bf9c', 'MossDark': 'f3f6fa', 'MossLight': 'f8fafd',
    'FlowerWhite': 'f6f3e8', 'FlowerLavender': 'c23a45', 'Stem': '50683a',
}  # Water: dark open water; LilyPad: floes of snow on it; FlowerWhite / FlowerLavender: narcissus and camellia
# canopy, deep to pale; the brightest is tinted: a near-pure white has full HSL saturation, so derives to a vivid blue
SNOW = [('Snow_Shadow', 'c3d0e2'), ('Snow', 'e4ebf4'), ('Snow_Bright', 'f6f9fc')]
LIGHT = Vector((60, -40, 90)).normalized()  # preview.py's key light: the bright snow leans toward it
LH = Vector((LIGHT.x, LIGHT.y, 0)).normalized()

# ---------- trunk and limbs: strands wind up a stout trunk, then splay into wide limbs that level out and rise ----------
SPLIT = Vector((1.0, -0.5, 11.5))
TWIST = math.radians(150)


def axis(t):
    return bez(Vector((0, 0, -1.5)), Vector((-3.5, 2.0, 5.0)), Vector((4.5, -2.5, 8.5)), SPLIT, t)


MAIN = [  # azimuth deg, horizontal reach from the split, tip height, start / end elevation deg, end-load size
    (10, 21.0, 25.0, 30, 8, 2.6),  # the long low limb reaching out toward the pond
    (70, 15.0, 30.0, 40, 12, 2.4),
    (130, 18.0, 27.0, 32, 10, 2.5),
    (190, 16.0, 29.0, 38, 12, 2.4),
    (250, 15.0, 26.0, 32, 8, 2.3),
    (310, 17.0, 29.0, 36, 10, 2.4),
    (40, 8.0, 34.5, 72, 10, 2.5),  # leader, arching over at the top
]  # limbs climb steeply out of the fork, then level off: the loads lie along level ends
splines, twig_splines, icicles, tips, snow_el = [], [], [], [], []  # snow_el: (centre, along, a, b, h) ellipsoids


def heading(pts, k):  # unnormalised tangent over a few points
    return pts[min(k + 3, len(pts) - 1)] - pts[max(k - 3, 0)]


def flat_dir(v):
    return Vector((v.x, v.y, 0)).normalized() if v.xy.length > 1e-6 else Vector((1, 0, 0))


def level(t):  # 1 on a level stretch of branch, 0 where it climbs steeply: snow only lies where it can
    return max(0.0, min(1.0, (0.92 - abs(t.normalized().z)) / 0.55))


def end_load(pts, R):  # snow loaded along a branch's last stretch: a long low pillow, deepest at the end
    n = len(pts)
    k0 = int(n * 0.72)
    for k in range(k0, n):
        u, f = (k - k0) / max(1, n - 1 - k0), level(heading(pts, k))
        if f > 0.5:
            hh = R * lerp(0.4, 0.62, u) * (0.4 + 0.6 * f)
            snow_el.append((pts[k] + Z * 0.2 * hh, flat_dir(heading(pts, k)), 0.9, R * lerp(0.5, 0.72, u), hh))
    d = flat_dir(heading(pts, n - 1))
    snow_el.append((pts[-1] + d * 0.5 + Z * 0.12 * R, d, 0.8 * R, 0.66 * R, 0.55 * R))  # the rounded end


limbs = []
for i, (az_deg, reach, tip_z, e1, e2, R) in enumerate(MAIN):
    az = math.radians(az_deg)
    pts, rad = [], []
    for k in range(33):
        t = k / 32
        q = axis(t) + horiz(az - TWIST + TWIST * t) * lerp(2.4, 1.0, t)
        pts.append(q + noise.noise_vector(q * 0.3 + Vector((i * 3.7, 0, 0))) * 0.4 * math.sin(math.pi * t))
        rad.append(lerp(1.9, 1.3, t))
    p0 = pts[-1]
    tip = SPLIT + horiz(az) * reach
    tip.z = tip_z
    L, h = (tip - p0).length, horiz(az)
    e1, e2 = math.radians(e1), math.radians(e2)
    bp, br = wobbly(p0, p0 + (h * math.cos(e1) + Z * math.sin(e1)) * L * 0.38,
                    tip - (h * math.cos(e2) + Z * math.sin(e2)) * L * 0.35, tip, 1.3, 0.42, 1.6, i)
    splines.append((pts + bp, rad + br))
    limbs.append((bp, br))
    end_load(bp, R)
    tips.append(tip)  # the limb ends lie > 1.0 deep in their loads

branches = list(limbs)  # every limb and side branch: they carry the ridges of snow and the twigs
for i, (bp, br) in enumerate(limbs):
    for j, at in enumerate((0.36, 0.6, 0.82)):
        k = int(at * (len(bp) - 1))
        p0, r0 = bp[k], br[k] * 0.72
        hd = flat_dir(heading(bp, k))
        a = math.atan2(hd.y, hd.x) + (1 if (i + j) % 2 else -1) * math.radians(rng.uniform(40, 65))
        length, rise = rng.uniform(6.0, 9.0) * (0.75 if j == 2 else 1.0), rng.uniform(2.5, 5.0)
        tip = p0 + horiz(a) * length + Z * rise
        pts, rad = wobbly(p0, p0 + horiz(a) * length * 0.3 + Z * rise * 0.55,
                          tip - horiz(a) * length * 0.35 - Z * rise * 0.05, tip, r0, 0.3, 0.7, 10 + 3 * i + j)
        splines.append(([p0] + pts, [r0] + rad))
        branches.append((pts, rad))
        end_load(pts, rng.uniform(1.2, 1.5))  # a lighter load; the side branch ends are left out of the tip check
        snow_el.append((p0 + Z * br[k] * 0.85, hd, br[k] * 1.7, br[k] * 1.4, br[k] * 0.7 + 0.35))  # piled in the fork

snow_el.append((SPLIT + Z * 0.9, Vector((1, 0, 0)), 3.2, 3.2, 1.5))  # the main crotch

for n, (pts, rad) in enumerate(branches):  # ridges along the tops, thickest where the branch runs level
    for k in range(len(pts)):
        t = heading(pts, k)
        f = level(t)
        if f > 0.08:
            r = rad[k]
            snow_el.append((pts[k] + Z * r * 0.62, flat_dir(t), 0.75, (r + 0.22) * (0.6 + 0.4 * f),
                            (0.32 + 0.55 * r) * f + 0.05))
            if f > 0.6 and r > 0.7 and pts[k].z < 27 and k % 3 == 0 and rng.random() < 0.45:
                icicles.append((pts[k] - Z * r * 0.8, rng.uniform(0.7, 2.0), rng.uniform(0.13, 0.2)))


def twig(q, d, length, r0, key):
    end = q + d * length
    pts, rad = wobbly(q, q + d * length * 0.35, end - d * length * 0.3 + Z * length * 0.1, end, r0, 0.09, 0.25, key)
    twig_splines.append(([q] + pts, [r0] + rad))
    return pts


for n, (pts, rad) in enumerate(branches):  # brooms of bare twigs, mostly toward and out of the branch ends
    count, (lo, hi) = (10, (4.0, 7.0)) if n < len(limbs) else (7, (3.0, 5.5))
    for j in range(count):
        u = lerp(0.3, 1.0, (j + rng.random()) / count) if j < count - 3 else 1.0
        k = min(int(u * (len(pts) - 1)), len(pts) - 1)
        hd = flat_dir(heading(pts, k))
        a = math.atan2(hd.y, hd.x) + rng.choice((-1, 1)) * math.radians(rng.uniform(5, 65))
        d = (horiz(a) + Z * rng.uniform(0.3, 1.1)).normalized()
        tp = twig(pts[k], d, rng.uniform(lo, hi), min(0.24, rad[k] * 0.8), 100 + 10 * n + j)
        if rng.random() < 0.6:  # a side twig off it
            d2 = (d + horiz(a + rng.choice((-1, 1)) * 1.1) * 0.8 + Z * 0.3).normalized()
            twig(tp[len(tp) // 2], d2, rng.uniform(1.4, 2.6), 0.15, 500 + 10 * n + j)

splines.append(([axis(k / 32) for k in range(33)], [lerp(2.2, 1.3, k / 32) for k in range(33)]))  # solid core
a0 = axis(0.2)
for k in range(6):  # nebari: a root flare sinking into the snow
    phi = math.radians(k * 60 + 15 + rng.uniform(-12, 12))
    a = a0 + horiz(phi) * 1.0
    c = Vector((a0.x, a0.y, -1.0)) + horiz(phi) * rng.uniform(5.0, 6.8)
    pts, rad = wobbly(a, a + horiz(phi) * 1.5 - Z * 1.2, c - horiz(phi) * 2 + Z * 0.5, c, 1.5, 0.35, 0.3, 20 + k)
    splines.append(([a] + pts, [1.5] + rad))


def curve_mesh(name, splines, voxel, smooth, budget):  # as D.trunk_mesh: bevelled splines, unioned and decimated
    cu = bpy.data.curves.new(name + 'Curve', 'CURVE')
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution, cu.use_fill_caps = '3D', 1.0, 4, True
    for pts, rad in splines:
        sp = cu.splines.new('POLY')
        sp.points.add(len(pts) - 1)
        for p, co, r in zip(sp.points, pts, rad):
            p.co, p.radius = (co.x, co.y, co.z, 1.0), r
    cob = bpy.data.objects.new(name + 'Curve', cu)
    bpy.context.scene.collection.objects.link(cob)
    ob = D.link(name, bpy.data.meshes.new_from_object(cob.evaluated_get(bpy.context.evaluated_depsgraph_get())))
    bpy.data.objects.remove(cob)
    D.voxel_union(ob, voxel)
    D.smooth_decimate(ob, smooth, budget / D.tris(ob.data))
    return ob


# Trunk: the wood (bark first and dominant) and the icicles hanging under the level limbs, one mesh in world space
bm = bmesh.new()
for ob in (curve_mesh('Wood', splines, 0.22, 6, 26000), curve_mesh('Twigs', twig_splines, 0.08, 2, 18000)):
    bm.from_mesh(ob.data)
    bpy.data.objects.remove(ob)
for p, length, r in icicles:
    D.rod(bm, 1, p + Z * 0.3, p - Z * length, r, 0.0, seg=5)
me = bpy.data.meshes.new('Trunk')
bm.to_mesh(me)
bm.free()
trunk = D.link('Trunk', me)
trunk.data.transform(Matrix.Translation(D.TREE))
for n, h in (('Bark', '3a2f2b'), ('Icicle', 'd5e7f2')):
    trunk.data.materials.append(D.material(n, h, 0.3 if n == 'Icicle' else 0.8))
trunk.data.shade_smooth()

# ---------- snow: every ellipsoid in three offset layers, one voxel-unioned shell per shade ----------
# where a layer pokes out of the others it shows: the shadow below, the bright on top toward the light
LAYERS = [(-0.25, 0.0, 0.97), (0.0, 0.0, 1.0), (0.24, 0.08, 0.93)]  # (up, toward the light) in radii, scale
shells = []
for i, (up, lit, sc) in enumerate(LAYERS):
    bm = bmesh.new()
    for c, d, a, b, h in snow_el:
        c = c + Z * up * h + LH * lit * a
        bmesh.ops.create_icosphere(bm, subdivisions=3 if max(a, b) > 1.2 else 2, radius=1.0,
                                   matrix=D.frame(c, d * a * sc, Z.cross(d) * b * sc, Z * h * sc))
    me = bpy.data.meshes.new('shell')
    bm.to_mesh(me)
    bm.free()
    shells.append(D.link(f'SnowShell{i}', me))
    D.voxel_union(shells[-1], 0.2)
    for v in shells[-1].data.vertices:  # each layer its own noise, so the shade boundaries wander
        v.co += v.normal * 0.08 * noise.noise(v.co * 0.5 + Vector((7.3 * i, 0, 0)))
blossoms = D.canopy_mesh(shells, [D.material(n, h) for n, h in SNOW], 65000)

# ---------- the garden ----------
LANTERN = Vector((1.0, -20.5, 0.0))  # yukimi-doro where the stepping stones meet the bridge, clear of its arch
KAMAKURA, KAMA_DOOR = Vector((-20.0, -18.0, 0.0)), math.radians(-37)  # the door faces the camera
PINES = [(Vector((15.0, 23.0, 0.0)), 1.0, True), (Vector((-27.0, -6.0, 0.0)), 0.75, False)]  # niwaki; yukitsuri?
FENCE = (Vector((-2.0, 32.5, 0.0)), Vector((31.0, 32.5, 0.0)))
CAMELLIAS = [(Vector((-10.5, -23.0, 0.0)), 1.0), (Vector((-2.0, -5.0, 0.0)), 0.85), (Vector((25.0, -22.0, 0.0)), 0.9)]
KARIKOMI = [(Vector((30.0, 3.0, 0.0)), 2.6), (Vector((27.0, 8.5, 0.0)), 2.0), (Vector((32.0, 9.5, 0.0)), 1.6)]
STEPS = [lerp(Vector((-14.0, -13.5, 0.0)), Vector((3.5, -15.5, 0.0)), k / 6) + Vector((0, 0.5 * (-1) ** k, 0))
         for k in range(7)]
ZONES = ([(LANTERN, 4.5), (KAMAKURA, 7.5)] + [(p, r * 1.4 + 0.5) for p, r in KARIKOMI] + [(p, 6.5 * s) for p, s, _ in PINES] + [(p, 3.2 * s) for p, s in CAMELLIAS]
         + [(p, 1.8) for p in STEPS])


def fence_dist(p):
    a, b = FENCE
    d = (b - a).normalized()
    return (D.flat(p - a) - D.flat(d) * max(0.0, min((b - a).length, (p - a).dot(d)))).length


def keep_clear(p, pad):
    return fence_dist(p) < 1.5 + pad or any(D.flat(p - c).length < r + pad for c, r in ZONES)


def glow(name, hexrgb, strength):
    m = D.material(name, hexrgb)
    m.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = D.srgb(hexrgb)
    m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = strength
    return m


def prism(bm, mi, outline, o, U, V, W, depth):  # a closed slab: outline [(u, v)] in the U, V plane, extruded by W
    front = [bm.verts.new(o + U * u + V * v) for u, v in outline]
    back = [bm.verts.new(o + U * u + V * v + W * depth) for u, v in outline]
    faces = [bm.faces.new(front), bm.faces.new(back[::-1])]
    n = len(outline)
    faces += [bm.faces.new((front[k], back[k], back[(k + 1) % n], front[(k + 1) % n])) for k in range(n)]
    for f in faces:
        f.material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=faces)


def arch(hw, hs, seg=10):  # doorway outline: straight sides hs tall, a round head of radius hw
    return ([(hw, 0.0)] + [(hw * math.cos(math.pi * k / seg), hs + hw * math.sin(math.pi * k / seg))
                           for k in range(seg + 1)] + [(-hw, 0.0)])


def snow_copy(bm, first, push=0.42, tuck=0.12):  # the verts from `first` on become a snow cap over the rest
    bm.normal_update()
    for v in list(bm.verts)[first:]:
        v.co += v.normal * (push * max(0.0, v.normal.z) ** 1.5 - tuck)


def deck_pt(s):  # the bridge's deck line, as in diorama.finish
    return D.B0 + D.BDIR * s + Z * (0.25 + D.H_BR * math.sin(math.pi * s / D.L_BR))


def extras():
    snow_mat, stone = D.material('SnowCap', 'f4f7fb'), D.material('LanternStone', '9fa3aa')
    ice_mat = D.material('Ice', 'd5e7f2', 0.25)

    # snow on the bridge deck and rails, and caps on the boulders
    bm = bmesh.new()
    for k in range(31):
        s = D.L_BR * k / 30
        t = (deck_pt(s + 0.01) - deck_pt(s - 0.01)).normalized()
        D.prim(bm, 'icosphere', 0, D.frame(deck_pt(s), t * 0.8, D.BSIDE * 1.5, t.cross(D.BSIDE) * 0.22),
               subdivisions=2, radius=1.0)
    for side in (-1, 1):
        D.tube(bm, 0, [deck_pt(D.L_BR * k / 40) + D.BSIDE * side * (D.W_BR / 2 - 0.15) + Z * 2.13 for k in range(41)],
               0.19, side=D.BSIDE, sides=8)
    first = len(bm.verts)
    bm.from_mesh(bpy.data.objects['Rocks'].data)
    snow_copy(bm, first, 0.45)
    for f in bm.faces:
        f.material_index = 0
    D.prop('Snow', bm, snow_mat)

    # the pond half frozen: shore ice, wide at the back and a thin rim at the front, round dark open water
    bm, K, front = bmesh.new(), 96, math.radians(-47)
    rings = []
    for z in (0.06, 0.13):
        outer, inner = [], []
        for k in range(K):
            a = 2 * math.pi * k / K
            s_in = 0.58 + 0.27 * math.cos(a - front) + 0.05 * math.sin(4 * a + 1)
            outer.append(bm.verts.new(D.pond_pt(a, 1.0, z)))
            inner.append(bm.verts.new(D.pond_pt(a, s_in, z)))
        rings.append((outer, inner))
    (ob, ib), (ot, it) = rings
    for k in range(K):
        k1 = (k + 1) % K
        for vs in ((ot[k], ot[k1], it[k1], it[k]), (ob[k1], ob[k], ib[k], ib[k1]), (ob[k], ob[k1], ot[k1], ot[k]),
                   (ib[k1], ib[k], it[k], it[k1])):
            bm.faces.new(vs)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for k in range(5):  # drifts of snow on the ice
        a = front + math.pi + rng.uniform(-1.3, 1.3)
        D.blob(bm, 1, D.pond_pt(a, rng.uniform(0.6, 0.8), 0.12), rng.uniform(1.0, 1.6), (1.5, 1.0, 0.14), sub=2,
               yaw=rng.uniform(0, 6.3))
    D.prop('Ice', bm, ice_mat, snow_mat)

    # yukimi-doro: three bowed legs, a glowing firebox, a very wide roof under a thick cushion of snow, icicles
    bm, P = bmesh.new(), LANTERN
    for k in range(3):
        h = horiz(math.radians(30 + 120 * k))
        D.tube(bm, 0, [bez(P + Z * 2.75 + h * 0.5, P + Z * 2.1 + h * 1.7, P + Z * 0.9 + h * 2.3, P + h * 2.5 - Z * 0.05,
                           t / 8) for t in range(9)], 0.33, side=Z.cross(h), sides=8)
    for z0, z1, r0, r1, mi in ((2.55, 3.1, 1.55, 1.4, 0), (3.1, 4.6, 1.0, 1.0, 1), (4.6, 4.85, 3.4, 3.6, 0),
                               (4.85, 6.0, 3.6, 0.5, 0)):
        D.prim(bm, 'cone', mi, Matrix.Translation(P + Z * ((z0 + z1) / 2)), segments=6, radius1=r0, radius2=r1,
               depth=z1 - z0, cap_ends=True)
    for k in range(6):
        c = P + horiz(k * math.pi / 3 + math.pi / 6) * 1.05
        D.rod(bm, 0, c + Z * 3.1, c + Z * 4.6, 0.2, 0.2, seg=4)
    D.blob(bm, 0, P + Z * 6.35, 0.55)
    D.blob(bm, 2, P + Z * 5.65, 3.75, (1, 1, 0.42), sub=3, rough=0.05)
    D.blob(bm, 2, P + Z * 6.75, 0.62, (1, 1, 0.6), sub=2)
    for k in range(12):
        c = P + horiz(k * math.pi / 6 + rng.uniform(-0.1, 0.1)) * 3.35 + Z * 4.65
        D.rod(bm, 3, c + Z * 0.1, c - Z * rng.uniform(0.5, 1.3), rng.uniform(0.1, 0.15), 0.0, seg=5)
    D.prop('SnowLantern', bm, stone, glow('LanternGlow', 'ffcf7a', 1.4), snow_mat, ice_mat, sharp=40)

    # kamakura: a lumpy snow dome, an arched entrance hood, candlelight in the doorway, drifts round its foot
    bm, P = bmesh.new(), KAMAKURA
    out = horiz(KAMA_DOOR)
    side = Z.cross(out)
    D.blob(bm, 0, P + Z * 0.3, 5.2, (1, 1, 1.0), sub=4, rough=0.04)
    prism(bm, 0, arch(1.85, 1.7), P + out * 3.3, side, Z, out, 2.95)
    prism(bm, 1, arch(1.2, 1.3), P + out * 6.2 + Z * 0.05, side, Z, out, 0.12)
    for k in range(8):
        a = KAMA_DOOR + math.radians(45 + 34 * k)
        D.blob(bm, 0, P + horiz(a) * rng.uniform(4.8, 5.4), rng.uniform(1.1, 1.6), (1.5, 1.0, 0.45), sub=2,
               yaw=a + math.pi / 2)
    for v in bm.verts:
        v.co.z = max(v.co.z, -0.1)
    D.prop('Kamakura', bm, D.material('KamakuraSnow', 'eef3f8'), glow('KamakuraGlow', 'ffb45e', 2.0), sharp=50)

    # niwaki pines: a leaning trunk, cloud-pruned pads under snow cushions; the big one under a yukitsuri rope tent
    bm = bmesh.new()
    for P, s, tent in PINES:
        lean = horiz(rng.uniform(0, 2 * math.pi))
        trunk_pts = [P + lean * 0.9 * s * math.sin(math.pi * t * 0.8) + Z * 8.0 * s * t for t in (k / 8 for k in range(9))]
        for k in range(8):
            D.rod(bm, 2, trunk_pts[k], trunk_pts[k + 1], lerp(0.6, 0.25, k / 8) * s, lerp(0.6, 0.25, (k + 1) / 8) * s,
                  seg=8)
        pads = [(3.0, 0.0, 3.4, 2.6), (4.3, 2.2, 2.9, 2.2), (5.6, 4.3, 2.6, 2.0), (6.9, 0.9, 2.0, 1.8),
                (8.2, 3.3, 0.0, 1.9)]  # height, azimuth, reach, size (x s)
        a0 = rng.uniform(0, 2 * math.pi)
        for z, az, reach, size in pads:
            base = trunk_pts[min(8, int(z / 8.0 * 8))]
            c = P + Z * z * s + horiz(a0 + az) * reach * s + lean * 0.5 * s
            D.rod(bm, 2, base, c, 0.22 * s, 0.14 * s, seg=6)
            D.blob(bm, 0, c, size * s, (1.0, 0.9, 0.42), sub=3, rough=0.12, yaw=a0 + az)
            D.blob(bm, 1, c + Z * size * s * 0.3, size * s * 0.93, (1.0, 0.9, 0.3), sub=3, rough=0.08, yaw=a0 + az)
        if tent:  # a pole above the crown, ropes fanning down to the outer pads
            top = P + Z * 13.4
            D.rod(bm, 2, P + lean * 0.4 - Z * 0.05, top, 0.17, 0.12, seg=6)
            D.blob(bm, 1, top + Z * 0.2, 0.32, sub=1)
            for k in range(26):
                anchor = P + horiz(2 * math.pi * k / 26) * 5.3 + Z * (3.4 + 0.4 * math.sin(3 * k))
                D.rod(bm, 3, top, anchor, 0.075, 0.075, seg=4)
    D.prop('Pines', bm, D.material('PineGreen', '2b4a35'), snow_mat, D.material('PineBark', '4a3a30'),
           D.material('Rope', 'd9c69a'))

    # bamboo fence (yotsume-gaki) along the back: posts, three rails, canes, black twine, snow on the rails
    bm = bmesh.new()
    a, b = FENCE
    d, length = (b - a).normalized(), (b - a).length
    n = Z.cross(d)
    for k in range(int(length / 4.4) + 1):
        p = a + d * (k * 4.4)
        D.rod(bm, 0, p - Z * 0.05, p + Z * 4.4, 0.32, 0.32, seg=8)
        D.blob(bm, 2, p + Z * 4.45, 0.38, (1, 1, 0.55), sub=1)
    for z in (1.3, 2.5, 3.6):
        D.rod(bm, 0, a + n * 0.32 + Z * z, b + n * 0.32 + Z * z, 0.16, 0.16, seg=6)
        D.tube(bm, 2, [a + n * 0.32 + Z * (z + 0.2) + d * (length * k / 20) for k in range(21)], 0.13, side=n, sides=6)
    for k in range(int(length / 0.8)):
        p = a + d * (0.4 + 0.8 * k)
        D.rod(bm, 0, p - Z * 0.05, p + Z * rng.uniform(3.85, 4.05), 0.13, 0.13, seg=5)
        for z in (1.3, 2.5, 3.6):
            if k % 3 == 0:
                D.blob(bm, 1, p + n * 0.32 + Z * z, 0.2, sub=1)
    D.prop('Fence', bm, D.material('Bamboo', 'b9a46b'), D.material('Twine', '2b2724'), snow_mat)

    # camellias: dark glossy bushes, red flowers, snow on top
    bm = bmesh.new()
    for P, s in CAMELLIAS:
        lobes = [(P + Z * 1.5 * s, 1.7 * s, 0.0)] + [(P + horiz(a) * 1.3 * s + Z * 1.0 * s, rng.uniform(1.1, 1.4) * s, a)
                                                     for a in (k * 1.57 + rng.uniform(-0.3, 0.3) for k in range(4))]
        for c, r, _ in lobes:
            for _ in range(3):
                dd = horiz(rng.uniform(0, 2 * math.pi)) * 0.9 + Z * rng.uniform(-0.1, 0.35)
                D.blob(bm, 1, c + dd.normalized() * r * 0.97, 0.3 * s, (1, 1, 0.7), sub=1)
        for mi in (0, 2):
            first = len(bm.verts)
            for c, r, a in lobes:
                D.blob(bm, mi, c, r, (1, 1, 0.85), sub=3, rough=0.15, yaw=a)
        snow_copy(bm, first, 0.4)
        for v in bm.verts:
            v.co.z = max(v.co.z, -0.1)
    D.prop('Camellias', bm, D.material('CamelliaLeaf', '24432f'), D.material('Camellia', 'c8283a'), snow_mat)

    # karikomi: clipped shrub mounds, dark green showing under heavy rounded snow
    bm = bmesh.new()
    for mi in (0, 1):
        first = len(bm.verts)
        for P, r in KARIKOMI:
            D.blob(bm, mi, P + Z * r * 0.35, r, (1.3, 1.05, 0.72), sub=3, rough=0.08, yaw=P.x)
    snow_copy(bm, first, 0.6, 0.1)
    for v in bm.verts:
        v.co.z = max(v.co.z, -0.1)
    D.prop('Karikomi', bm, D.material('KarikomiGreen', '2a4a33'), snow_mat)

    # stepping stones from the kamakura toward the bridge, each under a thin cap of snow
    bm = bmesh.new()
    for p in STEPS:
        r, yaw = rng.uniform(1.1, 1.35), rng.uniform(0, 6.3)
        D.blob(bm, 0, p + Z * 0.08, r, (1.25, 1.0, 0.3), sub=2, rough=0.12, yaw=yaw)
        D.blob(bm, 1, p + Z * 0.24, r * 0.86, (1.25, 1.0, 0.2), sub=2, rough=0.08, yaw=yaw)
    D.prop('Steps', bm, D.material('StepStone', '5f636b'), snow_mat)


D.finish('winter', COLOURS, trunk, shells, blossoms, tips, a0, pebbles=0, mounds=16, tufts=10, clumps=4, lotus=0,
         extras=extras, lantern=False, keep_clear=keep_clear)
