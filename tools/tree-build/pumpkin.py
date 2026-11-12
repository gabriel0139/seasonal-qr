"""Build the pumpkin diorama: public/models/pumpkin.glb + public/trees/pumpkin.json.

Run from the repo root: Blender -b -P tools/tree-build/pumpkin.py (Blender 5.2, headless). Deterministic (fixed SEED).
This file is the season: a jack-o'-lantern pile in a pumpkin patch at harvest time, instead of a tree in the pond
garden. Trunk is the stems and the curling vine; Blossoms is the pumpkins, the glowing carved face and the vine leaves.
The patch (split-rail fence and a crow, corn shocks, hay bales, trailing vines with pumpkins, gourds, fallen leaves) is
the season's extras. The base, props, slot cloud, self-checks and export are shared with the other seasons in
diorama.py.
"""
import math, os, sys
sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh, bpy
from mathutils import Vector, Matrix, noise
from mathutils.kdtree import KDTree
import diorama as D
from diorama import Z, bez, lerp, horiz, rng

SEED = 20261032
D.init(SEED)
D.TREE = Vector((-5.0, 6.0, 0.0))  # just behind the board centre: the patch fills the foreground
GROW = 1.4  # the pile is modelled 16 wide and shown 22 wide, to hold the board like the ~40-tall trees
COLOURS = {  # scenery material -> hex sRGB (the autumn lawn)
    'Moss': 'b4a64e', 'Stone': 'bea58e', 'PondBed': '4b6f5c', 'StoneChunk': '8e7464',
    'PondBank': '877c42', 'RimStone': 'b3a69c', 'RimStoneLight': 'cfc3b8', 'Water': '9fd6ea',
    'FlowerCentre': 'f2c84b', 'LilyPad': '7f9443', 'Wood': '9c6b47', 'WoodDark': '6e4932',
    'LanternGlow': 'ffe2a0', 'LanternStone': 'b8ada3', 'RockGrey': '9d9690', 'RockPink': 'ad9a8c',
    'GrassDark': '9e923d', 'GrassLight': 'd0bb6a', 'MossDark': 'a69d47', 'MossLight': 'bbad55',
    'FlowerWhite': 'f7f3ea', 'FlowerLavender': '9d84d6', 'Stem': '7d8f3a',
}
FALLEN = [('Crimson', 'a8241c'), ('Red', 'cc3a22'), ('Orange', 'e0612b'), ('Amber', 'eb9a3a'), ('Brown', '9a5b2c')]

FACE_AZ, FACE_EL = math.atan2(-98 - D.TREE.y, 88 - D.TREE.x), math.radians(18)  # facing the hero camera (88, -98, 66)
C0 = horiz(FACE_AZ + math.pi) * 1.2  # big pumpkin's foot, a little behind the root
SINK, PEN = 0.2, 0.35  # pumpkins sink into the lawn; small ones press this far into their neighbour


# ---------- pumpkin: a closed ribbed superellipsoid, bottom centre at c ----------
def ribbed(bm, c, R, H, ribs, depth, rot=Matrix.Identity(3), mi=0, seg=None, rings=40, dimple=0.08, key=0.0, k=4):
    """Lobes are round, the grooves soft U's (no crease edge), so smooth shading carries them. Returns the stem
    point (the top dimple) and the pumpkin's up axis."""
    seg = seg or ribs * 12

    def local(u, th):
        s, co = math.sin(u), math.cos(u)
        m = (1 - depth * abs(math.sin(ribs * th / 2)) ** k) * (1 + 0.035 * noise.noise(
            Vector((math.cos(th), math.sin(th), key)) * 1.6))  # lobes a little uneven
        e = 0.8 if co > 0 else 1.0  # full shoulders, the belly tucked under
        rho = R * s ** e * m
        z = H / 2 * (1 + math.copysign(abs(co) ** e, co)) - dimple * H * math.exp(-(u / 0.3) ** 2)
        return Vector((rho * math.cos(th), rho * math.sin(th), z))

    top = bm.verts.new(c + rot @ Vector((0, 0, H * (1 - dimple))))
    bot = bm.verts.new(c)
    g = [[bm.verts.new(c + rot @ local(math.pi * i / rings, 2 * math.pi * j / seg)) for j in range(seg)]
         for i in range(1, rings)]
    fs = []
    for j in range(seg):
        j1 = (j + 1) % seg
        fs.append(bm.faces.new((top, g[0][j], g[0][j1])))
        fs.append(bm.faces.new((bot, g[-1][j1], g[-1][j])))
        for r0, r1 in zip(g, g[1:]):
            fs.append(bm.faces.new((r0[j], r1[j], r1[j1], r0[j1])))
    for f in fs:
        f.material_index = mi
    return top.co.copy(), rot @ Z


