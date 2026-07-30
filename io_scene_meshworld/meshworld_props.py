"""Custom properties used by the add-on."""
import bpy
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Material, Object, Scene


class MeshWorldMaterialProps(bpy.types.PropertyGroup):
    specular: FloatVectorProperty(
        name="Specular",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
    )
    ambient: FloatVectorProperty(
        name="Ambient",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.9921, 0.9921, 0.9921, 1.0),
    )
    emissive: FloatVectorProperty(
        name="Emissive",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
    )
    power: FloatProperty(
        name="Power",
        description="Specular power / shininess",
        default=10.0,
        min=0.0,
        max=1000.0,
    )
    has_reflection: BoolProperty(
        name="Has Reflection",
        default=False,
    )
    meshworld_texture: StringProperty(
        name="Texture Name",
        default="",
    )


class MeshWorldObjectProps(bpy.types.PropertyGroup):
    is_ref_point: BoolProperty(default=False)
    is_spline: BoolProperty(default=False)
    is_light: BoolProperty(default=False)
    is_scene_metadata: BoolProperty(default=False)
    light_type: IntProperty(default=0)
    ref_rotation_z: FloatProperty(default=0.0)
    ref_rotation_y: FloatProperty(default=0.0)
    ref_rotation_x: FloatProperty(default=0.0)


class MeshWorldSceneProps(bpy.types.PropertyGroup):
    background_color: FloatVectorProperty(
        name="Background Color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0),
    )
    ambient_color: FloatVectorProperty(
        name="Ambient Color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0),
    )
    root_bound_min: FloatVectorProperty(
        name="Root Bound Min",
        size=3,
        default=(-1000000.0, -1000000.0, -1000000.0),
    )
    root_bound_max: FloatVectorProperty(
        name="Root Bound Max",
        size=3,
        default=(1000000.0, 1000000.0, 1000000.0),
    )


classes = [
    MeshWorldMaterialProps,
    MeshWorldObjectProps,
    MeshWorldSceneProps,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    Material.meshworld = PointerProperty(type=MeshWorldMaterialProps)
    Object.meshworld = PointerProperty(type=MeshWorldObjectProps)
    Scene.meshworld = PointerProperty(type=MeshWorldSceneProps)


def unregister():
    del Scene.meshworld
    del Object.meshworld
    del Material.meshworld
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
