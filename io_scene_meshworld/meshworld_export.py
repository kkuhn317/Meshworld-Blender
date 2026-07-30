"""Export Blender scene to MESHWORLD."""
import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix

from . import meshworld_format as fmt
from .meshworld_material import get_meshworld_material_data, normalize_texture_name


FOLDER_NAMES = {"RefPoints", "Splines", "Lights", "Level_Root", "SceneMetadata"}


def export_meshworld(filepath):
    scene = bpy.context.scene

    # Collect ref points, splines, lights, geometry objects
    ref_points = []
    splines = []
    lights = []
    geom_objects = []

    for obj in scene.objects:
        if obj.name in FOLDER_NAMES:
            continue
        if obj.meshworld.is_ref_point:
            ref_points.append(obj)
        elif obj.meshworld.is_spline:
            splines.append(obj)
        elif obj.meshworld.is_light:
            lights.append(obj)
        elif obj.type == "MESH" and obj.data and obj.data.polygons:
            geom_objects.append(obj)

    with open(filepath, "wb") as f:
        writer = fmt.MeshWorldWriter(f)

        write_ref_points(writer, ref_points)
        write_splines(writer, splines)
        write_lights(writer, lights)
        write_background_and_ambient(writer, scene)
        write_vertices_and_meshes(writer, geom_objects, scene)

    # Write textures to a textures/ folder next to the MESHWORLD
    write_textures(filepath, geom_objects)


def write_ref_points(writer, ref_points):
    writer.write_s32(len(ref_points))
    for obj in ref_points:
        name = obj.name
        if name.startswith("REF:"):
            name = name[4:]
        name = strip_blender_suffix(name)
        writer.write_string(name)

        pos = obj.location
        writer.write_float(pos.x * 50.0)
        writer.write_float(pos.y * 50.0)
        writer.write_float(-pos.z * 50.0)

        # Rotation: use object rotation Euler ZXY to match (RotZ, RotY, RotX)
        euler = obj.rotation_euler.copy()
        if obj.rotation_mode in {"ZXY", "ZYX", "YXZ", "XYZ", "XZY", "YZX"}:
            euler = obj.matrix_world.to_euler(obj.rotation_mode)
        else:
            euler = obj.matrix_world.to_euler("ZXY")

        writer.write_float(math.degrees(euler.z))
        writer.write_float(math.degrees(euler.y))
        writer.write_float(math.degrees(euler.x))

        # Material properties stored on object
        has_color = 1 if "mw_has_reflection" in obj or "mw_diffuse" in obj else 0
        # The C# code always wrote hasColor=1 for REF:FLAG/BRIDGE/SMALLFLAG
        if obj.name.startswith("REF:FLAG") or obj.name.startswith("REF:BRIDGE") or obj.name.startswith("REF:SMALLFLAG"):
            has_color = 1

        writer.write_s32(has_color)
        if has_color:
            ambient = tuple(obj.get("mw_ambient", [0.9921, 0.9921, 0.9921, 1.0]))
            diffuse = tuple(obj.get("mw_diffuse", [0.9921, 0.9921, 0.9921, 1.0]))
            specular = tuple(obj.get("mw_specular", [0.0, 0.0, 0.0, 1.0]))
            emissive = tuple(obj.get("mw_emissive", [0.0, 0.0, 0.0, 1.0]))
            power = float(obj.get("mw_power", 10.0))
            has_reflection = int(obj.get("mw_has_reflection", 0))
            texture = obj.get("mw_texture", None)

            writer.write_vec4(ambient)
            writer.write_vec4(diffuse)
            writer.write_vec4(specular)
            writer.write_vec4(emissive)
            writer.write_float(power)
            writer.write_s32(has_reflection)

            if texture:
                writer.write_s32(1)
                writer.write_string(texture)
            else:
                writer.write_s32(0)


def write_splines(writer, splines):
    writer.write_s32(len(splines))
    for obj in splines:
        name = obj.name
        if name.startswith("C:"):
            name = name[2:]
        name = strip_blender_suffix(name)
        writer.write_string(name)

        # Read curve points
        curve = obj.data
        pts = []
        for spline in curve.splines:
            for p in spline.points:
                pos = obj.matrix_world @ Vector(p.co[:3])
                pts.append(fmt.convert_out(pos))

        writer.write_s32(len(pts))
        for p in pts:
            writer.write_float(p[0])
            writer.write_float(p[1])
            writer.write_float(p[2])


