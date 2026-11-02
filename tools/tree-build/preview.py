"""Render a preview of an exported tree GLB.
Blender -b -P tools/tree-build/preview.py -- public/models/sakura.glb out.png [camX camY camZ]
"""
import bpy, math, sys
from mathutils import Vector

glb, out, *cam_loc = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 800
scene.view_settings.view_transform = 'Standard'
scene.world = bpy.data.worlds.new('World')
scene.world.color = (0.55, 0.6, 0.68)
if scene.world.node_tree:
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.6, 0.68, 1)


def aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()


def add(name, data, loc, target=(0, 0, 14)):
    ob = bpy.data.objects.new(name, data)
    scene.collection.objects.link(ob)
    ob.location = loc
    aim(ob, target)
    return ob


cam = bpy.data.cameras.new('Cam')
cam.lens = 50
scene.camera = add('Cam', cam, tuple(map(float, cam_loc)) or (88, -98, 66), (0, 0, 16))
for name, kind, energy, loc in (('Key', 'SUN', 2.2, (60, -40, 90)), ('Fill', 'SUN', 0.7, (-80, -60, 30)),
                                ('Rim', 'SUN', 1.2, (-30, 90, 60))):
    light = bpy.data.lights.new(name, kind)
    light.energy = energy
    light.angle = math.radians(8)
    add(name, light, loc, (0, 0, 0))
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
