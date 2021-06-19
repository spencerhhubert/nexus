import bpy
import os
import math
from random import seed
from random import random
from datetime import datetime

def deg_to_radians(deg):
    return (deg / 360) * 2 * math.pi

def random_radian():
    return deg_to_radians(random() * 360)

def timestamp():
    current_moment = datetime.now()
    timestamp = math.floor(datetime.timestamp(current_moment))
    return timestamp

def deselect_all():
    if bpy.context.object.mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

def gen_pics(model, iterations, inPath, outPath, res):
    seed()
    #delete everything
    if bpy.context.object.mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    path = os.path.join(inPath, model)
    bpy.ops.import_scene.importldraw(filepath=path)

    deselect_all()
    bpy.data.objects["LegoGroundPlane"].select_set(True)
    bpy.ops.object.delete()

    piece = bpy.data.objects[f"00000_{model}"]
    scene = bpy.data.scenes['Scene']

    dims = piece.dimensions
    dimx, dimy, dimz = dims[0], dims[1], dims[2]

    #camera location
    locx, locy, locz = ((max(dimx, dimy, dimz))+.5), ((max(dimx, dimy, dimz))+.5), (dimz / 2)
    rotx, roty, rotz = deg_to_radians(-90), deg_to_radians(180), deg_to_radians(-45)

    #set camera
    bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(locx, locy, locz), rotation=(rotx, roty, rotz), scale=(1, 1, 1))
    scene.camera = bpy.context.object
    scene.render.resolution_x = res
    scene.render.resolution_y = res

    #set light
    bpy.ops.object.light_add(type='SUN', radius=1, align='WORLD', location=(locx, locy, locz + 10), scale=(1, 1, 1))

    bpy.ops.mesh.primitive_plane_add(size=50, enter_editmode=False, align='WORLD', location=(-locx, -locy, 0), scale=(1,1,1), rotation=(deg_to_radians(90), 0, deg_to_radians(-45)))

    scene.cycles.device = 'GPU'
    scene.cycles.progressive = 'BRANCHED_PATH'
    scene.cycles.subsurface_samples = 5
    scene.cycles.aa_samples = 64

    def rotate_piece(x, y, z):
        deselect_all()
        piece.select_set(True)
        override=bpy.context.copy()
        override['area']=[a for a in bpy.context.screen.areas if a.type=="VIEW_3D"][0]
        bpy.ops.transform.rotate(override, value=x, orient_axis='X')
        bpy.ops.transform.rotate(override, value=y, orient_axis='Y')
        bpy.ops.transform.rotate(override, value=z, orient_axis='Z')

    for i in range(iterations):
        rotate_piece(random_radian(), random_radian(), random_radian())
        bpy.context.scene.render.filepath = os.path.join(outPath, f"{model[:-4]}_{i}")
        bpy.ops.render.render(write_still = True)

def gen_many_pics(modelDir, outputDir, quantity, res):
    allModels = os.listdir(modelDir)
    for daModel in allModels:
        modelFolder = os.path.join(outputDir, f"{daModel[:-4]}")
        if os.path.isdir(modelFolder) == False:
            os.mkdir(modelFolder)
        if len(os.listdir(modelFolder)) < (quantity - 1):
            gen_pics(daModel, 32, modelDir, modelFolder, res)

gen_many_pics("/home/spencer/ldraw/parts/", "/home/spencer/Documents/GitHub/nexus/tools/renders/", 32, 128)
