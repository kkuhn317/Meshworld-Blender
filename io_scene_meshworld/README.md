# Hamsterball MESHWORLD Blender Add-on

Blender add-on for importing and exporting Hamsterball `.MESHWORLD` level files.

Full documentation: [HamsterMall Wiki — Blender Add-on](https://github.com/kkuhn317/HamsterMall/wiki/Blender-Addon)

## Features

- Import full MESHWORLD levels into Blender
- Export Blender scenes back to MESHWORLD format
- Native material panel for Hamsterball-specific values:
  - Specular color (full range, no glTF clamp)
  - Ambient color
  - Emissive color
  - Specular power
  - Reflection flag
  - Texture name
- Imports ref points, splines, and directional lights
- Exports geometry as triangle strips
- Writes textures to a `textures/` folder next to the MESHWORLD file
- Import/export Hamsterball `.MESH` prop models (ball, hamster, chomper...)

## Installation

1. Download `io_scene_meshworld.zip`
2. In Blender, go to **Edit → Preferences → Add-ons → Install...**
3. Select the ZIP file and click **Install Add-on**
4. Enable the add-on: **Import-Export: Hamsterball MESHWORLD**

## Usage

### Import

1. **File → Import → Hamsterball MESHWORLD (.meshworld)**
   (Optional: tick `Octree Hierarchy` to put each mesh node in its own collection)
2. Select a `.MESHWORLD` file
3. Optional: choose a custom texture directory
4. Click **Import MESHWORLD**

### Export

1. **File → Export → Hamsterball MESHWORLD (.meshworld)**
2. Choose the output location
3. Click **Export MESHWORLD**

### MESH models

1. **File → Import → Hamsterball MESH (.mesh)**, pick a `.MESH` file.
   Each model part becomes one object in a collection named after the file.
2. Edit, then select the objects and **File → Export → Hamsterball MESH (.mesh)**.
   Each selected mesh object becomes one model part.
3. Animation is file-per-frame: export one `.MESH` per pose
   (like the stock `Hamster-Trot1/2/3` files).

## Material editing

Select any imported mesh and open the **Material Properties** tab. Scroll to the **Hamsterball Material** panel. The values in this panel are written verbatim to the MESHWORLD file on export.

## Scene settings

Open the **Scene Properties** tab and scroll to **Hamsterball Scene** to edit background color, ambient color, and root bounding box.

## Notes

- Tick `Octree Hierarchy` on import to keep each mesh node in its own collection.
- Ref points are imported as empties with custom object properties.
- Splines are imported as curve objects.
- Lights are imported as Sun lights.

## New level checklist

1. Model your geometry (any meshes; triangulated automatically on export).
2. `N` panel → Hamsterball tab: add a ref point named `START...`
   (the game spawns the ball here), plus any splines and lights.
3. Scene Properties → Hamsterball Scene: background and ambient colors.
4. **File → Export → Hamsterball MESHWORLD**. Root bounds are computed
   from your geometry automatically.
5. The exporter warns you if there is no geometry or no `REF:START` point.
