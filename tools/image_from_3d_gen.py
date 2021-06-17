import bpy
import os
import math
from random import seed
from random import random
from datetime import datetime

def deg_to_radians(deg):
    return (deg / 360) * 2 * math.pi

def timestamp():
    current_moment = datetime.now()
    timestamp = math.floor(datetime.timestamp(current_moment))
    return timestamp

def deselect_all():
    if bpy.context.object.mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

#delete everything
if bpy.context.object.mode == 'EDIT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()

model_path = "/home/spencer/ldraw/parts/"
render_path = "/home/spencer/Documents/GitHub/nexus/tools/renders/"

#model = "30136.dat"
model = "3034.dat"
path = os.path.join(model_path, model)
bpy.ops.import_scene.importldraw(filepath=path)

deselect_all()
bpy.data.objects["LegoGroundPlane"].select_set(True)
bpy.ops.object.delete()

brick = bpy.data.objects[f"00000_{model}"]
scene = bpy.data.scenes['Scene']

dims = brick.dimensions
dimx, dimy, dimz = dims[0], dims[1], dims[2]

#camera location
locx, locy, locz = ((max(dimx, dimy, dimz))*1.5), ((max(dimx, dimy, dimz))*1.5), (dimz / 2)
rotx, roty, rotz = deg_to_radians(-90), deg_to_radians(180), deg_to_radians(-45)

#set camera
bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(locx, locy, locz), rotation=(rotx, roty, rotz), scale=(1, 1, 1))
scene.camera = bpy.context.object
scene.render.resolution_x = 512
scene.render.resolution_y = 512

#set light
bpy.ops.object.light_add(type='SUN', radius=1, align='WORLD', location=(locx, locy, locz + 10), scale=(1, 1, 1))

scene.cycles.device = 'GPU'
scene.cycles.progressive = 'BRANCHED_PATH'
scene.cycles.subsurface_samples = 5

def rotate_brick(x, y, z):
    deselect_all()
    brick.select_set(True)
    override=bpy.context.copy()
    override['area']=[a for a in bpy.context.screen.areas if a.type=="VIEW_3D"][0]
    bpy.ops.transform.rotate(override, value=x, orient_axis='X')
    bpy.ops.transform.rotate(override, value=y, orient_axis='Y')
    bpy.ops.transform.rotate(override, value=z, orient_axis='Z')

seed()

for i in range(10):
    rotate_brick(random()*10, random()*10, random()*10)
    bpy.context.scene.render.filepath = os.path.join(render_path, f"{model[:-4]}-{timestamp()}")
    bpy.ops.render.render(write_still = True)