def shell(name, bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return D.link(name, me)


def closed(ob):  # every edge between exactly two faces: the slot parity test needs it
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    ok = all(e.is_manifold for e in bm.edges) and len(bm.edges) > 0
    bm.free()
    return ok


def boolean(ob, other, op):
    m = ob.modifiers.new('bool', 'BOOLEAN')
    m.operation, m.solver, m.object = op, 'EXACT', other
    D.apply_modifiers(ob)
    bpy.data.objects.remove(other)


big_bm = bmesh.new()
RIBS0 = 10
top0, _ = ribbed(big_bm, C0 - Z * SINK, 8.0, 12.0, RIBS0, 0.11, Matrix.Rotation(FACE_AZ + math.pi / RIBS0, 3, 'Z'),
                 seg=180, rings=72, dimple=0.09, k=3)  # a groove faces the camera, so the eyes sit on lobes
big = shell('ShellBig', big_bm)
bvh_big = D.bvh_of(big)

# ---------- carved face: holes cut along F, filled to just under the skin with a glowing insert ----------
F = horiz(FACE_AZ) * math.cos(FACE_EL) + Z * math.sin(FACE_EL)
RV = Z.cross(F).normalized()  # the viewer's right
UP = F.cross(RV)
P0 = bvh_big.ray_cast(C0 + Z * 7.2 + horiz(FACE_AZ) * 30, -horiz(FACE_AZ))[0]  # the nose bridge
RECESS, DEPTH = 0.25, 0.5  # glow sits RECESS under the skin; the hole's floor DEPTH under its deepest skin point


def tri(cx, cy, w, h):  # pointing up, counter-clockwise seen from the front
    return [Vector((cx - w / 2, cy - h / 3)), Vector((cx + w / 2, cy - h / 3)), Vector((cx, cy + 2 * h / 3))]


def notch(edge, xa, xb, dy):  # a square tooth across [xa, xb] (traversal order), dy tall, into the hole
    def y_at(x):
        for p, q in zip(edge, edge[1:]):
            if (p.x - x) * (q.x - x) <= 0:
                return lerp(p.y, q.y, (x - p.x) / (q.x - p.x))
    ya, yb = y_at(xa), y_at(xb)
    yt = (max if dy > 0 else min)(ya, yb) + dy
    lo, hi = min(xa, xb) - 0.6, max(xa, xb) + 0.6  # lip points cleared round the tooth: room for its fillets
    k = next(i for i, p in enumerate(edge) if lo < p.x < hi)
    return ([p for p in edge[:k] if not lo < p.x < hi] + [Vector((xa, ya)), Vector((xa, yt)), Vector((xb, yt)),
                                                          Vector((xb, yb))] + [p for p in edge[k:] if not lo < p.x < hi])


def grin(W=4.4, mid=-2.6, rise=1.7, h0=0.4, h1=1.05, n=24):  # smile band with round tips; teeth hang and rise
    def c(x):
        return Vector((x, mid + rise * (x / W) ** 2))

    def h(x):
        return h0 + (h1 - h0) * (1 - (x / W) ** 2)

    def nrm(x):
        return Vector((-2 * rise * x / W ** 2, 1)).normalized()

    def cap(x, a0):  # half circle round the tip, counter-clockwise from angle a0
        return [c(x) + Vector((math.cos(a0 + math.pi * k / 8), math.sin(a0 + math.pi * k / 8))) * h0 for k in range(1, 8)]

    xs = [W * (-1 + 2 * i / n) for i in range(n + 1)]
    lower = notch([c(x) - nrm(x) * h(x) for x in xs], -0.5, 0.5, 0.85)
    upper = [c(x) + nrm(x) * h(x) for x in reversed(xs)]
    upper = notch(notch(upper, 2.0, 1.05, -0.75), -1.05, -2.0, -0.75)
    a_r, a_l = math.atan2(*reversed(-nrm(W))), math.atan2(*reversed(nrm(-W)))
    return lower + cap(W, a_r) + upper + cap(-W, a_l)


def fillet(poly, r, n=5):  # round every convex corner sharper than 150 degrees
    out = []
    for i, b in enumerate(poly):
        a, c = poly[i - 1], poly[(i + 1) % len(poly)]
        u, w = (a - b).normalized(), (c - b).normalized()
        ang = math.acos(max(-1.0, min(1.0, u.dot(w))))
        if (b - a).cross(c - b) <= 0 or ang > math.radians(150):
            out.append(b)
            continue
        t = min(r / math.tan(ang / 2), 0.5 * (a - b).length, 0.5 * (c - b).length)
        rr = t * math.tan(ang / 2)
        o = b + (u + w).normalized() * (rr / math.sin(ang / 2))
        a1, a2 = (math.atan2(q.y - o.y, q.x - o.x) for q in (b + u * t, b + w * t))
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        out += [o + Vector((math.cos(a1 + da * k / n), math.sin(a1 + da * k / n))) * rr for k in range(n + 1)]
    return out


# rounded corners: an acute hole corner leaves interior points whose nearest skin point is that edge, and there
# diorama's normal-sign test depends on which face the BVH reports, so a rounded slot could flip
FEATURES = [fillet(p, 0.35) for p in (tri(-2.7, 2.3, 3.0, 2.7), tri(2.7, 2.3, 3.0, 2.7), tri(0, 0.35, 1.5, 1.3), grin())]
for p in FEATURES:  # self-check: no corner sharper than 90 degrees survives
    assert all((q - p[i - 1]).normalized().dot((p[(i + 1) % len(p)] - q).normalized()) > -0.05 or
               (q - p[i - 1]).cross(p[(i + 1) % len(p)] - q) < 0 for i, q in enumerate(p)), 'sharp face corner'


def in_poly(poly, x, y):
    c = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def grow(poly, g):  # mitred outward offset of a counter-clockwise outline
    out = []
    for i, (xb, yb) in enumerate(poly):
        (xa, ya), (xc, yc) = poly[i - 1], poly[(i + 1) % len(poly)]
        n1, n2 = Vector((yb - ya, xa - xb)).normalized(), Vector((yc - yb, xb - xc)).normalized()
        m = (n1 + n2).normalized()
        m *= g / max(0.35, m.dot(n1))
        out.append((xb + m.x, yb + m.y))
    return out


def skin_range(poly):  # lowest and highest skin height along F over the feature
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    pts = list(poly) + [(x, y) for x in [min(xs) + 0.2 * i for i in range(int((max(xs) - min(xs)) / 0.2) + 1)]
                        for y in [min(ys) + 0.2 * j for j in range(int((max(ys) - min(ys)) / 0.2) + 1)]
                        if in_poly(poly, x, y)]
    ss = [(bvh_big.ray_cast(P0 + RV * x + UP * y + F * 12, -F)[0] - P0).dot(F) for x, y in pts]
    return min(ss), max(ss)


def prism(bm, poly, s0, s1, floor=None):  # floor: the outline at s0, if narrower (a tapered hole)
    lo = [bm.verts.new(P0 + RV * x + UP * y + F * s0) for x, y in floor or poly]
    hi = [bm.verts.new(P0 + RV * x + UP * y + F * s1) for x, y in poly]
    n = len(poly)
    for i in range(n):
        bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
    bmesh.ops.triangulate(bm, faces=[bm.faces.new(hi), bm.faces.new(lo[::-1])], ngon_method='EAR_CLIP')


cut_bm, glow_bm = bmesh.new(), bmesh.new()
# the hole tapers in to its floor: with square floor edges, a point in the plane of the floor (or of a wall) has its
# nearest skin point on that edge at a right angle, and diorama's normal-sign test sees a dot of ~0 there and can flip
for poly, taper in zip(FEATURES, (0.3, 0.3, 0.3, 0.2)):
    s_lo, s_hi = skin_range(poly)
    prism(cut_bm, poly, s_lo - DEPTH, s_hi + 0.3, floor=grow(poly, -taper))
    prism(glow_bm, grow(poly, 0.08), s_lo - DEPTH - 0.6, s_hi + 0.3)
inner_bm = bmesh.new()
inner_bm.from_mesh(big.data)
inner_bm.normal_update()
for v in inner_bm.verts:
    v.co -= v.normal * RECESS
glow = shell('ShellGlow', glow_bm)
boolean(glow, shell('Inner', inner_bm), 'INTERSECT')  # the insert's top follows the skin, RECESS under it
boolean(big, shell('Cutter', cut_bm), 'DIFFERENCE')
assert closed(big) and closed(glow), 'face carving broke a shell'  # a self-crossing cutter makes the boolean fail
bvh_big = D.bvh_of(big)


# ---------- the small pumpkins: two nestled against the big one's foot, one perched on its shoulder ----------
def coarse(spec, c, rot):
    bm = bmesh.new()
    R, H, ribs, depth, dimple, key = spec
    ribbed(bm, c, R, H, ribs, depth, rot, seg=48, rings=14, dimple=dimple, key=key)
    vs = [v.co.copy() for v in bm.verts]
    bm.free()
    return vs


def press(vs):  # how deep the points reach into the big pumpkin
    deepest = 0.0
    for v in vs:
        co, nor, _, dist = bvh_big.find_nearest(v)
        if (co - v).dot(nor) > 0:
            deepest = max(deepest, dist)
    return deepest


def nestle(spec, az, rot, pen=PEN):  # slide in along the ground until it presses pen into the big one
    for k in range(120):
        c = C0 + horiz(az) * (12 - 0.1 * k) - Z * SINK
        if press(coarse(spec, c, rot)) > pen:
            return c + horiz(az) * 0.1
    raise AssertionError('small pumpkin never met the big one')


def perch(spec, az, rad, tilt):  # lower onto the big one's shoulder, leaning with its slope
    xy = C0 + horiz(az) * rad
    nor = bvh_big.ray_cast(xy + Z * 30, -Z)[1]
    rot = Z.rotation_difference(Z.lerp(nor, tilt).normalized()).to_matrix()
    for k in range(200):
        c = xy + Z * (16 - 0.05 * k)
        if press(coarse(spec, c, rot)) > PEN:
            return c + Z * 0.05, rot
    raise AssertionError('perched pumpkin never landed')


SMALL = {  # name: (R, H, ribs, depth, dimple, key)
    'A': (2.3, 2.1, 12, 0.10, 0.1, 3.0),  # deep red-orange, squat
    'B': (2.0, 2.8, 9, 0.08, 0.08, 5.0),  # pale amber, tall
    'C': (2.7, 3.0, 11, 0.09, 0.1, 7.0),  # bright orange, perched
}
lean_b = Z.rotation_difference((Z - horiz(math.radians(5)) * 0.14).normalized()).to_matrix()
cA = nestle(SMALL['A'], math.radians(-118), Matrix.Identity(3), 0.45)
cB = nestle(SMALL['B'], math.radians(5), lean_b)
cC, rot_c = perch(SMALL['C'], math.radians(170), 4.2, 0.6)
smalls = {}
for name, c, rot in (('A', cA, Matrix.Rotation(0.3, 3, 'Z')), ('B', cB, lean_b), ('C', cC, rot_c)):
    bm = bmesh.new()
    R, H, ribs, depth, dimple, key = SMALL[name]
    top, up = ribbed(bm, c, R, H, ribs, depth, rot, seg=ribs * 14, rings=40, dimple=dimple, key=key)
    smalls[name] = (shell('Shell' + name, bm), top, up)

# ---------- vine leaves: fat five-lobed pillows lying by the vines ----------
def vine_leaf(bm, c, R, az, tilt, thick=0.32, NR=4, K=60, mi=0):
    d = horiz(az) * math.cos(tilt) + Z * math.sin(tilt)
    side = horiz(az + math.pi / 2)
    n = d.cross(side)
    n = n if n.z > 0 else -n
    ct, cb = bm.verts.new(c + n * thick / 2), bm.verts.new(c - n * thick / 2)
    rings_t, rings_b = [], []
    for k in range(1, NR + 1):
        t = k / NR
        rt, rb = [], []
        for j in range(K):
            a = -math.pi + 2 * math.pi * (j + 0.5) / K
            r = R * (0.62 + 0.38 * abs(math.cos(2.5 * a)) ** 1.5) * (1 - 0.5 * math.exp(-((abs(a) - math.pi) / 0.3) ** 2))
            q = c + (d * math.cos(a) + side * math.sin(a)) * r * t + n * (R * t * t * (0.12 + 0.06 * math.sin(5 * a)))
            h = thick / 2 * (1 - t * t)
            if k == NR:
                v = bm.verts.new(q)
                rt.append(v)
                rb.append(v)
            else:
                rt.append(bm.verts.new(q + n * h))
                rb.append(bm.verts.new(q - n * h))
        rings_t.append(rt)
        rings_b.append(rb)
    fs = []
    for j in range(K):
        j1 = (j + 1) % K
        fs += [bm.faces.new((ct, rings_t[0][j], rings_t[0][j1])), bm.faces.new((cb, rings_b[0][j1], rings_b[0][j]))]
        fs += [bm.faces.new((r0[j], r1[j], r1[j1], r0[j1])) for r0, r1 in zip(rings_t, rings_t[1:])]
        fs += [bm.faces.new((r0[j], r0[j1], r1[j1], r1[j])) for r0, r1 in zip(rings_b, rings_b[1:])]
    for f in fs:
        f.material_index = mi


FWD, RIGHT = horiz(FACE_AZ), horiz(FACE_AZ + math.pi / 2)
# (forward, right) from C0 or (C0 az, radius), points to (deg off the face), R, tilt (negative: tip down, face up to us)
LEAF_AT = [(8.0, -4.3, -50, 2.7, -18), (7.2, 4.4, 45, 2.5, -18), (50, 7.0, 50, 2.4, 45)]
leaf_bm = bmesh.new()
for i, (f, r, to, R, tilt) in enumerate(LEAF_AT):
    tilt = math.radians(tilt)
    c = C0 + (FWD * f + RIGHT * r if i < 2 else horiz(math.radians(f)) * r)  # the third sits behind, by C0 azimuth
    vine_leaf(leaf_bm, c + Z * (0.3 + R * abs(math.sin(tilt)) * 0.9), R, (FACE_AZ if i < 2 else 0) + math.radians(to),
              tilt)
leaves = shell('ShellLeaves', leaf_bm)

# ---------- trunk: fluted stems and two fat vines snaking out from under the big pumpkin ----------
splines = []


def stem(base, up, length, r0, bend, flutes=5):
    p0, p3 = base - up * 0.8, base + up * length + bend
    e1 = up.orthogonal().normalized()
    e2 = up.cross(e1)
    ts = [k / 16 for k in range(17)]
    surf = 0.8 / (length + 0.8)
    axis = [bez(p0, base + up * length * 0.5, base + up * length * 0.9 + bend * 0.3, p3, t) for t in ts]
    rad = [r0 * lerp(1.0, 0.75, t) * (1 + 0.45 * math.exp(-((t - surf) / 0.12) ** 2)) for t in ts]
    splines.append((axis, [r * 0.8 for r in rad]))
    for f in range(flutes):
        a = 2 * math.pi * f / flutes
        splines.append(([p + (e1 * math.cos(a) + e2 * math.sin(a)) * r * 0.5 for p, r in zip(axis, rad)],
                        [r * 0.5 for r in rad]))


stem(top0, Z, 3.0, 1.15, horiz(math.radians(60)) * 1.3)
for name, bend_az, ln, r0 in (('A', -150, 1.3, 0.55), ('B', 40, 1.5, 0.5), ('C', 160, 1.4, 0.6)):
    _, top, up = smalls[name]
    stem(top, up, ln, r0, horiz(math.radians(bend_az)) * 0.5)


def run(p0, p1, p2, p3, r0, r1, n=24):
    return [bez(p0, p1, p2, p3, k / n) for k in range(n + 1)], [lerp(r0, r1, k / n) for k in range(n + 1)]


def curl(e, t, r0, r1, rho0=1.2, turns=0.95, n=36):  # lifts off the ground, rolls forward and over, tightening
    pts, rad = [], []
    for k in range(1, n + 1):
        u = k / n
        phi, rho = 2 * math.pi * turns * u, rho0 * (1 - 0.55 * u)
        pts.append(e + Z * rho0 + t * (rho * math.sin(phi)) - Z * (rho * math.cos(phi)))
        rad.append(lerp(r0, r1, u))
    return pts, rad


def through(ps, n=10):  # Catmull-Rom curve through the points
    out = []
    for i in range(len(ps) - 1):
        p0, p1, p2, p3 = ps[max(i - 1, 0)], ps[i], ps[i + 1], ps[min(i + 2, len(ps) - 1)]
        out += [0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3)
                for t in (k / n for k in range(n))]
    return out + [ps[-1]]