def write_lights(writer, lights):
    writer.write_s32(len(lights))
    for obj in lights:
        light_data = obj.data
        writer.write_s32(obj.meshworld.light_type)

        pos = obj.location
        writer.write_float(pos.x * 50.0)
        writer.write_float(pos.y * 50.0)
        writer.write_float(-pos.z * 50.0)

        # Direction: sun points down -Z in local space
        direction = obj.matrix_world @ Vector((0, 0, -1))
        writer.write_float(direction.x * 50.0)
        writer.write_float(direction.y * 50.0)
        writer.write_float(-direction.z * 50.0)

        col = light_data.color
        writer.write_float(col[0])
        writer.write_float(col[1])
        writer.write_float(col[2])


def write_background_and_ambient(writer, scene):
    bg = scene.meshworld.background_color
    amb = scene.meshworld.ambient_color
    writer.write_float(bg[0])
    writer.write_float(bg[1])
    writer.write_float(bg[2])
    writer.write_float(amb[0])
    writer.write_float(amb[1])
    writer.write_float(amb[2])


def write_vertices_and_meshes(writer, geom_objects, scene):
    verts = []
    meshes = []

    for obj in geom_objects:
        mesh_data = export_object_geometry(obj, verts)
        if mesh_data:
            meshes.append(mesh_data)

    writer.write_s32(len(verts))
    for v in verts:
        writer.write_vertex(v)

    root_min = scene.meshworld.root_bound_min
    root_max = scene.meshworld.root_bound_max
    writer.write_float(root_min[0])
    writer.write_float(root_min[1])
    writer.write_float(root_min[2])
    writer.write_float(root_max[0])
    writer.write_float(root_max[1])
    writer.write_float(root_max[2])

    writer.write_s32(len(meshes))
    for m in meshes:
        # Bounding box
        writer.write_float(root_min[0])
        writer.write_float(root_min[1])
        writer.write_float(root_min[2])
        writer.write_float(root_max[0])
        writer.write_float(root_max[1])
        writer.write_float(root_max[2])

        writer.write_s32(0)  # no children
        writer.write_s32(len(m["geoms"]))

        for g in m["geoms"]:
            writer.write_string(g["name"])
            writer.write_vec4(g["ambient"])
            writer.write_vec4(g["diffuse"])
            writer.write_vec4(g["specular"])
            writer.write_vec4(g["emissive"])
            writer.write_float(g["power"])
            writer.write_s32(g["has_reflection"])

            if g["texture"]:
                writer.write_s32(1)
                writer.write_string(g["texture"])
            else:
                writer.write_s32(0)

            writer.write_s32(len(g["strips"]))
            for s in g["strips"]:
                writer.write_s32(s["triangle_count"])
                writer.write_s32(s["vertex_offset"])


