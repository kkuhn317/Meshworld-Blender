"""Binary read/write helpers for the MESHWORLD format."""
import struct
import os


class MeshWorldReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def _read(self, fmt):
        size = struct.calcsize(fmt)
        val = struct.unpack_from(fmt, self.data, self.pos)[0]
        self.pos += size
        return val

    def read_u32(self):
        return self._read("<I")

    def read_s32(self):
        return self._read("<i")

    def read_float(self):
        return self._read("<f")

    def read_string(self):
        length = self.read_s32()
        if length <= 0:
            return ""
        raw = self.data[self.pos : self.pos + length]
        self.pos += length
        return raw.split(b"\x00")[0].decode("latin-1", errors="replace")

    def read_vec3(self):
        return (self.read_float(), self.read_float(), self.read_float())

    def read_vec4(self):
        return (self.read_float(), self.read_float(), self.read_float(), self.read_float())

    def read_bytes(self, n):
        out = self.data[self.pos : self.pos + n]
        self.pos += n
        return out


class MeshWorldWriter:
    def __init__(self, stream):
        self.stream = stream

    def write_u32(self, val):
        self.stream.write(struct.pack("<I", val))

    def write_s32(self, val):
        self.stream.write(struct.pack("<i", val))

    def write_float(self, val):
        self.stream.write(struct.pack("<f", val))

    def write_string(self, s):
        b = s.encode("latin-1") + b"\x00"
        self.write_s32(len(b))
        self.stream.write(b)

    def write_vec3(self, v):
        self.write_float(v[0])
        self.write_float(v[1])
        self.write_float(v[2])

    def write_vec4(self, v):
        self.write_float(v[0])
        self.write_float(v[1])
        self.write_float(v[2])
        self.write_float(v[3])

    def write_vertex(self, v):
        # v is a dict or tuple (X, Y, Z, NX, NY, NZ, U, V)
        if isinstance(v, dict):
            self.write_float(v["X"])
            self.write_float(v["Y"])
            self.write_float(v["Z"])
            self.write_float(v["NX"])
            self.write_float(v["NY"])
            self.write_float(v["NZ"])
            self.write_float(v["U"])
            self.write_float(v["V"])
        else:
            for f in v:
                self.write_float(f)


def find_texture_path(texture_name, meshworld_path, custom_texture_dir=""):
    """Search for a texture file matching texture_name. Returns absolute path or None."""
    if not texture_name:
        return None

    candidates = []
    base = texture_name
    # Strip extension if present; the game tries .bmp/.png/.tga
    for ext in (".bmp", ".png", ".tga", ".jpg", ".jpeg"):
        if base.lower().endswith(ext):
            base = base[: -len(ext)]
            break

    def add_search_dir(d):
        for ext in (".png", ".bmp", ".tga", ".jpg"):
            candidates.append(os.path.join(d, base + ext))
        candidates.append(os.path.join(d, texture_name))

    if custom_texture_dir and os.path.isdir(custom_texture_dir):
        add_search_dir(custom_texture_dir)
    else:
        meshworld_dir = os.path.dirname(meshworld_path)
        parent_dir = os.path.dirname(meshworld_dir) or meshworld_dir
        add_search_dir(os.path.join(parent_dir, "Textures"))
        add_search_dir(os.path.join(parent_dir, "textures"))
        add_search_dir(os.path.join(meshworld_dir, "textures"))

    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def convert_in_vertex(pos):
    """Convert MESHWORLD vertex coordinates to Blender coordinates."""
    x, y, z = pos
    return (x / 50.0, z / 50.0, y / 50.0)


def convert_out_vertex(pos):
    """Convert Blender vertex coordinates to MESHWORLD coordinates."""
    x, y, z = pos
    return (x * 50.0, z * 50.0, y * 50.0)


def normal_convert_in_vertex(n):
    x, y, z = n
    return (x, z, y)


def normal_convert_out_vertex(n):
    x, y, z = n
    return (x, z, y)


def convert_in(pos):
    """Convert MESHWORLD coordinates (x,y,z) to Blender (x,y,z)."""
    x, y, z = pos
    return (x / 50.0, z / 50.0, y / 50.0)


def convert_out(pos):
    """Convert Blender coordinates (x,y,z) to MESHWORLD (x,y,z)."""
    x, y, z = pos
    return (x * 50.0, z * 50.0, y * 50.0)


def normal_convert_in(n):
    x, y, z = n
    return (x, z, y)


def normal_convert_out(n):
    x, y, z = n
    return (x, z, y)


def uv_convert_in(u, v):
    # The C# code did not flip V; leave as-is
    return (u, v)


def quaternion_to_euler_zxy(q):
    """Return (RotZ, RotY, RotX) in degrees from a (w, x, y, z) quaternion."""
    w, x, y, z = q
    # C# CreateFromYawPitchRoll order: yaw=Y, pitch=X, roll=Z
    # The C# code wrote RotZ = ...YawPitchRoll(...).Z (roll)
    # So we replicate the same extraction used in exporter.
    # For simplicity, match the exporter math used by the C# code.
    rY, rX, rZ, rW = x, y, -z, w

    denom_y = 1 - 2 * (rX * rX + rY * rY)
    if denom_y != 0:
        RotY = 180.0 * (2 * (rW * rX + rY * rZ)) / (denom_y * 3.14159265358979323846)
        RotY = (180.0 / 3.14159265358979323846) * ((2 * (rW * rX + rY * rZ)) / denom_y)
    else:
        RotY = 0.0

    denom_z = 1 - 2 * (rY * rY + rZ * rZ)
    if denom_z != 0:
        RotZ = (180.0 / 3.14159265358979323846) * ((2 * (rW * rZ + rX * rY)) / denom_z)
    else:
        RotZ = 0.0

    sin_x = 2 * (rW * rY - rZ * rX)
    sin_x = max(-1.0, min(1.0, sin_x))
    RotX = (180.0 / 3.14159265358979323846) * (asin(sin_x))

    if abs(sin_x) > 0.99999:
        if sin_x > 0:
            RotY = 90.0
        else:
            RotY = -90.0

    return (RotZ, RotY, RotX)
