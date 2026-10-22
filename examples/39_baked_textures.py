# Textures baked from fields: the pictures a model is painted with, made from the model itself.
#
#   export_mesh(rock, "rock.glb", max_triangles=3000, uvs="unwrap", materials=[stone, moss, gold], textures=bake(size=512))
#
# Every texel of a picture is a place on the surface (the UV map says which); what the place is made of is read from the fields there:
#   rock_color.png    the colour: the material of the place -- `where` is read at the texel, so the edge between two materials is as sharp as the picture -- times the vertex colours;
#                     a material's colour, roughness ... can be a FIELD (here: noise), and then the picture is the pattern
#   rock_normal.png   the normal map: the exact normal of the field, in the tangent space of the mesh.  A coarse mesh shaded with it looks like the fine surface
#   rock_orm.png      occlusion (red: how much of the sky the place sees), roughness (green), metalness (blue)
#   rock_layout.png   the UV map: the islands and the edges of the triangles
# A .glb has the pictures inside it as well; the materials refer to them.
#
# The rock is drawn.  The script writes the files, reads the pictures back, and prints a line that starts with ok or FAIL for each check (in the output pane).
import json
import struct
from fieldev import *
from fieldev.stdlib.pngfile import read_png

view.set_bounds((-60, -60, -5), (60, 60, 100))
view.set_resolution(1.5)
view.set_quality(8)

rock = sphere(40, (0, 0, 45)) - 2.5 * noise_field(14, 3, seed=4, kind='ridged')
rock

# the stone is grey with a pattern of its own; the moss is on the lower part; gold fills the cracks
grain = noise_field(5, 2, seed=2)
stone = material("stone", color=(0.45 + 0.25 * grain, 0.43 + 0.25 * grain, 0.40 + 0.25 * grain), roughness=0.85)
moss = material("moss", color=(0.20, 0.38, 0.12), roughness=0.95, where=z_field() - 28)
gold = material_preset("gold", where=noise_field(16, 2, seed=7, kind='cracks') + 0.8)

failed = []


def check(label, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + label + (("    " + detail) if detail else ""))
    if not ok:
        failed.append(label)


def texels(path):
    w, h, ch, px = read_png(path)
    return w, h, ch, px


def channel(px, ch, k):
    return px[k::ch]


# 1. the bake
spec = bake(size=256, occlusion_samples=8)
export_mesh(rock, "meshes/rock.glb", max_triangles=3000, uvs=uv_unwrap(angle=45, margin=4, size=256), materials=[stone, moss, gold], textures=spec,
            uv_layout="meshes/rock_layout.png")
report = spec.report
check("bake: the pictures were made", report is not None and set(report["maps"]) == {"color", "normal", "orm"},
      "%d texels (%.0f %% of the picture) in %.1f s" % (report["texels"], 100 * report["coverage"], report["seconds"]))

w, h, ch, color = texels("meshes/rock_color.png")
check("color: a 256 x 256 RGB picture", (w, h, ch) == (256, 256, 3))
rgb = [tuple(color[i:i + 3]) for i in range(0, len(color), 3)]
painted = [c for c in rgb if c != (128, 128, 128)]
check("color: most of the picture is painted (the islands and their padding)", len(painted) > 0.3 * len(rgb), "%.0f %%" % (100 * len(painted) / len(rgb)))
greens = sum(1 for r, g, b in painted if g > r + 25 and g > b + 25)
golds = sum(1 for r, g, b in painted if r > 150 and r > b + 60 and g > b + 20)
greys = sum(1 for r, g, b in painted if abs(r - g) < 20 and abs(g - b) < 25 and 70 < r < 200)
check("color: moss on the lower part, gold in the cracks, grey stone elsewhere", greens > 50 and golds > 20 and greys > 500, "%d green, %d gold, %d grey texels" % (greens, golds, greys))
tones = [r for r, g, b in painted if abs(r - g) < 20 and abs(g - b) < 25]
mean = sum(tones) / len(tones)
spread = (sum((t - mean) ** 2 for t in tones) / len(tones)) ** 0.5
check("color: the stone's colour is a field, so it varies over the surface", spread > 6, "grey from %d to %d, spread %.1f" % (min(tones), max(tones), spread))

w, h, ch, orm = texels("meshes/rock_orm.png")
occlusion, rough, metal = channel(orm, 3, 0), channel(orm, 3, 1), channel(orm, 3, 2)
covered = [i for i, c in enumerate(rgb) if c != (128, 128, 128)]
check("orm: the metalness is high in the gold only", 0.003 < sum(1 for i in covered if metal[i] > 200) / len(covered) < 0.4 and sum(1 for i in covered if 20 < metal[i] < 235) < 0.02 * len(covered),
      "%.1f %% metal" % (100 * sum(1 for i in covered if metal[i] > 200) / len(covered)))
stone_rough = sum(1 for i in covered if 205 < rough[i] < 230)
gold_rough = sum(1 for i in covered if 55 < rough[i] < 75)
check("orm: the roughness is the stone's (0.85), the moss's (0.95) and the gold's (0.25)", stone_rough > 500 and gold_rough > 20, "%d stone, %d gold texels" % (stone_rough, gold_rough))
dark = sum(1 for i in covered if occlusion[i] < 200)
mean_occ = sum(occlusion[i] for i in covered) / len(covered)
check("orm: the occlusion is dark in the hollows and bright on the heights", dark > 0.02 * len(covered) and mean_occ > 140 and max(occlusion[i] for i in covered) > 245,
      "%.0f %% darker than 200, mean %.0f" % (100 * dark / len(covered), mean_occ))

