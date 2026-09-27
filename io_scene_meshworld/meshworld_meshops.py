"""Import/export Hamsterball .MESH model files (Blender side).

Format I/O lives in meshworld_mesh (pure python, no bpy). This module
only converts between parsed groups and Blender objects.
"""
import bpy
import os
from mathutils import Vector

from . import meshworld_format as fmt
from . import meshworld_mesh as meshio
from .meshworld_material import (
    make_material,
    get_meshworld_material_data,
    default_material_data,
)
from .meshworld_export import (
    generate_vertex_strips,
    strip_blender_suffix,
    show_warning,
    write_textures,
)


def _triangulate_strip(verts):
    """Yield triangles from one inline-vert strip, game winding order."""
    n = len(verts)
    for i in range(n - 2):
        if i % 2 == 0:
            yield (verts[i + 2], verts[i + 1], verts[i])
        else:
            yield (verts[i + 1], verts[i + 2], verts[i])


def import_mesh(filepath, custom_texture_dir=""):
    with open(filepath, "rb") as f:
        data = f.read()
    groups, _bbox_min, _bbox_max = meshio.read_mesh(data)

    base = os.path.basename(filepath)
    if "." in base:
        base = base[:base.rfind(".")]
    coll = bpy.data.collections.new(base or "Mesh")
    bpy.context.scene.collection.children.link(coll)

    for g in groups:
        name = g["name"] or "Group"
        all_verts = []  # (pos, normal, uv)
        all_faces = []
        vert_index_map = {}

        for s in g["strips"]:
            for tri in _triangulate_strip(s["verts"]):
                face = []
                for v in tri:
                    key = (
                        round(v["X"], 6), round(v["Y"], 6), round(v["Z"], 6),
                        round(v["NX"], 6), round(v["NY"], 6), round(v["NZ"], 6),
                        round(v["U"], 6), round(v["V"], 6),
                    )
                    if key not in vert_index_map:
                        pos = fmt.convert_in_vertex((v["X"], v["Y"], v["Z"]))
                        norm = fmt.normal_convert_in_vertex((v["NX"], v["NY"], v["NZ"]))
                        vert_index_map[key] = len(all_verts)
                        # Game textures are D3D top-left origin; Blender UVs
                        # are OpenGL bottom-left. Flip V so the preview matches.
                        all_verts.append((pos, norm, (v["U"], 1.0 - v["V"])))
                    face.append(vert_index_map[key])
                all_faces.append(tuple(face))

        if not all_faces:
            continue

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([v[0] for v in all_verts], [], all_faces)
        mesh.update()
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        mesh.update()

        uv_layer = mesh.uv_layers.new(name="UVMap")
        for face in mesh.polygons:
            for loop_idx in face.loop_indices:
                vert_idx = mesh.loops[loop_idx].vertex_index
                uv_layer.data[loop_idx].uv = all_verts[vert_idx][2]

        obj = bpy.data.objects.new(name, mesh)
        coll.objects.link(obj)

        texture_path = fmt.find_texture_path(g["texture"], filepath, custom_texture_dir)
        mat = make_material(
            name=name,
            diffuse=g["diffuse"],
            ambient=g["ambient"],
            specular=g["specular"],
            emissive=g["emissive"],
            power=g["power"],
            has_reflection=g["has_reflection"],
            texture_path=texture_path,
            texture_name=g["texture"],
        )
        obj.data.materials.append(mat)

    return {"FINISHED"}


def export_mesh(filepath):
    objs = [
        o for o in bpy.context.selected_objects
        if o.type == "MESH" and o.data and o.data.polygons
    ]
    if not objs:
        show_warning("MESH Export",
                     "Select at least one mesh object to export.")
        return

    # Scene order for determinism
    order = {o.name: i for i, o in enumerate(bpy.context.scene.objects)}
    objs.sort(key=lambda o: order.get(o.name, 0))

    groups = []
    all_file_pos = []

    for obj in objs:
        local = _export_object_geometry(obj)
        if not local:
            continue
        mat = obj.data.materials[0] if obj.data.materials else None
        mat_data = (get_meshworld_material_data(mat) if mat
                    else default_material_data())
        strips = []
        for strip in generate_vertex_strips(local["triangles"]):
            tc = len(strip) - 2
            if tc < 1:
                continue
            strips.append({
                "triangle_count": tc,
                "verts": [local["file_verts"][i] for i in strip],
            })
        if not strips:
            continue
        all_file_pos.extend(
            (v["X"], v["Y"], v["Z"]) for s in strips for v in s["verts"]
        )
        groups.append({
            "name": strip_blender_suffix(obj.name),
            "center": local["center"],
            "ambient": mat_data["ambient"],
            "diffuse": mat_data["diffuse"],
            "specular": mat_data["specular"],
            "emissive": mat_data["emissive"],
            "power": mat_data["power"],
            "has_reflection": mat_data["has_reflection"],
            "texture": mat_data["texture"] or "",
            "strips": strips,
        })

    if not groups:
        show_warning("MESH Export", "Selected objects have no geometry.")
        return

    xs = [p[0] for p in all_file_pos]
    ys = [p[1] for p in all_file_pos]
    zs = [p[2] for p in all_file_pos]
    # meshio.write_mesh expects Blender-order triples, converts to file order.
    bbox_min = (min(xs), min(ys), min(zs))
    bbox_max = (max(xs), max(ys), max(zs))

    with open(filepath, "wb") as f:
        meshio.write_mesh(f, groups, bbox_min, bbox_max)

    write_textures(filepath, objs)


def _export_object_geometry(obj):
    """Flatten one Blender mesh object into .MESH file-space verts."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    if not mesh or not mesh.polygons:
        eval_obj.to_mesh_clear()
        return None

    mesh.calc_loop_triangles()
    uv_layer = mesh.uv_layers.active
    world_matrix = obj.matrix_world
    world_n3 = world_matrix.to_3x3()

    local_verts = []  # (Blender-space pos, normal, uv)
    vert_map = {}
    triangles = []

    for tri in mesh.loop_triangles:
        face = []
        for loop_index in tri.loops:
            v = mesh.vertices[mesh.loops[loop_index].vertex_index]
            wpos = world_matrix @ Vector(v.co)
            wno = (world_n3 @ Vector(mesh.loops[loop_index].normal)).normalized()
            if uv_layer:
                uv = tuple(uv_layer.data[loop_index].uv)
            else:
                uv = (1.0, 1.0)
            pos = tuple(wpos)
            normal = tuple(wno)
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

    file_verts = []
    for pos, normal, uv in local_verts:
        fp = fmt.convert_out_vertex(pos)
        fn = fmt.normal_convert_out_vertex(normal)
        file_verts.append({
            "X": fp[0], "Y": fp[1], "Z": fp[2],
            "NX": fn[0], "NY": fn[1], "NZ": fn[2],
            # Flip V back to D3D top-left origin (see import).
            "U": uv[0], "V": 1.0 - uv[1],
        })

    n = len(local_verts)
    center = (
        sum(v[0][0] for v in local_verts) / n,
        sum(v[0][1] for v in local_verts) / n,
        sum(v[0][2] for v in local_verts) / n,
    )
    return {"triangles": triangles, "file_verts": file_verts, "center": center}
