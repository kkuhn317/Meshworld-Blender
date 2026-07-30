"""Material creation and property application."""
import bpy
import os
from . import meshworld_format as fmt


def make_material(name, diffuse, ambient, specular, emissive, power, has_reflection, texture_path=None, texture_name=""):
    """Create a Blender material matching a MESHWORLD geom."""
    mat = bpy.data.materials.new(name=name or "Material")
    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links

    # Clear default nodes except Principled BSDF and output
    principled = None
    output = None
    for node in list(nodes):
        if node.type == "BSDF_PRINCIPLED":
            principled = node
        elif node.type == "OUTPUT_MATERIAL":
            output = node
        else:
            nodes.remove(node)

    if principled is None:
        principled = nodes.new("ShaderNodeBsdfPrincipled")
    if output is None:
        output = nodes.new("ShaderNodeOutputMaterial")

    principled.location = (0, 0)
    output.location = (300, 0)
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    # Diffuse -> Base Color
    principled.inputs["Base Color"].default_value = (
        diffuse[0], diffuse[1], diffuse[2], diffuse[3]
    )

    # Emissive
    if any(emissive[:3]):
        principled.inputs["Emission Color"].default_value = (
            emissive[0], emissive[1], emissive[2], 1.0
        )
        principled.inputs["Emission Strength"].default_value = max(emissive[:3]) or 1.0

    # Metallic/roughness approximation for preview (not exported, custom props are)
    avg_spec = (specular[0] + specular[1] + specular[2]) / 3.0
    roughness = max(0.0, 1.0 - (power / 100.0))
    principled.inputs["Metallic"].default_value = avg_spec
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Specular IOR Level"].default_value = min(avg_spec, 0.5)

    # Custom Hamsterball properties (authoritative for export)
    mw = mat.meshworld
    mw.specular = specular
    mw.ambient = ambient
    mw.emissive = emissive
    mw.power = power
    mw.has_reflection = bool(has_reflection)
    if texture_name:
        mw.meshworld_texture = texture_name

    # Texture
    if texture_path and os.path.isfile(texture_path):
        tex_image = nodes.new("ShaderNodeTexImage")
        tex_image.location = (-300, 0)
        try:
            img = bpy.data.images.load(texture_path, check_existing=True)
            tex_image.image = img
        except Exception:
            pass
        links.new(tex_image.outputs["Color"], principled.inputs["Base Color"])
        # Store texture name without extension for export
        if texture_name:
            mw.meshworld_texture = texture_name

    return mat


def get_meshworld_texture_name(mat):
    """Return the texture name to write for a material, or None."""
    if not mat or not mat.use_nodes:
        return None

    # Authoritative: custom property
    mw_tex = getattr(mat, "meshworld", None)
    if mw_tex and mw_tex.meshworld_texture:
        name = mw_tex.meshworld_texture
        return normalize_texture_name(name)

    # Fallback: image node
    for node in mat.node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.image:
            name = os.path.basename(node.image.filepath)
            return normalize_texture_name(name)
    return None


def normalize_texture_name(name):
    if not name:
        return None
    base = name
    for ext in (".bmp", ".png", ".tga", ".jpg", ".jpeg"):
        if base.lower().endswith(ext):
            base = base[: -len(ext)]
            break
    # The C# code forced .bmp for checker textures, .png otherwise
    if base in {
        "BlueChecker",
        "BrightGreenChecker",
        "GreenChecker",
        "OrangeChecker",
        "PinkChecker",
        "PurpleChecker",
        "RedChecker",
    }:
        return base + ".bmp"
    return base + ".png"


def get_meshworld_material_data(mat):
    """Collect the Hamsterball material values for export."""
    mw = getattr(mat, "meshworld", None)
    if mw:
        return {
            "diffuse": tuple(mat.diffuse_color),
            "ambient": tuple(mw.ambient),
            "specular": tuple(mw.specular),
            "emissive": tuple(mw.emissive),
            "power": mw.power,
            "has_reflection": 1 if mw.has_reflection else 0,
            "texture": get_meshworld_texture_name(mat),
        }

    # No custom props: derive from Principled BSDF
    principled = None
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                principled = node
                break

    if principled is None:
        return default_material_data(mat.diffuse_color)

    base = tuple(principled.inputs["Base Color"].default_value)
    metallic = principled.inputs["Metallic"].default_value
    roughness = principled.inputs["Roughness"].default_value
    spec = tuple([metallic] * 3 + [1.0])
    power = max(1.0, (1.0 - roughness) * 100.0)
    return {
        "diffuse": base,
        "ambient": base,
        "specular": spec,
        "emissive": (0.0, 0.0, 0.0, 1.0),
        "power": power,
        "has_reflection": 0,
        "texture": get_meshworld_texture_name(mat),
    }


def default_material_data(diffuse=(1.0, 1.0, 1.0, 1.0)):
    return {
        "diffuse": diffuse,
        "ambient": (0.9921, 0.9921, 0.9921, 1.0),
        "specular": (0.0, 0.0, 0.0, 1.0),
        "emissive": (0.0, 0.0, 0.0, 1.0),
        "power": 10.0,
        "has_reflection": 0,
        "texture": None,
    }
