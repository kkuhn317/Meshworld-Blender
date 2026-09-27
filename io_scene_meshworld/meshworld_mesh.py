"""Read/write Hamsterball .MESH model files.

Binary layout (verified against all 32 stock files, byte-exact):
  u32 group_count (1-5), then groups back to back, then one bbox (6 floats).
  Per group:
    string name (s32 length incl NUL, unpadded)
    float[3] center in (x, z, y) file order
    float[16] material: ambient RGBA, diffuse RGBA, specular RGBA, emissive RGBA
    float power; u32 has_reflection; u32 has_texture; [string texture]
    u32 strip_count
    per strip: u32 tri_count, then (tri_count + 2) verts of 32 bytes
      (pos xyz, normal xyz, uv) all in file order/units
  Final: bbox min/max as (x, z, y) triples.

Animation is file-per-frame (Hamster-Trot1/2/3...), no bones.
"""
import struct

VERTEX_SIZE = 32


def _unpack(fmt, data, pos):
    val = struct.unpack_from(fmt, data, pos)[0]
    return val, pos + struct.calcsize(fmt)


def read_string(data, pos):
    length, pos = _unpack("<i", data, pos)
    if length <= 0:
        return "", pos
    raw = data[pos:pos + length]
    pos += length
    return raw.split(b"\x00")[0].decode("latin-1", errors="replace"), pos


def write_string(stream, s):
    b = s.encode("latin-1") + b"\x00"
    stream.write(struct.pack("<i", len(b)))
    stream.write(b)


def read_vertex(data, pos):
    v = struct.unpack_from("<8f", data, pos)
    return {
        "X": v[0], "Y": v[1], "Z": v[2],
        "NX": v[3], "NY": v[4], "NZ": v[5],
        "U": v[6], "V": v[7],
    }, pos + VERTEX_SIZE


def write_vertex(stream, v):
    if isinstance(v, dict):
        vals = (v["X"], v["Y"], v["Z"], v["NX"], v["NY"], v["NZ"], v["U"], v["V"])
    else:
        vals = tuple(v)
    stream.write(struct.pack("<8f", *vals))


def read_mesh(data):
    """Parse .MESH bytes. Returns (groups, bbox_min, bbox_max)."""
    pos = 0
    group_count, pos = _unpack("<I", data, pos)
    groups = []
    for _ in range(group_count):
        name, pos = read_string(data, pos)
        # File stores (x, z, y); API uses Blender (x, y, z).
        fx, pos = _unpack("<f", data, pos)
        fz, pos = _unpack("<f", data, pos)
        fy, pos = _unpack("<f", data, pos)
        mat = struct.unpack_from("<16f", data, pos)
        pos += 64
        power, pos = _unpack("<f", data, pos)
        has_reflection, pos = _unpack("<I", data, pos)
        has_texture, pos = _unpack("<I", data, pos)
        texture = ""
        if has_texture:
            texture, pos = read_string(data, pos)
        strip_count, pos = _unpack("<I", data, pos)
        strips = []
        for _ in range(strip_count):
            tri_count, pos = _unpack("<I", data, pos)
            verts = []
            for _ in range(tri_count + 2):
                v, pos = read_vertex(data, pos)
                verts.append(v)
            strips.append({"triangle_count": tri_count, "verts": verts})
        groups.append({
            "name": name,
            "center": (fx, fy, fz),
            "ambient": tuple(mat[0:4]),
            "diffuse": tuple(mat[4:8]),
            "specular": tuple(mat[8:12]),
            "emissive": tuple(mat[12:16]),
            "power": power,
            "has_reflection": has_reflection,
            "texture": texture,
            "strips": strips,
        })
    raw_min = struct.unpack_from("<3f", data, pos)
    pos += 12
    raw_max = struct.unpack_from("<3f", data, pos)
    pos += 12
    # File stores (x, z, y); API uses Blender (x, y, z).
    bbox_min = (raw_min[0], raw_min[2], raw_min[1])
    bbox_max = (raw_max[0], raw_max[2], raw_max[1])
    return groups, bbox_min, bbox_max


def write_mesh(stream, groups, bbox_min, bbox_max):
    """Write groups + trailing bbox. center/bbox are Blender (x, y, z)."""
    stream.write(struct.pack("<I", len(groups)))
    for g in groups:
        write_string(stream, g["name"])
        cx, cy, cz = g["center"]
        stream.write(struct.pack("<3f", cx, cz, cy))
        stream.write(struct.pack("<16f",
                                 *g["ambient"], *g["diffuse"],
                                 *g["specular"], *g["emissive"]))
        stream.write(struct.pack("<f", g["power"]))
        stream.write(struct.pack("<I", g["has_reflection"]))
        if g["texture"]:
            stream.write(struct.pack("<I", 1))
            write_string(stream, g["texture"])
        else:
            stream.write(struct.pack("<I", 0))
        stream.write(struct.pack("<I", len(g["strips"])))
        for s in g["strips"]:
            stream.write(struct.pack("<I", s["triangle_count"]))
            for v in s["verts"]:
                write_vertex(stream, v)
    stream.write(struct.pack("<3f", bbox_min[0], bbox_min[2], bbox_min[1]))
    stream.write(struct.pack("<3f", bbox_max[0], bbox_max[2], bbox_max[1]))
