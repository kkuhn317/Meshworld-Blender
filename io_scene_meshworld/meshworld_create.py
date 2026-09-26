"""Viewport creation helpers for new ref points, splines, and lights."""
import bpy
from bpy.types import Operator, Panel


def clean_base_name(raw, prefix):
    base = (raw or "").strip()
    if prefix and base.startswith(prefix):
        base = base[len(prefix):]
    return base or "NEWPOINT"


class MESHWORLD_OT_add_ref_point(Operator):
    """Add a Hamsterball ref point empty (REF: prefix, ZXY order)"""
    bl_idname = "meshworld.add_ref_point"
    bl_label = "Add Ref Point"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        mw = context.scene.meshworld
        name = "REF:" + clean_base_name(mw.helper_name, "REF:")
        bpy.ops.object.empty_add(type="ARROWS",
                                 location=context.scene.cursor.location)
        obj = context.active_object
        obj.name = name
        obj.empty_display_size = 0.4
        obj.rotation_mode = "ZXY"
        obj.meshworld.is_ref_point = True
        return {"FINISHED"}


class MESHWORLD_OT_add_spline(Operator):
    """Add a Hamsterball spline curve (C: prefix)"""
    bl_idname = "meshworld.add_spline"
    bl_label = "Add Spline"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        mw = context.scene.meshworld
        name = "C:" + clean_base_name(mw.helper_name, "C:")
        curve = bpy.data.curves.new(name, type="CURVE")
        curve.dimensions = "3D"
        spline = curve.splines.new("NURBS")
        spline.points.add(1)
        cursor = context.scene.cursor.location
        spline.points[0].co = (cursor.x - 1.0, cursor.y, cursor.z, 1.0)
        spline.points[1].co = (cursor.x + 1.0, cursor.y, cursor.z, 1.0)
        obj = bpy.data.objects.new(name, curve)
        context.collection.objects.link(obj)
        obj.meshworld.is_spline = True
        return {"FINISHED"}


class MESHWORLD_OT_add_light(Operator):
    """Add a Hamsterball sun light"""
    bl_idname = "meshworld.add_light"
    bl_label = "Add Light"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        mw = context.scene.meshworld
        name = clean_base_name(mw.helper_name, "")
        light_data = bpy.data.lights.new(name=name, type="SUN")
        light_data.energy = 1.0
        obj = bpy.data.objects.new(name, light_data)
        obj.location = context.scene.cursor.location
        context.collection.objects.link(obj)
        obj.meshworld.is_light = True
        obj.meshworld.light_type = mw.helper_light_type
        return {"FINISHED"}


class MESHWORLD_PT_create(Panel):
    bl_label = "Hamsterball"
    bl_idname = "MESHWORLD_PT_create"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Hamsterball"

    def draw(self, context):
        layout = self.layout
        mw = context.scene.meshworld
        layout.prop(mw, "helper_name")
        layout.operator(MESHWORLD_OT_add_ref_point.bl_idname)
        layout.operator(MESHWORLD_OT_add_spline.bl_idname)
        layout.operator(MESHWORLD_OT_add_light.bl_idname)
        layout.prop(mw, "helper_light_type")


classes = [
    MESHWORLD_OT_add_ref_point,
    MESHWORLD_OT_add_spline,
    MESHWORLD_OT_add_light,
    MESHWORLD_PT_create,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