# from under the big one's chin it snakes towards the camera (the open side: the big one sits back from the root),
# then rolls up into a curl whose plane is square to the view
FWD, RIGHT = horiz(FACE_AZ), horiz(FACE_AZ + math.pi / 2)
VINE = [(3.0, -1.0), (5.2, -2.6), (6.8, -1.6), (7.3, 0.6), (7.6, 2.2)]  # (forward, right) from C0
pts = through([C0 + FWD * f + RIGHT * r + Z * 0.75 for f, r in VINE])
t = D.flat(pts[-1] - pts[-2]).normalized().to_3d()
cp, cr = curl(pts[-1], t, 0.75, 0.3)
splines.append((pts + cp, [lerp(1.0, 0.75, i / (len(pts) - 1)) for i in range(len(pts))] + cr))

# a pig-tail tendril off the big stem, coiling in a plane that faces the camera (and stepping towards it, so the
# coils never fuse)
S0 = top0 + Z * 1.6 - RV * 0.75
LEFT = -RV
tail = []
for k in range(49):
    phi = math.pi + 2.5 * math.pi * k / 48
    rho = 1.1 * (1 - 0.6 * k / 48)
    tail.append(S0 + LEFT * 1.1 + (LEFT * math.cos(phi) + Z * math.sin(phi)) * rho + F * (0.5 * k / 48))
