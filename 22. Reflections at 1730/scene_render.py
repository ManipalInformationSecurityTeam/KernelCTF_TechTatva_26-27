# Run with: blender -b -P scene_render.py  (from the project folder)
import bpy
import bmesh
import math
import os
from mathutils import Vector

PROJECT_DIR = os.getcwd()
OUT_PATH = os.path.join(PROJECT_DIR, "render_raw.png")

WALL_FRONT_Y = 4.15
SKU_TEXT_SIZE = 0.13
TAG_W, TAG_H = 0.72, 0.30


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_material(name, rgba, emit_strength=0.0, emit_color=None, roughness=0.6):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = roughness
    if emit_strength > 0:
        bsdf.inputs["Emission Color"].default_value = emit_color or rgba
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    return mat


def add_box(name, loc, size, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    obj.data.materials.append(mat)
    return obj


def add_text(name, body, loc, size, mat, align="CENTER"):
    bpy.ops.object.text_add(location=loc, rotation=(math.radians(90), 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.body = body
    obj.data.size = size
    obj.data.align_x = align
    obj.data.align_y = "CENTER"
    obj.data.extrude = 0.004
    obj.data.materials.append(mat)
    return obj


def lathe(name, profile, loc, mat, segments=24):
    """Build a solid of revolution from (radius, z) points. Gives tapered,
    rounded forms like bottles, bins, and bodies instead of raw cylinders."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        ring = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for j in range(len(rings) - 1):
        for i in range(segments):
            a = rings[j][i]
            b = rings[j][(i + 1) % segments]
            c = rings[j + 1][(i + 1) % segments]
            d = rings[j + 1][i]
            bm.faces.new((a, b, c, d))
    if profile[0][0] > 0:
        bm.faces.new(rings[0])
    if profile[-1][0] > 0:
        bm.faces.new(rings[-1][::-1])
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(mat)
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
    return obj


def build_person(loc, mat_cloth, mat_skin):
    x, y, z0 = loc
    lathe("leg_l", [(0.09, 0.0), (0.085, 0.45), (0.07, 0.85)], (x - 0.09, y, z0), mat_cloth)
    lathe("leg_r", [(0.09, 0.0), (0.085, 0.45), (0.07, 0.85)], (x + 0.09, y, z0), mat_cloth)
    lathe("torso", [(0.08, 0.85), (0.19, 1.05), (0.20, 1.35), (0.15, 1.5), (0.06, 1.55)],
          (x, y, z0), mat_cloth)
    lathe("arm_l", [(0.05, 1.45), (0.045, 1.0), (0.04, 0.72)], (x - 0.24, y, z0), mat_cloth)
    lathe("arm_r", [(0.05, 1.45), (0.045, 1.0), (0.04, 0.72)], (x + 0.24, y, z0), mat_cloth)
    lathe("neck", [(0.04, 1.52), (0.045, 1.6)], (x, y, z0), mat_skin)
    lathe("head", [(0.0, 1.6), (0.10, 1.62), (0.12, 1.72), (0.09, 1.82), (0.0, 1.84)],
          (x, y, z0), mat_skin)


def build_scene():
    mat_floor = make_material("floor", (0.05, 0.05, 0.055, 1))
    mat_wall = make_material("wall", (0.18, 0.17, 0.16, 1))
    mat_wood = make_material("wood", (0.12, 0.07, 0.04, 1))
    mat_tag = make_material("tag", (0.85, 0.85, 0.8, 1))
    mat_ink = make_material("ink", (0.02, 0.02, 0.02, 1))
    mat_empty = make_material("empty", (0.03, 0.03, 0.035, 1))
    mat_exit = make_material("exit", (0.0, 0.05, 0.0, 1), 12.0, (0.1, 1.0, 0.2, 1))
    mat_metal = make_material("metal", (0.25, 0.25, 0.27, 1), roughness=0.3)
    mat_glass = make_material("glass", (0.1, 0.12, 0.13, 1), roughness=0.1)
    mat_box = make_material("box", (0.35, 0.3, 0.25, 1))
    mat_plant = make_material("plant", (0.05, 0.14, 0.05, 1))
    mat_pot = make_material("pot", (0.2, 0.12, 0.08, 1))
    mat_red = make_material("extinguisher", (0.28, 0.04, 0.03, 1), roughness=0.4)
    mat_paper = make_material("paper", (0.6, 0.6, 0.55, 1))
    mat_cloth = make_material("cloth", (0.03, 0.03, 0.035, 1), roughness=0.9)
    mat_skin = make_material("skin", (0.18, 0.13, 0.11, 1), roughness=0.5)

    # Room
    add_box("floor", (0, 2.5, -0.05), (8, 10, 0.1), mat_floor)
    add_box("back_wall", (0, WALL_FRONT_Y + 0.05, 1.8), (8, 0.1, 3.6), mat_wall)

    # Back door, with EXIT sign above it
    door_x = -3.0
    add_box("door", (door_x, WALL_FRONT_Y - 0.01, 1.05), (0.95, 0.05, 2.1), mat_wood)
    add_text("exit_sign", "EXIT", (door_x, WALL_FRONT_Y - 0.03, 2.55), 0.22, mat_exit)

    # Shelf: 3 rows x 4 columns, reading order
    grid = [
        ["A1F3", "B7K2", "C9D4", "E0M8"],
        ["H5J1", "K3P6", None,   "T4W9"],
        ["X2Y7", "Z6N0", "L1U5", "G3V8"],
    ]
    row_z = [2.35, 1.85, 1.35]
    col_x = [-1.2, -0.4, 0.4, 1.2]
    slot_y = WALL_FRONT_Y - 0.03

    for r, z in enumerate(row_z):
        add_box(f"shelf_{r}", (0, slot_y - 0.02, z - 0.2), (3.6, 0.45, 0.05), mat_wood)
        for c, x in enumerate(col_x):
            sku = grid[r][c]
            if sku is None:
                add_box(f"empty_{r}_{c}", (x, slot_y, z), (TAG_W, 0.02, TAG_H), mat_empty)
                continue
            add_box(f"tag_{r}_{c}", (x, slot_y, z), (TAG_W, 0.02, TAG_H), mat_tag)
            add_text(f"sku_{r}_{c}", sku, (x, slot_y - 0.02, z - 0.04), SKU_TEXT_SIZE, mat_ink)

    # Display case: glass counter with a metal frame, open jewellery boxes
    counter_y = 3.2
    add_box("case_body", (0, counter_y, 0.5), (4.4, 0.6, 0.95), mat_glass)
    add_box("case_frame_top", (0, counter_y, 1.0), (4.5, 0.65, 0.05), mat_metal)
    add_box("case_frame_base", (0, counter_y, 0.03), (4.5, 0.65, 0.06), mat_metal)
    add_box("jewel_box_1", (-1.2, counter_y, 1.1), (0.36, 0.3, 0.12), mat_box, rot=(0, 0, 0.05))
    add_box("jewel_lid_1", (-1.2, counter_y, 1.2), (0.36, 0.3, 0.02), mat_box, rot=(0.5, 0, 0.05))
    add_box("jewel_box_2", (0.9, counter_y, 1.1), (0.4, 0.3, 0.14), mat_box, rot=(0, 0, -0.03))
    add_box("paper_stack", (1.7, counter_y - 0.1, 1.07), (0.4, 0.3, 0.05), mat_paper, rot=(0, 0, 0.08))

    # Potted plant: tapered pot, trunk, leaf clusters
    lathe("pot", [(0.0, 0.0), (0.22, 0.0), (0.26, 0.3), (0.24, 0.5), (0.0, 0.5)],
          (2.8, 3.5, 0.0), mat_pot)
    lathe("plant_stem", [(0.02, 0.5), (0.03, 0.9)], (2.8, 3.5, 0.0), mat_pot)
    for i, (dx, dz, s) in enumerate([(0.0, 1.0, 0.28), (-0.15, 0.85, 0.2), (0.16, 0.9, 0.22)]):
        bpy.ops.mesh.primitive_ico_sphere_add(radius=s, location=(2.8 + dx, 3.5, dz))
        leaf = bpy.context.object
        leaf.name = f"leaf_{i}"
        leaf.data.materials.append(mat_plant)
        leaf.scale = (1.0, 0.6, 1.3)

    # Wastebin: tapered body and rim
    lathe("bin", [(0.0, 0.0), (0.18, 0.0), (0.2, 0.55), (0.22, 0.6), (0.0, 0.6)],
          (-2.7, 3.6, 0.0), mat_metal)

    # Fire extinguisher: body, shoulder, neck, valve
    ext_loc = (-3.7, WALL_FRONT_Y - 0.15, 0.0)
    lathe("ext_body", [(0.0, 0.1), (0.1, 0.1), (0.11, 0.5), (0.1, 0.65), (0.06, 0.72), (0.0, 0.72)],
          ext_loc, mat_red)
    lathe("ext_valve", [(0.0, 0.72), (0.03, 0.72), (0.03, 0.8), (0.0, 0.8)], ext_loc, mat_metal)

    # Wall calendar with a card face
    add_box("calendar", (2.4, WALL_FRONT_Y - 0.08, 2.3), (0.5, 0.03, 0.6), mat_paper)

    # Cardboard box, slightly tilted
    add_box("cardboard", (-3.4, 3.3, 0.2), (0.6, 0.5, 0.4), mat_box, rot=(0, 0, 0.12))

    # Figure standing away from the wall, built from tapered parts
    build_person((2.0, 2.2, 0.0), mat_cloth, mat_skin)


def setup_lighting():
    bpy.ops.object.light_add(type="AREA", location=(0, 1.6, 2.9))
    key = bpy.context.object
    key.data.energy = 220
    key.data.size = 2.0
    key.rotation_euler = (math.radians(15), 0, 0)

    bpy.ops.object.light_add(type="POINT", location=(-2.5, 2.6, 1.6))
    fill = bpy.context.object
    fill.data.energy = 25

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.02, 0.02, 0.025, 1)
    bg.inputs["Strength"].default_value = 0.4
    bpy.context.scene.world = world


def setup_camera():
    bpy.ops.object.camera_add(location=(0, -2.6, 1.5), rotation=(math.radians(90), 0, 0))
    cam = bpy.context.object
    cam.data.lens = 26
    bpy.context.scene.camera = cam


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = OUT_PATH


if __name__ == "__main__":
    reset_scene()
    build_scene()
    setup_lighting()
    setup_camera()
    setup_render()
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {OUT_PATH}")