def export_object_geometry(obj, global_verts):
    """Flatten one Blender mesh object into MESHWORLD vertex/strip data."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    if not mesh or not mesh.polygons:
        eval_obj.to_mesh_clear()
        return None

    mesh.calc_loop_triangles()
    mesh.calc_normals_split()

    uv_layer = mesh.uv_layers.active

    # Collect unique local vertices
    local_verts = []  # list of (pos, normal, uv)
    vert_map = {}
    triangles = []  # list of (i0, i1, i2) into local_verts

    for tri in mesh.loop_triangles:
        face = []
        for loop_index in tri.loops:
            v = mesh.vertices[mesh.loops[loop_index].vertex_index]
            pos = tuple(v.co)
            normal = tuple(mesh.loops[loop_index].normal)
            if uv_layer:
                uv = tuple(uv_layer.data[loop_index].uv)
            else:
                uv = (1.0, 1.0)

            key = (round(pos[0], 6), round(pos[1], 6), round(pos[2], 6),
                   round(normal[0], 6), round(normal[1], 6), round(normal[2], 6),
                   round(uv[0], 6), round(uv[1], 6))
            if key not in vert_map:
                vert_map[key] = len(local_verts)
                local_verts.append((pos, normal, uv))
            face.append(vert_map[key])
        triangles.append(tuple(face))

    eval_obj.to_mesh_clear()

    if not triangles:
        return None

    # Stripify
    strips = generate_vertex_strips(triangles)

    # Build geom
    material = obj.data.materials[0] if obj.data.materials else None
    mat_data = get_meshworld_material_data(material)

    g = {
        "name": strip_blender_suffix(obj.name),
        "ambient": mat_data["ambient"],
        "diffuse": mat_data["diffuse"],
        "specular": mat_data["specular"],
        "emissive": mat_data["emissive"],
        "power": mat_data["power"],
        "has_reflection": mat_data["has_reflection"],
        "texture": mat_data["texture"],
        "strips": [],
    }

    world_matrix = obj.matrix_world
    for strip in strips:
        vertex_offset = len(global_verts)
        triangle_count = len(strip) - 2
        g["strips"].append({
            "triangle_count": triangle_count,
            "vertex_offset": vertex_offset,
        })
        for local_idx in strip:
            pos, normal, uv = local_verts[local_idx]
            world_pos = world_matrix @ Vector(pos)
            world_no = (world_matrix.to_3x3() @ Vector(normal)).normalized()

            file_pos = fmt.convert_out_vertex(world_pos)
            file_no = fmt.normal_convert_out_vertex(world_no)

            global_verts.append({
                "X": file_pos[0],
                "Y": file_pos[1],
                "Z": file_pos[2],
                "NX": file_no[0],
                "NY": file_no[1],
                "NZ": file_no[2],
                "U": uv[0],
                "V": uv[1],
            })

    return {"name": g["name"], "geoms": [g]}


def generate_vertex_strips(triangles):
    """Convert a list of triangles into triangle strips."""
    if not triangles:
        return []

    # Build edge -> triangle map
    edge_to_tris = {}

    def add_edge(v1, v2, tri_idx):
        key = (min(v1, v2), max(v1, v2))
        edge_to_tris.setdefault(key, []).append(tri_idx)

    for i, tri in enumerate(triangles):
        add_edge(tri[0], tri[1], i)
        add_edge(tri[1], tri[2], i)
        add_edge(tri[2], tri[0], i)

    unvisited = set(range(len(triangles)))
    strips = []

    while unvisited:
        # Start with triangle with fewest unvisited neighbors
        best_tri = -1
        min_neighbors = float("inf")
        for idx in unvisited:
            tri = triangles[idx]
            n = 0
            for edge in [(tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])]:
                key = (min(edge[0], edge[1]), max(edge[0], edge[1]))
                for t in edge_to_tris.get(key, []):
                    if t != idx and t in unvisited:
                        n += 1
                        break
            if n < min_neighbors:
                min_neighbors = n
                best_tri = idx

        start_tri = triangles[best_tri]
        start_perms = [
            [start_tri[2], start_tri[1], start_tri[0]],
            [start_tri[1], start_tri[0], start_tri[2]],
            [start_tri[0], start_tri[2], start_tri[1]],
        ]

        best_strip = None
        best_path = None
        for perm in start_perms:
            strip = list(perm)
            path = [best_tri]
            temp_visited = {best_tri}
            while True:
                va = strip[-2]
                vb = strip[-1]
                key = (min(va, vb), max(va, vb))
                next_tri = -1
                for t in edge_to_tris.get(key, []):
                    if t in unvisited and t not in temp_visited:
                        next_tri = t
                        break
                if next_tri == -1:
                    break
                nt = triangles[next_tri]
                vnew = nt[0]
                if nt[1] != va and nt[1] != vb:
                    vnew = nt[1]
                if nt[2] != va and nt[2] != vb:
                    vnew = nt[2]
                strip.append(vnew)
                path.append(next_tri)
                temp_visited.add(next_tri)

            if best_strip is None or len(strip) > len(best_strip):
                best_strip = strip
                best_path = path

        strips.append(best_strip)
        for t in best_path:
            unvisited.discard(t)

    return strips


def write_textures(filepath, geom_objects):
    """Copy used textures to textures/ next to the MESHWORLD file."""
    out_dir = os.path.dirname(filepath)
    tex_dir = os.path.join(out_dir, "textures")
    os.makedirs(tex_dir, exist_ok=True)

    copied = set()
    for obj in geom_objects:
        for mat in obj.data.materials:
            if not mat or not mat.use_nodes:
                continue
            tex_name = None
            # Prefer custom property
            if hasattr(mat, "meshworld") and mat.meshworld.meshworld_texture:
                tex_name = mat.meshworld.meshworld_texture
            # Find image node
            if not tex_name:
                for node in mat.node_tree.nodes:
                    if node.type == "TEX_IMAGE" and node.image:
                        tex_name = os.path.basename(node.image.filepath)
                        break
            if not tex_name:
                continue

            norm = normalize_texture_name(tex_name)
            if norm in copied:
                continue
            copied.add(norm)

            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    src = node.image.filepath
                    if src.startswith("//"):
                        src = bpy.path.abspath(src)
                    if src and os.path.isfile(src):
                        ext = os.path.splitext(src)[1].lower() or ".png"
                        dst = os.path.join(tex_dir, os.path.splitext(norm)[0] + ext)
                        try:
                            import shutil
                            shutil.copy2(src, dst)
                        except Exception:
                            pass
                    break


def strip_blender_suffix(name):
    if not name:
        return name
    dot = name.rfind(".")
    if dot > 0:
        after = name[dot + 1 :]
        if after.isdigit():
            return name[:dot]
    return name