splines.append((tail, [lerp(0.34, 0.26, k / 48) for k in range(49)]))

trunk = D.trunk_mesh([([p * GROW for p in ps], [r * GROW for r in rs]) for ps, rs in splines], '56602b')

# ---------- canopy: one shell per colour, deep to pale; the glow and the leaves ride in the middle ----------
pumpkins = [smalls['A'][0], big, glow, leaves, smalls['C'][0], smalls['B'][0]]
for ob in pumpkins:
    assert closed(ob), ('open shell', ob.name)
    ob.data.transform(Matrix.Scale(GROW, 4))
MATS = [D.material(n, h) for n, h in (('Pumpkin_Deep', 'b9471b'), ('Pumpkin', 'e8781f'), ('FaceGlow', 'ffc64a'),
                                      ('VineLeaf', '5f7d2f'), ('Pumpkin_Bright', 'f0962e'), ('Pumpkin_Pale', 'f2c47e'))]
bsdf = MATS[2].node_tree.nodes['Principled BSDF']
bsdf.inputs['Emission Color'].default_value = D.srgb('ffa928')
bsdf.inputs['Emission Strength'].default_value = 1.0
blossoms = D.canopy_mesh(pumpkins, MATS, 90000, smooth=0)
blossoms.data.set_sharp_from_angle(angle=math.radians(45))  # crisp cut rims and leaf edges, soft grooves




