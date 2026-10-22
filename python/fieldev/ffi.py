'''
Python bindings to the libfive CAD kernel
Copyright (C) 2021  Matt Keeter

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import ctypes
import os
import sys

def try_link(folder, name):
    if sys.platform == "linux" or sys.platform == "linux2":
        suffix = '.so'
    elif sys.platform == "win32":
        suffix = '.dll'
    path = os.path.join(folder, name + suffix)
    try:
        return ctypes.cdll.LoadLibrary(path)
    except OSError:
        return None

def paths_for(folder):
    # Where the libraries are: the folder the application names (FIELDEV_DIR), the
    # folders from the package up (a packaged application keeps the package next to
    # the libraries), then wherever the system looks.
    paths = []
    env = os.environ.get('FIELDEV_DIR')
    if env:
        paths.append(env)
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        paths.append(here)
        here = os.path.dirname(here)
    paths.append("")
    return paths

def link_lib(folder, name):
    for p in paths_for(folder):
        lib = try_link(p, name)
        if lib is not None:
            return lib
    raise RuntimeError("Could not find {} library".format(name))

lib = link_lib('src', 'fieldev')
stdlib = link_lib('stdlib', 'fieldev-stdlib')

################################################################################

class libfive_interval_t(ctypes.Structure):
    _fields_ = [("lower", ctypes.c_float), ("upper", ctypes.c_float)]
class libfive_region_t(ctypes.Structure):
    _fields_ = [("X", libfive_interval_t),
                ("Y", libfive_interval_t),
                ("Z", libfive_interval_t)]
class libfive_vec3_t(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float),
                ("y", ctypes.c_float),
                ("z", ctypes.c_float)]

libfive_tree = ctypes.c_void_p

class libfive_tri_t(ctypes.Structure):
    _fields_ = [("a", ctypes.c_uint32),
                ("b", ctypes.c_uint32),
                ("c", ctypes.c_uint32)]

class libfive_mesh_t(ctypes.Structure):
    _fields_ = [("verts", ctypes.POINTER(libfive_vec3_t)),
                ("tris",  ctypes.POINTER(libfive_tri_t)),
                ("tri_count", ctypes.c_uint32),
                ("vert_count", ctypes.c_uint32)]

################################################################################

# Types used in the libfive stdlib
class tvec2(ctypes.Structure):
    _fields_ = [("x", libfive_tree), ("y", libfive_tree)]
    def __init__(self, x, y):
        super().__init__(x, y)

class tvec3(ctypes.Structure):
    _fields_ = [("x", libfive_tree), ("y", libfive_tree), ("z", libfive_tree)]
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
tfloat = libfive_tree

################################################################################
# Function signatures
lib.libfive_tree_delete.argtypes = [libfive_tree]

lib.libfive_tree_const.argtypes = [ctypes.c_float]
lib.libfive_tree_const.restype = libfive_tree

lib.libfive_opcode_enum.argtypes = [ctypes.c_char_p]
lib.libfive_opcode_enum.restype = ctypes.c_int

lib.libfive_tree_is_var.argtypes = [libfive_tree]
lib.libfive_tree_is_var.restype = ctypes.c_uint8

if hasattr(lib, 'libfive_tree_set_var_value'):
    lib.libfive_tree_set_var_value.argtypes = [libfive_tree, ctypes.c_float]
    lib.libfive_tree_set_var_value.restype = None

lib.libfive_opcode_args.argtypes = [ctypes.c_int]
lib.libfive_opcode_args.restype = ctypes.c_int

lib.libfive_tree_nullary.argtypes = [ctypes.c_int]
lib.libfive_tree_nullary.restype = libfive_tree

lib.libfive_tree_unary.argtypes = [ctypes.c_int, libfive_tree]
lib.libfive_tree_unary.restype = libfive_tree

lib.libfive_tree_binary.argtypes = [ctypes.c_int, libfive_tree, libfive_tree]
lib.libfive_tree_binary.restype = libfive_tree

lib.libfive_tree_id.argtypes = [libfive_tree]
lib.libfive_tree_id.restype = ctypes.c_void_p

lib.libfive_tree_remap.argtypes = [libfive_tree, libfive_tree, libfive_tree, libfive_tree]
lib.libfive_tree_remap.restype = libfive_tree

lib.libfive_tree_call.argtypes = [libfive_tree, libfive_tree, libfive_tree, libfive_tree]
lib.libfive_tree_call.restype = libfive_tree

lib.libfive_tree_partial.argtypes = [libfive_tree, ctypes.c_int, ctypes.c_float, ctypes.c_int]
lib.libfive_tree_partial.restype = libfive_tree

lib.libfive_tree_print.argtypes = [libfive_tree]
lib.libfive_tree_print.restype = ctypes.c_void_p # actually a c_char_p,
# but we don't want Python to auto-convert into a bytestring

lib.libfive_free_str.argtypes = [ctypes.c_char_p]

try:
    # The numbers of a tree that place its surfaces, as variables (fieldev.stdlib.handles.handles)
    lib.libfive_tree_expose_count.argtypes = [libfive_tree]
    lib.libfive_tree_expose_count.restype = ctypes.c_int
    lib.libfive_tree_expose_values.argtypes = [libfive_tree, ctypes.POINTER(ctypes.c_float)]
    lib.libfive_tree_expose_values.restype = None
    lib.libfive_tree_expose.argtypes = [libfive_tree, ctypes.POINTER(libfive_tree), ctypes.c_int]
    lib.libfive_tree_expose.restype = libfive_tree
except AttributeError:
    pass

try:
    # The key the render cache keeps a shape's mesh by
    lib.libfive_tree_persistent_key.argtypes = [libfive_tree, ctypes.POINTER(libfive_tree), ctypes.POINTER(ctypes.c_float),
                                                ctypes.c_int]
    lib.libfive_tree_persistent_key.restype = ctypes.c_void_p
except AttributeError:
    pass

try:
    # An exact key of a tree's structure (a library from before it has none: nothing is then cached by content)
    lib.libfive_tree_content_key.argtypes = [libfive_tree]
    lib.libfive_tree_content_key.restype = ctypes.c_void_p
except AttributeError:
    pass

lib.libfive_tree_save_mesh.argtypes = [libfive_tree, libfive_region_t, ctypes.c_float, ctypes.c_char_p]
lib.libfive_tree_save_mesh.restype = ctypes.c_uint8

lib.libfive_tree_save_meshes.argtypes = [libfive_tree, libfive_region_t, ctypes.c_float, ctypes.c_float, ctypes.c_char_p]
lib.libfive_tree_save_meshes.restype = ctypes.c_uint8

lib.libfive_tree_save.argtypes = [libfive_tree, ctypes.c_char_p]
lib.libfive_tree_save.restype = ctypes.c_bool

if hasattr(lib, 'libfive_tree_can_save'):
    lib.libfive_tree_can_save.argtypes = [libfive_tree]
    lib.libfive_tree_can_save.restype = ctypes.c_bool
if hasattr(lib, 'libfive_tree_axes'):
    lib.libfive_tree_axes.argtypes = [libfive_tree]
    lib.libfive_tree_axes.restype = ctypes.c_int

lib.libfive_tree_load.argtypes = [ctypes.c_char_p]
lib.libfive_tree_load.restype = libfive_tree


try:
    lib.libfive_tree_interval_lower.argtypes = [libfive_tree, libfive_region_t,
                                                ctypes.POINTER(libfive_tree), ctypes.POINTER(ctypes.c_float),
                                                ctypes.c_int]
    lib.libfive_tree_interval_lower.restype = ctypes.c_float
except AttributeError:
    pass    # an older library


class libfive_mesh_import_info_t(ctypes.Structure):
    _fields_ = [("triangles", ctypes.c_uint32),
                ("vertices", ctypes.c_uint32),
                ("components", ctypes.c_uint32),
                ("boundary_edges", ctypes.c_uint32),
                ("nonmanifold_edges", ctypes.c_uint32),
                ("reoriented", ctypes.c_uint32),
                ("dropped", ctypes.c_uint32),
                ("watertight", ctypes.c_uint8),
                ("winding_sign", ctypes.c_uint8),
                ("bounds", libfive_region_t)]

lib.libfive_import_mesh.argtypes = [ctypes.c_char_p, ctypes.c_float,
                                    ctypes.POINTER(libfive_mesh_import_info_t)]
lib.libfive_import_mesh.restype = libfive_tree

lib.libfive_mesh_from_arrays.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_uint32,
                                         ctypes.POINTER(ctypes.c_uint32), ctypes.c_uint32,
                                         ctypes.c_float,
                                         ctypes.POINTER(libfive_mesh_import_info_t)]
lib.libfive_mesh_from_arrays.restype = libfive_tree

try:
    lib.libfive_mesh_patch.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_uint32,
                                       ctypes.POINTER(ctypes.c_uint32), ctypes.c_uint32,
                                       ctypes.POINTER(ctypes.c_uint8),
                                       ctypes.POINTER(libfive_mesh_import_info_t)]
    lib.libfive_mesh_patch.restype = libfive_tree
except AttributeError:
    pass    # an older library: no surface selection

lib.libfive_import_mesh_last_message.argtypes = []
lib.libfive_import_mesh_last_message.restype = ctypes.c_char_p

lib.libfive_tree_eval_f.argtypes = [libfive_tree, libfive_vec3_t]
lib.libfive_tree_eval_f.restype = ctypes.c_float

lib.libfive_tree_eval_r.argtypes = [libfive_tree, libfive_region_t]
lib.libfive_tree_eval_r.restype = libfive_interval_t

lib.libfive_tree_bounds.argtypes = [libfive_tree, libfive_region_t, ctypes.c_int, ctypes.c_float,
                                   ctypes.POINTER(libfive_region_t), ctypes.POINTER(ctypes.c_int)]
lib.libfive_tree_bounds.restype = ctypes.c_bool
try:
    lib.libfive_tree_bounds_vars.argtypes = [libfive_tree, libfive_region_t, ctypes.c_int, ctypes.c_float,
                                             ctypes.POINTER(libfive_region_t), ctypes.POINTER(ctypes.c_int),
                                             ctypes.POINTER(libfive_tree), ctypes.POINTER(ctypes.c_float),
                                             ctypes.c_int]
    lib.libfive_tree_bounds_vars.restype = ctypes.c_bool
except AttributeError:
    pass    # an older library: the numbers of var()s are read as 0

lib.libfive_tree_eval_points.argtypes = [libfive_tree, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                                         ctypes.POINTER(ctypes.c_float)]
lib.libfive_tree_eval_points.restype = None
try:
    lib.libfive_tree_eval_points_vars.argtypes = [libfive_tree, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                                                  ctypes.POINTER(ctypes.c_float),
                                                  ctypes.POINTER(libfive_tree), ctypes.POINTER(ctypes.c_float),
                                                  ctypes.c_int]
    lib.libfive_tree_eval_points_vars.restype = None
except AttributeError:
    pass    # an older library: the numbers of var()s are read as 0

lib.libfive_tree_copy.argtypes = [libfive_tree]
lib.libfive_tree_copy.restype = libfive_tree

# A script run's progress (run_progress.py)
lib.libfive_run_begin.argtypes = [ctypes.c_int]
lib.libfive_run_begin.restype = None
lib.libfive_run_step.argtypes = [ctypes.c_int, ctypes.c_char_p]
lib.libfive_run_step.restype = None
lib.libfive_run_end.argtypes = []
lib.libfive_run_end.restype = None
lib.libfive_run_task_begin.argtypes = [ctypes.c_char_p]
lib.libfive_run_task_begin.restype = None
lib.libfive_run_task_set.argtypes = [ctypes.c_double, ctypes.c_char_p]
lib.libfive_run_task_set.restype = None
lib.libfive_run_task_span.argtypes = [ctypes.c_double, ctypes.c_double]
lib.libfive_run_task_span.restype = None
lib.libfive_run_task_end.argtypes = []
lib.libfive_run_task_end.restype = None

lib.libfive_tree_eval_d.argtypes = [libfive_tree, libfive_vec3_t]
lib.libfive_tree_eval_d.restype = libfive_vec3_t

lib.libfive_tree_optimized.argtypes = [libfive_tree]
lib.libfive_tree_optimized.restype = libfive_tree

lib.libfive_tree_render_mesh.argtypes = [libfive_tree, libfive_region_t, ctypes.c_float]
lib.libfive_tree_render_mesh.restype = ctypes.POINTER(libfive_mesh_t)
try:
    # the same for a shape with var()s: the trees of the variables and the numbers they stand for (inside the application)
    lib.libfive_tree_render_mesh_vars.argtypes = [libfive_tree, libfive_region_t, ctypes.c_float,
                                                  ctypes.POINTER(libfive_tree), ctypes.POINTER(ctypes.c_float),
                                                  ctypes.c_int]
    lib.libfive_tree_render_mesh_vars.restype = ctypes.POINTER(libfive_mesh_t)
except AttributeError:
    pass    # an older library: the numbers of var()s are read as 0

# algo: 0=dual contouring (default/fastest), 1=iso simplex, 2=hybrid.
# hybrid/simplex are slower but measurably more robust for STEP-imported
# oracle shapes -- dual contouring was found to fragment meshes it
# shouldn't (see step import notes) even when the underlying field is
# provably correct at every queried point.
lib.libfive_tree_render_mesh_algo.argtypes = [libfive_tree, libfive_region_t, ctypes.c_float,
                                               ctypes.c_int, ctypes.c_double, ctypes.c_int]
lib.libfive_tree_render_mesh_algo.restype = ctypes.POINTER(libfive_mesh_t)

lib.libfive_mesh_delete.argtypes = [ctypes.POINTER(libfive_mesh_t)]

# Batch evaluation (newer libraries; optional so older DLLs still load)
try:
    lib.libfive_tree_grid_stats.argtypes = [libfive_tree, ctypes.POINTER(ctypes.c_float),
                                            ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                                            ctypes.c_int, ctypes.c_int,
                                            ctypes.POINTER(ctypes.c_double)]
    lib.libfive_tree_grid_stats.restype = ctypes.c_bool
except AttributeError:
    pass


class libfive_surface_patch_t(ctypes.Structure):
    _fields_ = [("points", ctypes.POINTER(ctypes.c_float)),
                ("normals", ctypes.POINTER(ctypes.c_float)),
                ("count", ctypes.c_uint32),
                ("seed_point", ctypes.c_double * 3),
                ("seed_distance", ctypes.c_double),
                ("spacing", ctypes.c_double),
                ("stopped", ctypes.c_int32)]

try:
    # A patch of a surface found by walking over it from a seed, from the field alone; the field of a set of points
    lib.libfive_surface_select.argtypes = [libfive_tree, ctypes.POINTER(libfive_tree), ctypes.POINTER(ctypes.c_float),
                                           ctypes.c_int, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
                                           ctypes.POINTER(ctypes.c_double), ctypes.c_double, ctypes.c_int, ctypes.c_double,
                                           ctypes.c_double]
    lib.libfive_surface_select.restype = ctypes.POINTER(libfive_surface_patch_t)
    lib.libfive_surface_patch_delete.argtypes = [ctypes.POINTER(libfive_surface_patch_t)]
    lib.libfive_surface_patch_delete.restype = None
    lib.libfive_points_distance.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_uint32]
    lib.libfive_points_distance.restype = libfive_tree
    lib.libfive_points_surface.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_uint32,
                                           ctypes.c_double]
    lib.libfive_points_surface.restype = libfive_tree
    lib.libfive_surface_last_error.argtypes = []
    lib.libfive_surface_last_error.restype = ctypes.c_char_p
except AttributeError:
    pass


# Shapes made of points: the line through them and their plane (newer libraries; optional)
try:
    _dp = ctypes.POINTER(ctypes.c_double)
    _ip = ctypes.POINTER(ctypes.c_int)
    lib.libfive_pointshape_polyline.argtypes = [_dp, _ip, _ip, _dp, _dp, _dp, _dp, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, _dp, _ip, _dp, ctypes.c_int]
    lib.libfive_pointshape_polyline.restype = ctypes.c_int
    lib.libfive_pointshape_fillets.argtypes = [_dp, _ip, _dp, _dp, ctypes.c_int, ctypes.c_int, ctypes.c_int, _dp, ctypes.c_int]
    lib.libfive_pointshape_fillets.restype = ctypes.c_int
    lib.libfive_pointshape_plane.argtypes = [_dp, ctypes.c_int, _dp]
    lib.libfive_pointshape_plane.restype = ctypes.c_bool
except AttributeError:
    pass

# Analysis fields (newer libraries; optional)
try:
    lib.libfive_field_gradient.argtypes = [libfive_tree, ctypes.c_int]
    lib.libfive_field_gradient.restype = libfive_tree
    lib.libfive_field_curvature.argtypes = [libfive_tree, ctypes.c_float]
    lib.libfive_field_curvature.restype = libfive_tree
except AttributeError:
    pass


# Data fields (newer libraries; optional)
try:
    lib.libfive_field_points.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                                         ctypes.c_int, ctypes.c_int, ctypes.c_float]
    lib.libfive_field_points.restype = libfive_tree
    lib.libfive_field_noise.argtypes = [ctypes.c_float, ctypes.c_int, ctypes.c_uint, ctypes.c_float,
                                        ctypes.c_float]
    lib.libfive_field_noise.restype = libfive_tree
    lib.libfive_field_cellular.argtypes = [ctypes.c_float, ctypes.c_uint, ctypes.c_int, ctypes.c_float]
    lib.libfive_field_cellular.restype = libfive_tree
except AttributeError:
    pass


