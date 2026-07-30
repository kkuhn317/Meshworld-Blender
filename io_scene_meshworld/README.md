# Hamsterball MESHWORLD Blender Add-on

Blender add-on for importing and exporting Hamsterball `.MESHWORLD` level files.

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

## Installation

1. Download `io_scene_meshworld.zip`
2. In Blender, go to **Edit → Preferences → Add-ons → Install...**
3. Select the ZIP file and click **Install Add-on**
4. Enable the add-on: **Import-Export: Hamsterball MESHWORLD**

## Usage

### Import

1. **File → Import → Hamsterball MESHWORLD (.meshworld)**
2. Select a `.MESHWORLD` file
3. Optional: choose a custom texture directory
4. Click **Import MESHWORLD**

### Export

1. **File → Export → Hamsterball MESHWORLD (.meshworld)**
2. Choose the output location
3. Click **Export MESHWORLD**

## Material editing

Select any imported mesh and open the **Material Properties** tab. Scroll to the **Hamsterball Material** panel. The values in this panel are written verbatim to the MESHWORLD file on export.

## Scene settings

Open the **Scene Properties** tab and scroll to **Hamsterball Scene** to edit background color, ambient color, and root bounding box.

## Notes

- This add-on is flat import/export only; hierarchy is flattened.
- Ref points are imported as empties with custom object properties.
- Splines are imported as curve objects.
- Lights are imported as Sun lights.