# ---------- the patch: scenery added inside finish() ----------
CAMDIR, SIDE = horiz(FACE_AZ), horiz(FACE_AZ + math.pi / 2)  # from the pile towards the hero camera, and screen right
taken = []  # (centre, radius) discs of lawn the patch props hold


def at(f, r):  # a lawn point f towards the camera and r to screen right of the pile
    return D.TREE + CAMDIR * f + SIDE * r


def free(p, r):  # open lawn: on the board, off the pile (its leaves reach ~15) and the patch props
    return (max(abs(p.x), abs(p.y)) < 33 - r and D.flat(p - D.TREE).length > 15 + r
            and all(D.flat(p - c).length > r + cr for c, cr in taken))


def append(bm, tmp):  # copy a bmesh into another, material indices kept
    me = bpy.data.meshes.new('tmp')
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def box(bm, mi, c, size, rot=Matrix.Identity(3), bevel=0.0):  # c: centre of the bottom face
    tmp = bmesh.new()
    for v in bmesh.ops.create_cube(tmp, size=1.0)['verts']:
        v.co = c + rot @ Vector((v.co.x * size[0], v.co.y * size[1], (v.co.z + 0.5) * size[2]))
    if bevel:
        bmesh.ops.bevel(tmp, geom=list(tmp.edges), offset=bevel, segments=2, profile=0.6, affect='EDGES')
    for f in tmp.faces:
        f.material_index = mi
    append(bm, tmp)


