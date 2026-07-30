"""Import MESHWORLD files into Blender."""
import bpy
import bmesh
import math
from mathutils import Matrix, Quaternion, Vector
import os

from . import meshworld_format as fmt
from .meshworld_material import make_material


def import_meshworld(filepath, custom_texture_dir=""):
    with open(filepath, "rb") as f:
        data = f.read()
    reader = fmt.MeshWorldReader(data)

    ref_points = read_ref_points(reader)
    splines = read_splines(reader)
    lights = read_lights(reader)

    bg = reader.read_vec3()
    amb = reader.read_vec3()
    scene = bpy.context.scene
    scene.meshworld.background_color = bg
    scene.meshworld.ambient_color = amb

    vert_count = reader.read_s32()
    verts = []
    for _ in range(vert_count):
        v = {
            "X": reader.read_float(),
            "Y": reader.read_float(),
            "Z": reader.read_float(),
            "NX": reader.read_float(),
            "NY": reader.read_float(),
            "NZ": reader.read_float(),
            "U": reader.read_float(),
            "V": reader.read_float(),
        }
        verts.append(v)

    root_min = reader.read_vec3()
    root_max = reader.read_vec3()
    scene.meshworld.root_bound_min = root_min
    scene.meshworld.root_bound_max = root_max

    top_level_count = reader.read_s32()
    meshes = []
    for _ in range(top_level_count):
        meshes.append(read_mesh_node(reader))

    # Build geometry meshes
    for m in meshes:
        build_geometry_mesh(m, verts, filepath, custom_texture_dir)

    # Build ref points as empties
    for rp in ref_points:
        build_ref_point(rp)

    # Build splines as curves
    for sp in splines:
        build_spline(sp)

    # Build lights as sun lights
    for lt in lights:
        build_light(lt)

    return {"FINISHED"}


def read_ref_points(reader):
    count = reader.read_s32()
    points = []
    for _ in range(count):
        name = "REF:" + reader.read_string()
        pos = fmt.convert_in(reader.read_vec3())
        rot = reader.read_vec3()  # (RotZ, RotY, RotX) in degrees

        has_color = reader.read_s32()
        props = None
        if has_color == 1:
            props = {
                "ambient": reader.read_vec4(),
                "diffuse": reader.read_vec4(),
                "specular": reader.read_vec4(),
                "emissive": reader.read_vec4(),
                "power": reader.read_float(),
                "has_reflection": reader.read_s32(),
            }
            has_image = reader.read_s32()
            if has_image == 1:
                props["texture"] = reader.read_string()

        points.append({
            "name": name,
            "position": pos,
            "rotation": rot,
            "properties": props,
        })
    return points


def read_splines(reader):
    count = reader.read_s32()
    splines = []
    for _ in range(count):
        name = "C:" + reader.read_string()
        pt_count = reader.read_s32()
        pts = []
        for _ in range(pt_count):
            pts.append(fmt.convert_in(reader.read_vec3()))
        splines.append({"name": name, "points": pts})
    return splines


def read_lights(reader):
    count = reader.read_s32()
    lights = []
    for _ in range(count):
        lt = {"type": reader.read_s32()}
        lt["position"] = fmt.convert_in(reader.read_vec3())
        lt["direction"] = fmt.convert_in(reader.read_vec3())
        lt["color"] = reader.read_vec3()
        lights.append(lt)
    return lights


def read_mesh_node(reader):
    reader.read_bytes(24)  # bounding box
    child_count = reader.read_s32()
    geom_count = 0
    if child_count == 0:
        geom_count = reader.read_s32()

    m = {"name": "Folder", "geoms": [], "children": []}

    for g_idx in range(geom_count):
        g = {
            "name": reader.read_string(),
            "ambient": reader.read_vec4(),
            "diffuse": reader.read_vec4(),
            "specular": reader.read_vec4(),
            "emissive": reader.read_vec4(),
            "power": reader.read_float(),
            "has_reflection": reader.read_s32(),
            "strips": [],
        }
        if g_idx == 0:
            m["name"] = "Chunk_" + g["name"]

        has_texture = reader.read_s32()
        if has_texture != 0:
            g["texture"] = reader.read_string()

        strip_count = reader.read_s32()
        for _ in range(strip_count):
            g["strips"].append({
                "triangle_count": reader.read_s32(),
                "vertex_offset": reader.read_s32(),
            })
        m["geoms"].append(g)

    for _ in range(child_count):
        m["children"].append(read_mesh_node(reader))
    return m


