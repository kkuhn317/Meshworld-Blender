bl_info = {
    "name": "Hamsterball MESHWORLD",
    "author": "BookwormKevin",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "File > Import-Export",
    "description": "Import and export Hamsterball .MESHWORLD level files",
    "category": "Import-Export",
    "support": "COMMUNITY",
}

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import (
    Operator,
    OperatorFileListElement,
    Panel,
    PropertyGroup,
    TOPBAR_MT_file_import,
    TOPBAR_MT_file_export,
)

if "bpy" in locals():
    import importlib
    if "meshworld_format" in locals():
        importlib.reload(meshworld_format)
    if "meshworld_import" in locals():
        importlib.reload(meshworld_import)
    if "meshworld_export" in locals():
        importlib.reload(meshworld_export)
    if "meshworld_material" in locals():
        importlib.reload(meshworld_material)
    if "meshworld_props" in locals():
        importlib.reload(meshworld_props)
    if "meshworld_ui" in locals():
        importlib.reload(meshworld_ui)

from . import (
    meshworld_format,
    meshworld_import,
    meshworld_export,
    meshworld_material,
    meshworld_props,
    meshworld_ui,
)


class MESHWORLD_OT_import(Operator):
    """Import Hamsterball MESHWORLD"""
    bl_idname = "import_scene.meshworld"
    bl_label = "Import MESHWORLD"
    bl_options = {"PRESET", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.MESHWORLD;*.meshworld", options={"HIDDEN"})

    use_custom_texture_dir: BoolProperty(
        name="Use Custom Texture Directory",
        description="Pick a directory to search for textures instead of ../Textures",
        default=False,
    )
    custom_texture_dir: StringProperty(
        name="Texture Directory",
        subtype="DIR_PATH",
        default="",
    )

    def execute(self, context):
        meshworld_import.import_meshworld(
            self.filepath,
            custom_texture_dir=self.custom_texture_dir if self.use_custom_texture_dir else "",
        )
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class MESHWORLD_OT_export(Operator):
    """Export Hamsterball MESHWORLD"""
    bl_idname = "export_scene.meshworld"
    bl_label = "Export MESHWORLD"
    bl_options = {"PRESET"}

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.MESHWORLD;*.meshworld", options={"HIDDEN"})

    def execute(self, context):
        meshworld_export.export_meshworld(self.filepath)
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


def menu_func_import(self, context):
    self.layout.operator(MESHWORLD_OT_import.bl_idname, text="Hamsterball MESHWORLD (.meshworld)")


def menu_func_export(self, context):
    self.layout.operator(MESHWORLD_OT_export.bl_idname, text="Hamsterball MESHWORLD (.meshworld)")


classes = [
    MESHWORLD_OT_import,
    MESHWORLD_OT_export,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    meshworld_props.register()
    meshworld_ui.register()
    TOPBAR_MT_file_import.append(menu_func_import)
    TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    TOPBAR_MT_file_import.remove(menu_func_import)
    TOPBAR_MT_file_export.remove(menu_func_export)
    meshworld_ui.unregister()
    meshworld_props.unregister()
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