def mini(bm, c, R, mi, stem_mi, key):  # a small pumpkin on the lawn with a stubby stem
    top, _ = ribbed(bm, c - Z * 0.05, R, R * rng.uniform(0.75, 0.95), rng.choice((8, 10)), 0.1,
                    Matrix.Rotation(rng.uniform(0, 6.3), 3, 'Z'), mi, seg=60, rings=16, key=key)
    D.rod(bm, stem_mi, top - Z * 0.2, top + Z * R * 0.5 + horiz(rng.uniform(0, 6.3)) * 0.15, R * 0.17, R * 0.12, seg=6)


def fence():  # split-rail fence along the two back edges, a fat crow on one post looking at the pumpkins
    bm, E = bmesh.new(), 31.5
    tops = []
    for a, b, n in ((Vector((-E, E, 0)), Vector((E, E, 0)), 7), (Vector((-E, -E, 0)), Vector((-E, E, 0)), 7)):
        posts = [a.lerp(b, k / n) + horiz(rng.uniform(0, 6.3)) * rng.uniform(0, 0.3) for k in range(n + 1)]
        if b.x < 0:
            posts[-1] = tops[0] - Z * tops[0].z  # the shared corner post
        for k, p in enumerate(posts):
            if not (b.x < 0 and k == n):
                h = rng.uniform(4.8, 5.4)
                box(bm, 1, p, (0.8, 0.8, h), Matrix.Rotation(rng.uniform(-0.3, 0.3), 3, 'Z'), bevel=0.12)
                tops.append(p + Z * h)
        for p, q in zip(posts, posts[1:]):
            x = D.flat(q - p).normalized().to_3d()
            for hz in (1.9, 3.7):
                z = (Z + x * rng.uniform(-0.04, 0.04)).normalized()
                rot = Matrix((x, z.cross(x), z)).transposed()
                box(bm, 0, (p + q) / 2 + Z * (hz - 0.3 + rng.uniform(-0.15, 0.15)), ((q - p).length + 1.0, 0.45, 0.6),
                    rot, bevel=0.1)
    D.prop('Fence', bm, D.material('Wood', COLOURS['Wood']), D.material('WoodDark', COLOURS['WoodDark']), sharp=50)

    perch = min(tops, key=lambda t: (D.flat(t) - Vector((13.5, 31.5))).length)
    look = D.flat(D.TREE - perch).normalized().to_3d()
    s = Z.cross(look)
    body, bm = perch + Z * 0.95, bmesh.new()
    D.prim(bm, 'icosphere', 0, D.frame(body, look * 1.3, s * 0.85, Z * 0.85), subdivisions=3, radius=1.0)
    head = body + look * 1.05 + Z * 0.7
    D.blob(bm, 0, head, 0.6, sub=3)
    D.rod(bm, 1, head + look * 0.35, head + look * 1.15 - Z * 0.1, 0.22, 0.0, seg=8)  # beak
    tail = (-look * 0.94 + Z * 0.34).normalized()
    D.prim(bm, 'icosphere', 0, D.frame(body + tail * 1.35, tail * 0.85, s * 0.42, tail.cross(s) * 0.13), subdivisions=2,
           radius=1.0)
    for side in (-1, 1):
        D.blob(bm, 2, head + look * 0.32 + Z * 0.15 + s * side * 0.47, 0.12, sub=2)  # eyes
        D.prim(bm, 'icosphere', 0, D.frame(body + s * side * 0.66 + Z * 0.15 - look * 0.15, look * 1.0, s * 0.28,
                                          Z * 0.55), subdivisions=2, radius=1.0)  # folded wings
        D.rod(bm, 1, body - Z * 0.6 + s * side * 0.3, perch + s * side * 0.3 + Z * 0.02, 0.09, 0.09, seg=5)  # legs
    D.prop('Crow', bm, *[D.material(n, h) for n, h in (('Crow', '2c2a35'), ('CrowBeak', '4b4552'), ('CrowEye', 'f4efe0'))])


