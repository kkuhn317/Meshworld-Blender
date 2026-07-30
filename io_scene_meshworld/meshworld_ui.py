"""UI panels for custom Hamsterball material/scene properties."""
import bpy
from bpy.types import Panel


class MESHWORLD_PT_material(Panel):
    bl_label = "Hamsterball Material"
    bl_idname = "MESHWORLD_PT_material"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.material is not None

    def draw(self, context):
        layout = self.layout
        mat = context.material
        if not hasattr(mat, "meshworld"):
            return
        mw = mat.meshworld

        layout.prop(mw, "ambient")
        layout.prop(mw, "specular")
        layout.prop(mw, "emissive")
        layout.prop(mw, "power")
        layout.prop(mw, "has_reflection")
        layout.prop(mw, "meshworld_texture")

        layout.separator()
        layout.label(text="Export uses these values (not PBR sliders).")


class MESHWORLD_PT_scene(Panel):
    bl_label = "Hamsterball Scene"
    bl_idname = "MESHWORLD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if not hasattr(scene, "meshworld"):
            return
        mw = scene.meshworld

        layout.prop(mw, "background_color")
        layout.prop(mw, "ambient_color")
        layout.prop(mw, "root_bound_min")
        layout.prop(mw, "root_bound_max")


classes = [
    MESHWORLD_PT_material,
    MESHWORLD_PT_scene,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