w, h, ch, normal = texels("meshes/rock_normal.png")
nx, ny, nz = channel(normal, 3, 0), channel(normal, 3, 1), channel(normal, 3, 2)
lengths = [((nx[i] / 127.5 - 1) ** 2 + (ny[i] / 127.5 - 1) ** 2 + (nz[i] / 127.5 - 1) ** 2) ** 0.5 for i in covered]
check("normal: every normal is a unit vector (within the rounding of 8 bits)", all(0.93 < l < 1.07 for l in lengths), "%.3f to %.3f" % (min(lengths), max(lengths)))
check("normal: it points out of the surface (blue is high) and carries detail (not all flat)", sum(nz[i] for i in covered) / len(covered) > 190 and sum(1 for i in covered if abs(nx[i] - 128) > 10 or abs(ny[i] - 128) > 10) > 0.05 * len(covered),
      "mean blue %.0f, %.0f %% leans" % (sum(nz[i] for i in covered) / len(covered), 100 * sum(1 for i in covered if abs(nx[i] - 128) > 10 or abs(ny[i] - 128) > 10) / len(covered)))

w, h, ch, layout = texels("meshes/rock_layout.png")
check("uv_layout: the picture of the map", (w, h, ch) == (256, 256, 3))

# 2. a coarse mesh needs more of the normal map than a fine one: a ball with bumps that the coarse mesh cannot hold (a plain sphere would not show it: the mesh's own
#    normals are exact at its corners, and between them a sphere is nearly what they say)
ball = sphere(20, (0, 0, 45)) - 1.5 * noise_field(9, 1, seed=3)
for label, triangles in (("coarse", 300), ("fine", 6000)):
    export_mesh(ball, "meshes/ball_%s.glb" % label, max_triangles=triangles, uvs=uv_unwrap(angle=45, margin=4, size=128), textures=bake(size=128, maps=["normal"]))
leans = {}
for label in ("coarse", "fine"):
    w, h, ch, px = texels("meshes/ball_%s_normal.png" % label)
    drawn = [i for i in range(0, len(px), 3) if (px[i], px[i + 1], px[i + 2]) != (128, 128, 255)]
    leans[label] = sum(abs(px[i] - 128) + abs(px[i + 1] - 128) for i in drawn) / max(1, len(drawn))
check("normal: a coarse mesh has more in its normal map than a fine one", leans["coarse"] > 1.5 * leans["fine"], "the texels lean %.1f on the coarse one, %.1f on the fine (of 255)" % (leans["coarse"], leans["fine"]))

# 3. the glTF
data = open("meshes/rock.glb", "rb").read()
jsize = struct.unpack_from("<I", data, 12)[0]
doc = json.loads(data[20:20 + jsize].decode("utf-8"))
prim = doc["meshes"][0]["primitives"][0]
check("glTF: normals, tangents and texture coordinates are in it", all(k in prim["attributes"] for k in ("POSITION", "NORMAL", "TANGENT", "TEXCOORD_0")))
mat = doc["materials"][0]
pbr = mat["pbrMetallicRoughness"]
check("glTF: the material refers to the pictures", all(k in pbr for k in ("baseColorTexture", "metallicRoughnessTexture")) and "normalTexture" in mat and "occlusionTexture" in mat
      and pbr["metallicFactor"] == 1.0 and pbr["roughnessFactor"] == 1.0)
check("glTF: the pictures are inside the file, as PNG", len(doc["images"]) == 3 and all(i.get("mimeType") == "image/png" and "bufferView" in i for i in doc["images"]))
check("glTF: three materials, a primitive of the mesh for each", [m["name"] for m in doc["materials"]] == ["stone", "moss", "gold"] and len(doc["meshes"][0]["primitives"]) == 3)

# 4. an OBJ: the materials name the pictures
export_mesh(ball, "meshes/ball.obj", max_triangles=1500, uvs="unwrap", materials=[stone, gold], textures=bake(size=64, maps=["color", "normal"]))
mtl = open("meshes/ball.mtl").read()
check("obj: the .mtl names the colour map and the normal map", "map_Kd ball_color.png" in mtl and "map_Bump ball_normal.png" in mtl)
check("obj: the file has normals and texture coordinates", sum(1 for ln in open("meshes/ball.obj") if ln.startswith("vn ")) > 0 and sum(1 for ln in open("meshes/ball.obj") if ln.startswith("vt ")) > 0)

# 5. what is refused
for label, call in (("a material with a field for its colour, written without textures", lambda: export_mesh(rock, "meshes/x.glb", materials=[stone])),
                    ("textures without texture coordinates", lambda: export_mesh(rock, "meshes/x.glb", materials=[gold], textures=bake(size=64))),
                    ("a picture of 8 texels", lambda: bake(size=8)),
                    ("a map that is not one", lambda: bake(maps=["glitter"])),
                    ("orm with roughness beside it", lambda: bake(maps=["orm", "roughness"])),
                    ("textures in an STL", lambda: export_mesh(rock, "meshes/x.stl", uvs="unwrap", textures=bake(size=64)))):
    try:
        call()
        check(label + " is refused", False)
    except (ValueError, TypeError) as e:
        check(label + " is refused", True, str(e)[:70])

print("")
print("%d checks failed: %s" % (len(failed), ", ".join(failed)) if failed else "all checks passed")
