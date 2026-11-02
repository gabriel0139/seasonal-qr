"""Build the autumn diorama: public/models/autumn.glb + public/trees/autumn.json.

Run from the repo root: npm run tree:build (Blender 5.2, headless). Deterministic (fixed SEED).
This file is the season: a leaning Japanese maple in full red, with flat tiered pads of fine foliage, dry grass and
fallen leaves. The base, props, slot cloud, self-checks and export are shared with the other seasons in diorama.py.
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
LEAVES = [('Crimson', 'a8241c'), ('Red', 'cc3a22'), ('Orange', 'e0612b'), ('Amber', 'eb9a3a')]  # canopy, deep to pale

# ---------- trunk: a fluted stem leaning right, turning upright near the top; branches go out level, dip, rise ----------
LEAN = horiz(math.radians(20))  # screen right and a little towards the camera


def axis(t):
    return bez(Vector((0, 0, -1.5)), LEAN * 3.5 + Z * 6, LEAN * 13 + Z * 15, LEAN * 14 + Z * 24, t)


def trunk_r(t):
    return lerp(2.6, 1.1, t)


splines, pads, tips = [], [], []  # pads: (centre, radius, thickness, yaw)
for s in range(3):  # strands twisting a little round the core: a fluted, muscular maple trunk
    pts, rad = [], []
    for k in range(33):
        t = k / 32
        q = axis(t) + horiz(2 * math.pi * s / 3 + math.radians(100) * t) * trunk_r(t) * 0.55
        pts.append(q + noise.noise_vector(q * 0.3 + Vector((s * 3.7, 0, 0))) * 0.3 * math.sin(math.pi * t))
        rad.append(trunk_r(t) * 0.7)
    splines.append((pts, rad))
splines.append(([axis(k / 32) for k in range(33)], [trunk_r(k / 32) * 0.9 for k in range(33)]))  # solid core

MAIN = [  # position on the trunk, azimuth deg, horizontal reach, tip rise, pad radius
    (0.36, 200, 18.5, 2.5, 8.2),  # the long low branch balancing the lean
    (0.50, 105, 12.5, 2.5, 6.6),
    (0.56, 330, 15.0, 2.0, 7.2),
    (0.68, 245, 12.5, 3.0, 6.6),
    (0.78, 55, 11.0, 2.5, 6.0),
    (0.88, 160, 10.0, 2.5, 6.0),
]
for i, (t, az_deg, reach, rise, R) in enumerate(MAIN):
    az = math.radians(az_deg)
    p0, d = axis(t), horiz(az)
    tip = p0 + d * reach + Z * rise
    L = reach
    pts, rad = wobbly(p0, p0 + d * L * 0.4 - Z * 0.5, tip - d * L * 0.25 - Z * 1.5, tip, trunk_r(t) * 0.75, 0.4,
                      0.8, i)
    splines.append(([p0] + pts, [trunk_r(t) * 0.75] + rad))
    pads.append((tip - Z * 0.3, R, 3.2, az))  # the tip sits a little above the pad centre
    tips.append(tip)
    k = int(0.55 * (len(pts) - 1))  # one side shoot to a smaller pad
    q0, side = pts[k], az + math.radians(55 if i % 2 else -55)
    stip = q0 + horiz(side) * R * 0.9 + Z * 1.2
    sp, sr = wobbly(q0, q0 + horiz(side) * R * 0.4, stip - Z * 0.8, stip, rad[k] * 0.8, 0.3, 0.4, 10 + i)
    splines.append(([q0] + sp, [rad[k] * 0.8] + sr))
    pads.append((stip - Z * 0.3, R * 0.62, 3.0, side))
    tips.append(stip)
top = axis(1) + LEAN * -2.5 + Z * 5.5  # apex
sp, sr = wobbly(axis(1), axis(1) + Z * 2, top - Z * 1.5, top, trunk_r(1), 0.4, 0.4, 30)
splines.append(([axis(1)] + sp, [trunk_r(1)] + sr))
pads.append((top - Z * 0.3, 6.6, 3.4, 0.0))
tips.append(top)

a0 = axis(0.12)
for k in range(6):  # nebari: a wide root flare sinking into the soil
    phi = math.radians(k * 60 + 10 + rng.uniform(-12, 12))
    a = a0 + horiz(phi) * 1.0
    c = Vector((a0.x, a0.y, -1.0)) + horiz(phi) * rng.uniform(5.0, 6.8)
    pts, rad = wobbly(a, a + horiz(phi) * 1.5 - Z * 1.2, c - horiz(phi) * 2 + Z * 0.5, c, 1.5, 0.35, 0.3, 20 + k)
    splines.append(([a] + pts, [1.5] + rad))

trunk = D.trunk_mesh(splines, '4a3329')

# ---------- canopy: flat cloud pads (soft flat underside, low dome, scalloped rim), crusted with fine leaf lobes ----------
MATS = [D.material('Leaf_' + n, h) for n, h in LEAVES]
zs = [c.z for c, *_ in pads]
zmin, zmax = min(zs), max(zs)


def pad(bm, c, R, H, yaw):
    zb = c.z - H * 0.38  # the underside plane

    def lobe(p, r, sq):
        for v in bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r,
                                            matrix=Matrix.LocRotScale(p, Euler((0, 0, yaw)), (1, 0.85, sq)))['verts']:
            if v.co.z < zb:
                v.co.z = zb - (zb - v.co.z) * 0.25
    lobe(c, R * 0.8, H * 0.5 / (R * 0.8))
    for k in range(8):  # scalloped rim
        a = yaw + 2 * math.pi * (k + rng.uniform(-0.3, 0.3)) / 8
        r = R * rng.uniform(0.32, 0.45)
        lobe(c + horiz(a) * Vector((R * 0.7, R * 0.6, 0)) + Z * rng.uniform(-0.3, 0.2), r, H * 0.42 / r)
    for _ in range(3):  # a low dome
        r = R * rng.uniform(0.3, 0.4)
        lobe(c + horiz(rng.uniform(0, 2 * math.pi)) * R * 0.3 + Z * H * 0.25, r, H * 0.45 / r)


bms = [bmesh.new() for _ in LEAVES]
TONE = [2.0 * (c.z - zmin) / (zmax - zmin) + rng.uniform(-0.25, 0.25) for c, *_ in pads]  # crimson low, orange high
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
    if me.vertices:  # no pad is amber at its core: that shell is crust only
        D.voxel_union(shells[-1], 0.3, displace=0.15)

# fine leaf lobes over the top and sides in the pad's tone, a step paler on top: each tier gets a lit upper face
crust = [bmesh.new() for _ in LEAVES]
for ob in shells:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    faces = [f for f in bm.faces if f.normal.z > -0.25]
    areas = [f.calc_area() for f in faces]
    for f in (rng.choices(faces, areas, k=int(2.4 * sum(areas))) if faces else []):
        p, nz = f.calc_center_median(), f.normal.z
        val = TONE[pad_of(p)] + 0.95 * max(0.0, nz) ** 2 + 0.25 * noise.noise(p * 0.2) + rng.gauss(0, 0.08)
        r = rng.uniform(0.25, 0.5)
        bmesh.ops.create_icosphere(crust[max(0, min(3, int(val)))], subdivisions=1, radius=r,
                                   matrix=Matrix.Translation(p + f.normal * r * 0.2))
    bm.free()
for ob, cb in zip(shells, crust):
    cb.from_mesh(ob.data)  # appends the shell to its crust
    cb.to_mesh(ob.data)
    cb.free()
    D.voxel_union(ob, 0.13)
blossoms = D.canopy_mesh(shells, MATS, 155000, smooth=1)


# ---------- ground extras: fallen leaves, thickest under the pads, a few afloat on the pond ----------
def leaves():
    bm = bmesh.new()
    fmats = [D.material('Fallen' + n, h) for n, h in LEAVES + [('Brown', '9a5b2c')]]
    grass = bpy.data.objects['Grass']
    mounds = D.bvh_of(grass, keep=lambda f: f.material_index >= 2)
    lily_pts = [v.co for v in bpy.data.objects['LilyPads'].data.vertices]

    def leaf(p, z):  # a five-lobed star, cupped: top and bottom fans share the rim, so it is closed
        r, a0, tx, ty = rng.uniform(0.5, 0.8), rng.uniform(0, 2 * math.pi), rng.gauss(0, 0.08), rng.gauss(0, 0.08)
        mi = rng.choices(range(5), (2, 3, 3, 2, 1))[0]  # mostly red and orange, a few brown
        rim = [bm.verts.new(Vector((p.x, p.y, z))
                            + (horiz(a) * (1 if k % 2 == 0 else 0.5) + Z * (tx * math.cos(a) + ty * math.sin(a))) * r)
               for k, a in ((k, a0 + math.pi * k / 5) for k in range(10))]  # tilted a little
        cu, cd = bm.verts.new(Vector((p.x, p.y, z + 0.08))), bm.verts.new(Vector((p.x, p.y, z - 0.02)))
        for k in range(10):
            bm.faces.new((cu, rim[k], rim[(k + 1) % 10])).material_index = mi
            bm.faces.new((cd, rim[(k + 1) % 10], rim[k])).material_index = mi

    n = 0
    while n < 420:
        if rng.random() < 0.75:  # under a pad
            c, R, *_ = pads[rng.randrange(len(pads))]
            p = D.TREE + Vector((c.x, c.y, 0)) + horiz(rng.uniform(0, 2 * math.pi)) * R * 1.2 * math.sqrt(rng.random())
        else:
            p = Vector((rng.uniform(-34, 34), rng.uniform(-34, 34), 0))
        if not D.open_ground(p, -0.5):
            continue
        hit = mounds.ray_cast(p + Z * 5, -Z)[0]
        leaf(p, (hit.z if hit else 0.0) + 0.05)
        n += 1
    n = 0
    while n < 12:  # afloat, clear of the lily pads and the bridge piers
        p = D.POND + Vector((rng.uniform(-9, 9), rng.uniform(-7, 7), 0))
        if D.pond_gap(p) < -1.2 and D.bridge_dist(p) > 2.8 and min((D.flat(p) - D.flat(q)).length for q in lily_pts) > 0.9:
            leaf(p, 0.13)
            n += 1
    D.prop('Leaves', bm, *fmats, sharp=30)


D.finish('autumn', COLOURS, trunk, shells, blossoms, tips, a0, rocks=(((6, 25, 0), 1.6), ((-26, -17, 0), 2.1),
         ((31, 1, 0), 1.4), ((-9, -27, 0), 1.9), ((-30, 10, 0), 1.3)), pebbles=26, mounds=12, tufts=55, clumps=4,
         lotus=0, extras=leaves)