def corn_shocks():  # bundled stalks tied at the waist, splaying out at the top, a few leaves hanging
    bm = bmesh.new()
    for base, h in ((Vector((8.0, 21.0, 0.0)), 12.0), (Vector((-24.0, -3.0, 0.0)), 10.5)):
        taken.append((base, 4.0))
        tie = base + Z * h * 0.48
        for k in range(18):
            a = 2 * math.pi * k / 18 + rng.uniform(-0.12, 0.12)
            foot = base + horiz(a) * 2.7 * rng.uniform(0.85, 1.1)
            waist = tie + horiz(a) * 0.55
            top = tie + horiz(a + rng.uniform(-0.15, 0.15)) * 2.7 * rng.uniform(0.45, 0.8) + Z * h * rng.uniform(0.4, 0.52)
            D.rod(bm, k % 2, foot, waist, 0.3, 0.26, seg=5)
            D.rod(bm, k % 2, waist, top, 0.26, 0.08, seg=5)
            if k % 3 == 0:
                d = (horiz(a) * 0.75 - Z * 0.65).normalized()
                q = waist.lerp(top, rng.uniform(0.35, 0.6)) + d * 1.3
                w = Z.cross(d).normalized()
                D.prim(bm, 'icosphere', k % 2, D.frame(q, d * 1.5, w * 0.35, d.cross(w) * 0.07), subdivisions=1,
                       radius=1.0)
        D.tube(bm, 2, [tie + horiz(2 * math.pi * k / 20) * 0.95 for k in range(20)], 0.24, closed=True)  # twine
    D.prop('CornShocks', bm, *[D.material(n, h) for n, h in (('CornStalk', 'd8b96e'), ('CornStalkDark', 'b8954c'),
                                                            ('Twine', '8a6a3a'))])


def hay_bales():  # two bales side by side, a third across them, a pumpkin on top
    bm, c, L, W, H = bmesh.new(), Vector((-15.0, -17.0, 0.0)), 6.4, 3.4, 3.0
    taken.append((c, 5.5))
    r0 = Matrix.Rotation(math.radians(25), 3, 'Z')

    def bale(p, rot):
        box(bm, 0, p, (L, W, H), rot, bevel=0.55)
        for t in (-0.27, 0.27):
            box(bm, 1, p + rot @ Vector((t * L, 0, -0.05)), (0.24, W + 0.1, H + 0.1), rot)

    for side in (-1, 1):
        bale(c + r0 @ Vector((0, side * (W / 2 + 0.1), 0)), r0)
    bale(c + Z * (H - 0.05), r0 @ Matrix.Rotation(math.pi / 2, 3, 'Z'))
    mini(bm, c + Z * (2 * H - 0.1), 2.1, 2, 3, 21.0)
    D.prop('HayBales', bm, *[D.material(n, h) for n, h in (('Hay', 'dcbd6a'), ('HayTwine', 'a0773e'),
                                                          ('GourdOrange', 'ea8a2c'), ('GourdStem', '6b5a2e'))])


def patch_vines():  # vines trailing off the pile across the foreground, with leaves, curls and pumpkins on them
    bm = bmesh.new()
    VINES = [([(12.5, 4), (16, 8), (19, 6.5), (23, 10), (27, 9), (30, 12)], ((0.35, 2.0, 2), (0.8, 1.6, 4))),
             ([(12.5, -3), (16, -7), (20, -5.5), (24, -10), (28, -9), (31, -13)], ((0.45, 1.8, 3), (0.9, 1.4, 2)))]
    for v, (ctrl, crop) in enumerate(VINES):
        pts = through([at(f, r) + Z * 0.38 for f, r in ctrl], n=12)
        D.tube(bm, 0, pts, 0.38, sides=7)
        arc = [0.0]
        for p, q in zip(pts, pts[1:]):
            arc.append(arc[-1] + (q - p).length)

        def along(u):  # point and tangent at a fraction of the vine's length
            i = min(next((i for i, a in enumerate(arc) if a >= u * arc[-1]), len(arc) - 1), len(pts) - 2)
            return pts[i], (pts[i + 1] - pts[i]).normalized()

        for j, u in enumerate(x / arc[-1] for x in [2.5 + 3.3 * k for k in range(int((arc[-1] - 3) / 3.3))]):
            p, t = along(u)
            side = Z.cross(t) * (1 if j % 2 else -1)
            R, tilt = rng.uniform(1.4, 1.9), math.radians(rng.uniform(-14, 8))
            vine_leaf(bm, p + side * R * 0.8 + Z * (0.25 + R * abs(math.sin(tilt))), R,
                      math.atan2(side.y, side.x) + rng.uniform(-0.4, 0.4), tilt, thick=0.24, NR=3, K=36, mi=1)
            if j % 3 == 1:  # a tendril curling up off the vine, its plane square to the vine
                c = p - side * 0.3 + Z * 0.95
                D.tube(bm, 0, [c + (side * math.cos(-math.pi / 2 - 3 * math.pi * k / 24) + Z * math.sin(
                    -math.pi / 2 - 3 * math.pi * k / 24)) * 0.7 * (1 - 0.6 * k / 24) + t * 0.03 * k for k in range(25)],
                       0.11, sides=5)
        for u, R, mi in crop:
            p, t = along(u)
            side = Z.cross(t) * (1 if u > 0.6 else -1)
            c = D.flat(p + side * (R + 0.35)).to_3d()
            mini(bm, c, R, mi, 5, 30.0 + 3 * v + u)
            taken.append((c, R + 1.0))
        taken.extend((p, 1.5) for p in pts[::4])
    D.prop('PatchVines', bm, *[D.material(n, h) for n, h in (
        ('PatchVine', '5d6b2c'), ('PatchLeaf', '6a8a34'), ('GourdOrange', 'ea8a2c'), ('GourdCream', 'efe2c4'),
        ('GourdRed', 'c4502a'), ('GourdStem', '6b5a2e'))])