def build_geometry_mesh(m, verts, filepath, custom_texture_dir):
    for g in m["geoms"]:
        name = g["name"] or m["name"]

        # Gather triangles from strips
        all_verts = []  # list of (pos, normal, uv)
        all_faces = []  # list of (i0, i1, i2)
        vert_index_map = {}  # dedupe by full vertex data

        for s in g["strips"]:
            tc = s["triangle_count"]
            off = s["vertex_offset"]
            for i in range(tc):
                idx0 = off + i
                idx1 = off + i + 1
                idx2 = off + i + 2
                if idx2 >= len(verts):
                    continue
                if i % 2 == 0:
                    tri = (idx2, idx1, idx0)
                else:
                    tri = (idx1, idx2, idx0)
                face = []
                for vi in tri:
                    v = verts[vi]
                    key = (
                        round(v["X"], 6),
                        round(v["Y"], 6),
                        round(v["Z"], 6),
                        round(v["NX"], 6),
                        round(v["NY"], 6),
                        round(v["NZ"], 6),
                        round(v["U"], 6),
                        round(v["V"], 6),
                    )
                    if key not in vert_index_map:
                        pos = fmt.convert_in_vertex((v["X"], v["Y"], v["Z"]))
                        norm = fmt.normal_convert_in_vertex((v["NX"], v["NY"], v["NZ"]))
                        uv = (v["U"], v["V"])
                        vert_index_map[key] = len(all_verts)
                        all_verts.append((pos, norm, uv))
                    face.append(vert_index_map[key])
                all_faces.append(tuple(face))

        if not all_faces:
            continue

        # Create mesh
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(
            [v[0] for v in all_verts],
            [],
            all_faces,
        )
        mesh.update()

        # Normals
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        mesh.update()

        # UVs
        uv_layer = mesh.uv_layers.new(name="UVMap")
        for face in mesh.polygons:
            for loop_idx in face.loop_indices:
                vert_idx = mesh.loops[loop_idx].vertex_index
                uv_layer.data[loop_idx].uv = all_verts[vert_idx][2]

        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)

        # Material
        texture_name = g.get("texture", "")
        texture_path = fmt.find_texture_path(texture_name, filepath, custom_texture_dir)
        mat = make_material(
            name=name,
            diffuse=g["diffuse"],
            ambient=g["ambient"],
            specular=g["specular"],
            emissive=g["emissive"],
            power=g["power"],
            has_reflection=g["has_reflection"],
            texture_path=texture_path,
            texture_name=texture_name,
        )
        obj.data.materials.append(mat)

    # Recurse into octree children
    for child in m["children"]:
        build_geometry_mesh(child, verts, filepath, custom_texture_dir)


def build_ref_point(rp):
    bpy.ops.object.empty_add(type="ARROWS", location=rp["position"])
    obj = bpy.context.active_object
    obj.name = rp["name"]
    obj.empty_display_size = 0.4

    # Rotation: stored as (RotZ, RotY, RotX) degrees
    rot = rp["rotation"]
    obj.rotation_euler = (
        math.radians(rot[2]),  # X
        math.radians(rot[1]),  # Y
        math.radians(rot[0]),  # Z
    )
    obj.rotation_mode = "ZXY"

    obj.meshworld.is_ref_point = True
    obj.meshworld.ref_rotation_x = rot[2]
    obj.meshworld.ref_rotation_y = rot[1]
    obj.meshworld.ref_rotation_z = rot[0]

    props = rp["properties"]
    if props:
        # Store ref-point material properties on the empty via custom object props
        obj["mw_ambient"] = list(props["ambient"])
        obj["mw_diffuse"] = list(props["diffuse"])
        obj["mw_specular"] = list(props["specular"])
        obj["mw_emissive"] = list(props["emissive"])
        obj["mw_power"] = props["power"]
        obj["mw_has_reflection"] = props["has_reflection"]
        if "texture" in props:
            obj["mw_texture"] = props["texture"]


def build_spline(sp):
    curve = bpy.data.curves.new(sp["name"], type="CURVE")
    curve.dimensions = "3D"
    spline = curve.splines.new("NURBS")
    spline.points.add(len(sp["points"]) - 1)
    for i, pt in enumerate(sp["points"]):
        spline.points[i].co = (pt[0], pt[1], pt[2], 1.0)

    obj = bpy.data.objects.new(sp["name"], curve)
    bpy.context.collection.objects.link(obj)
    obj.meshworld.is_spline = True


def build_light(lt):
    light_data = bpy.data.lights.new(name="Light", type="SUN")
    light_data.color = lt["color"]
    light_data.energy = 1.0

    obj = bpy.data.objects.new("Light", light_data)
    bpy.context.collection.objects.link(obj)
    obj.location = lt["position"]

    # Direction is stored as a point; make the sun point from position toward direction point
    dir_vec = Vector(lt["direction"]) - Vector(lt["position"])
    if dir_vec.length > 0.0001:
        obj.rotation_euler = dir_vec.to_track_quat("-Z", "Y").to_euler()

    obj.meshworld.is_light = True
    obj.meshworld.light_type = lt["type"]