def prune(obstacles):  # drop every grass tuft, mound, flower and rock touching the pile or a patch prop
    out = [D.bvh_of(ob) for ob in obstacles]

    def touches(p):
        if D.flat(p - D.TREE).length < 7.5:
            return True
        # ray parity, not the nearest face's normal: the thin leaves and overlapping fence boxes fool the latter
        return any(b.find_nearest(p)[3] < 0.3 or D.parity_inside(b, p) for b in out)

    for name in ('Grass', 'Rocks', 'Flowers'):
        bm = bmesh.new()
        bm.from_mesh(bpy.data.objects[name].data)
        islands, seen = [], set()
        for v in bm.verts:  # connected pieces: a blade, a mound, a rock, a petal
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
        # vertices and points along the edges: a blade can pierce a thin leaf with both ends clear of it
        hit = [isl for isl in islands if any(touches(u.co) for u in isl)
               or any(touches(e.verts[0].co.lerp(e.verts[1].co, t)) for u in isl for e in u.link_edges for t in (0.25, 0.5, 0.75))]
        print('PUMPKIN pruned', len(hit), 'of', len(islands), 'pieces of', name)
        bad = [u for isl in hit for u in isl]
        bmesh.ops.delete(bm, geom=bad, context='VERTS')
        # cap the blades' open bases (underground): open blades make the slot sampler's ray parity flip on rounding
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=3)
        assert not any(e.is_boundary for e in bm.edges), name
        bm.to_mesh(bpy.data.objects[name].data)
        bm.free()


def patch():
    fence()
    corn_shocks()
    hay_bales()
    patch_vines()
    prune(pumpkins + [trunk] + [bpy.data.objects[n] for n in ('Fence', 'CornShocks', 'HayBales', 'PatchVines')])
    grass = bpy.data.objects['Grass']
    mounds = D.bvh_of(grass, keep=lambda f: f.material_index >= 2)
    kd = KDTree(len(grass.data.vertices))
    for i, v in enumerate(grass.data.vertices):
        kd.insert(Vector((v.co.x, v.co.y, 0)), i)
    kd.balance()

    def ground(p):
        hit = mounds.ray_cast(p + Z * 5, -Z)[0]
        return hit.z if hit else 0.0

    bm = bmesh.new()
    for k in range(9):  # gourds scattered on open lawn, clear of grass tufts
        while True:
            p = Vector((rng.uniform(-33, 33), rng.uniform(-33, 33), 0))
            if free(p, 2.5) and kd.find(p)[2] > 1.8:
                break
        R = rng.uniform(0.9, 1.4)
        mini(bm, p + Z * ground(p), R, rng.choices(range(3), (3, 2, 1))[0], 3, 10.0 + k)
        taken.append((p, R + 2.0))
    D.prop('Gourds', bm, *[D.material(n, h) for n, h in (('GourdOrange', 'ea8a2c'), ('GourdCream', 'efe2c4'),
                                                         ('GourdRed', 'c4502a'), ('GourdStem', '6b5a2e'))])

    bm = bmesh.new()

    def leaf(p, z):  # a five-lobed star, cupped: top and bottom fans share the rim, so it is closed (as autumn.py)
        r, a0, tx, ty = rng.uniform(0.5, 0.8), rng.uniform(0, 2 * math.pi), rng.gauss(0, 0.08), rng.gauss(0, 0.08)
        mi = rng.choices(range(5), (2, 3, 3, 2, 1))[0]
        rim = [bm.verts.new(Vector((p.x, p.y, z))
                            + (horiz(a) * (1 if k % 2 == 0 else 0.5) + Z * (tx * math.cos(a) + ty * math.sin(a))) * r)
               for k, a in ((k, a0 + math.pi * k / 5) for k in range(10))]
        cu, cd = bm.verts.new(Vector((p.x, p.y, z + 0.08))), bm.verts.new(Vector((p.x, p.y, z - 0.02)))
        for k in range(10):
            bm.faces.new((cu, rim[k], rim[(k + 1) % 10])).material_index = mi
            bm.faces.new((cd, rim[(k + 1) % 10], rim[k])).material_index = mi

    n = 0
    while n < 240:
        p = Vector((rng.uniform(-34, 34), rng.uniform(-34, 34), 0))
        if free(p, -0.8):
            leaf(p, ground(p) + 0.05)
            n += 1
    D.prop('Leaves', bm, *[D.material('Fallen' + n, h) for n, h in FALLEN], sharp=30)


D.finish('pumpkin', COLOURS, trunk, pumpkins, blossoms, [], Vector((0, 0, 0)),
         rocks=(((25, -3, 0), 2.4), ((-24, 12, 0), 1.8), ((14, 26, 0), 1.6)), pebbles=20, mounds=12, tufts=55,
         clumps=4, lotus=0, extras=patch, pond=False, bridge=False, lantern=False)
