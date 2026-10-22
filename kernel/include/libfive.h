/*
libfive: a CAD kernel for modeling with implicit functions
Copyright (C) 2017  Matt Keeter

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#pragma once

#ifdef __cplusplus
#include <cstdint>
#include "libfive/tree/tree.hpp"
#include "libfive/eval/evaluator.hpp"
extern "C" {
#else
#include <stdint.h>
#include <stdbool.h>
#endif

/*
 *  libfive_interval is a range used in interval arithmetic
 *  It usually represents either a spatial region (along a single axis)
 *  or a range that is guaranteed to contain a value.
 */
typedef struct libfive_interval  { float lower; float upper; } libfive_interval;

/*
 *  libfive_region2:  A 2D region
 */
typedef struct libfive_region2   { libfive_interval X, Y; } libfive_region2;

/*
 *  libfive_region3:  A 3D region
 */
typedef struct libfive_region3   { libfive_interval X, Y, Z; } libfive_region3;

/*
 *  libfive_vec2:  A 2D point or vector
 */
typedef struct libfive_vec2      { float x, y; } libfive_vec2;

/*
 *  libfive_vec3:  A 3D point or vector
 */
typedef struct libfive_vec3      { float x, y, z; } libfive_vec3;

/*
 *  libfive_vec4:  A 4D point or vector
 */
typedef struct libfive_vec4      { float x, y, z, w; } libfive_vec4;

/*
 *  libfive_tri:    A triangle, with corners stored as indices
 *  into a separate vertex array
 */
typedef struct libfive_tri       { uint32_t a, b, c; } libfive_tri;

/*
 *  libfive_contour is a single 2D contour, consisting of a sequence of
 *  2D points plus a count of how many points are stored
 */
typedef struct libfive_contour {
    libfive_vec2* pts;
    uint32_t count;
} libfive_contour;

/*
 *  libfive_contour is a set of 2D contours, consisting of multiple
 *  libfive_contour objects and a count of how many are stored
 */
typedef struct libfive_contours {
    libfive_contour* cs;
    uint32_t count;
} libfive_contours;

/*
 *  libfive_contour3 is a single 2D contour, consisting of a sequence of
 *  3D points plus a count of how many points are stored
 */
typedef struct libfive_contour3 {
    libfive_vec3* pts;
    uint32_t count;
} libfive_contour3;

/*
 *  libfive_contours3 is a set of 2D contours, consisting of multiple
 *  libfive_contour3 objects and a count of how many are stored
 */
typedef struct libfive_contours3 {
    libfive_contour3* cs;
    uint32_t count;
} libfive_contours3;

/*
 *  libfive_mesh is an indexed 3D mesh.
 *  There are vert_count vertices, and tri_count triangles.
 */
typedef struct libfive_mesh {
    libfive_vec3* verts;
    libfive_tri* tris;
    uint32_t tri_count;
    uint32_t vert_count;
} libfive_mesh;

/*
 *  libfive_mesh_coords is an indexed 3D mesh, similar to
 *  libfive_mesh, with sets of vertex indices separated by -1 instead
 *  of using triangle structs. There are vert_count vertices, and
 *  coord_index_count coordinate indices (including the -1s), for
 *  coord_index_count / 4 total triangles.
 */
typedef struct libfive_mesh_coords {
    libfive_vec3* verts;
    uint32_t vert_count;
    int32_t* coord_indices;
    uint32_t coord_index_count;
} libfive_mesh_coords;

/*
 *  libfive_pixels is a bitmap representing occupancy
 *  There are width * height pixels, in row-major order
 */
typedef struct libfive_pixels {
    bool* pixels;
    uint32_t width;
    uint32_t height;
} libfive_pixels;

////////////////////////////////////////////////////////////////////////////////

/*
 *  Frees an libfive_contours data structure
 */
void libfive_contours_delete(libfive_contours* cs);

/*
 *  Frees an libfive_contours data structure
 */
void libfive_contours3_delete(libfive_contours3* cs);

/*
 *  Frees an libfive_mesh data structure
 */
void libfive_mesh_delete(libfive_mesh* m);

/*
 *  Frees an libfive_mesh_coords data structure
 */
void libfive_mesh_coords_delete(libfive_mesh_coords* m);

/*
 *  Frees an libfive_pixels data structure
 */
void libfive_pixels_delete(libfive_pixels* ps);

/*
 *  Takes a string description of an op-code ('min', 'max', etc) and
 *  returns the libfive::Opcode value, or -1 if no such value exists.
 */
int libfive_opcode_enum(const char* op);

/*
 *  Returns the number of arguments for the given opcode
 *  (either 0, 1, 2, or -1 if the opcode is invalid)
 */
int libfive_opcode_args(int op);

////////////////////////////////////////////////////////////////////////////////

/*  libfive_vars is a general-purpose struct for mapping a set of
 *  free variables to their values.  The variables are opaque
 *  pointers, i.e. values returned with libfive_tree_id. */
typedef struct libfive_vars {
    void* const* vars;
    float* values;
    uint32_t size;
} libfive_vars;
void libfive_vars_delete(libfive_vars* j);

////////////////////////////////////////////////////////////////////////////////

#ifdef __cplusplus
typedef const libfive::Tree::Data* libfive_tree;
typedef libfive::Evaluator *libfive_evaluator;
#else
typedef struct libfive_tree_ libfive_tree_;
typedef struct libfive_tree_* libfive_tree;

typedef struct libfive_evaluator_ libfive_evaluator_;
typedef struct libfive_evaluator_ *libfive_evaluator;
#endif

/*
 *  Constructs a new tree that returns the X coordinate
 */
libfive_tree libfive_tree_x();

/*
 *  Constructs a new tree that returns the Y coordinate
 */
libfive_tree libfive_tree_y();

/*
 *  Constructs a new tree that returns the Z coordinate
 */
libfive_tree libfive_tree_z();

/*
 *  Constructs a new tree that contains a free variable
 */
libfive_tree libfive_tree_var();

/*
 *  Returns true if the given tree is a free variable
 */
bool libfive_tree_is_var(libfive_tree t);

/*
 *  Gives a free variable the number it stands for in the evaluators that are made without the script's numbers (the analyses):
 *  what a parametric optimisation does to try a design.  Nothing happens for a tree that is not a free variable.
 */
void libfive_tree_set_var_value(libfive_tree t, float value);

/*
 *  Constructs a new tree that contains the given constant value
 */
libfive_tree libfive_tree_const(float f);

/*
 *  If t is a constant value, returns that value and sets *success to true.
 *  Otherwise, sets success to false and returns 0.
 */
float libfive_tree_get_const(libfive_tree t, bool* success);

/*
 *  Constructs a tree with the given no-argument opcode
 *  Returns NULL if the opcode is invalid.
 */
libfive_tree libfive_tree_nullary(int op);

/*
 *  Constructs a tree with the given one-argument opcode
 *  Returns NULL if the opcode or argument is invalid
 */
libfive_tree libfive_tree_unary(int op, libfive_tree a);

/*
 *  Constructs a tree with the given two-argument opcode
 *  Returns NULL if the opcode or arguments are invalid
 */
libfive_tree libfive_tree_binary(int op, libfive_tree a, libfive_tree b);

/*
 *  Returns a unique ID for the given tree.  There is no global deduplication;
 *  e.g. multiple calls to libfive_tree_const(1.0) will return trees with
 *  different IDs.
 *
 *  This is primarily used to uniquely identify free variables, i.e. trees
 *  returned from libfive_tree_var().
 */
const void* libfive_tree_id(libfive_tree t);

/*
 *  Evaluates the given math tree at the given position.
 *  TODO:  Free variables are treated as zero
 */
float libfive_tree_eval_f(libfive_tree t, libfive_vec3 p);

/*
 *  Evaluates the given math tree over a spatial region, returning an interval
 *  that is guaranteed to contain the result
 *  TODO:  Free variables are treated as zero
 */
libfive_interval libfive_tree_eval_r(libfive_tree t, libfive_region3 r);

/*
 *  Samples the tree at the cell centres of an nx x ny x nz grid over the box
 *  [lower, upper] and reports: out[0] number of samples < 0 (inside),
 *  out[1..3] sums of their x, y, z, out[4] / out[5] min / max value,
 *  out[6..8] sums of x^2, y^2, z^2 of the inside samples.  Returns false on
 *  bad arguments.
 */
bool libfive_tree_grid_stats(libfive_tree t, const float* lower3, const float* upper3,
                             int nx, int ny, int nz, double* out9);

/*
 *  Estimates the bounding box of a shape's interior (where the tree is
 *  <= 0) within the search region, by branch-and-bound on interval
 *  arithmetic.  The box is conservative (never smaller than the shape),
 *  within about 0.1% of the shape's size.  Returns false if the shape has
 *  no interior in the region or the search needs more than max_evals
 *  interval evaluations or max_seconds (if > 0) of time; a search cut
 *  short while refining returns the coarser box found so far.  Sides that reach the search region's faces (the
 *  shape may continue past them, e.g. a half-space) are flagged in `open`
 *  (bit 2*axis for the lower side, 2*axis+1 for the upper), if not NULL.
 */
bool libfive_tree_bounds(libfive_tree t, libfive_region3 search, int max_evals,
                         float max_seconds, libfive_region3* out, int* open);

/*
 *  The same for a shape with variables: `vars` (count of them) are the variable trees and `values`
 *  the numbers they stand for.
 */
bool libfive_tree_bounds_vars(libfive_tree t, libfive_region3 search, int max_evals, float max_seconds,
                              libfive_region3* out, int* open,
                              const libfive_tree* vars, const float* values, int count);

/*
 *  The same, coarser and much quicker: the box is found to within `rel_tol` of the longest side of the search region (0.02: two per cent) and not refined.  Still
 *  conservative (the box holds the shape); for what only needs to know roughly where a shape is -- the region it must be meshed over while it is dragged.
 */
bool libfive_tree_bounds_vars_coarse(libfive_tree t, libfive_region3 search, int max_evals, float max_seconds, float rel_tol,
                                     libfive_region3* out, int* open,
                                     const libfive_tree* vars, const float* values, int count);

/*
 *  The lowest value a tree can take anywhere in a box (interval arithmetic:
 *  a lower bound, never too high), with the numbers `values` for the
 *  variables `vars` (count of each).  A field with a positive lower bound
 *  is nowhere inside (negative) in the box.
 */
float libfive_tree_interval_lower(libfive_tree t, libfive_region3 box,
                                  const libfive_tree* vars, const float* values, int count);

/*
 *  Evaluates the partial derivatives of a math tree at a specific point,
 *  with respect to x, y, z.
 */
libfive_vec3 libfive_tree_eval_d(libfive_tree t, libfive_vec3 p);

/*  A second, independently owned handle to the same tree  */
libfive_tree libfive_tree_copy(libfive_tree t);

/*
 *  A script run's progress, for a GUI (see run_progress.hpp): the runner
 *  says how many steps (top-level statements) the script has and which one
 *  runs; an operation in a step (a loop, progress()) counts how far it is.
 *  Operations nest: one begun inside another counts within the share the
 *  outer one gave it with libfive_run_task_span.
 */
void libfive_run_begin(int steps);
void libfive_run_step(int index, const char* label);
/*  The (1-based) line the step just begun starts on  */
void libfive_run_step_line(int line);
void libfive_run_end(void);
void libfive_run_task_begin(const char* name);
void libfive_run_task_set(double fraction, const char* detail);
void libfive_run_task_span(double a, double b);
void libfive_run_task_end(void);

/*
 *  Evaluates a math tree at n points (xyz holds 3n floats) into out (n
 *  floats), with one evaluator per thread -- much faster than n calls
 *  to libfive_tree_eval_f for a large tree.
 */
void libfive_tree_eval_points(libfive_tree t, const float* xyz, int n, float* out);

/*
 *  Meshes a tree with variables (see libfive_tree_render_mesh): `vars` (count of them) are the variable
 *  trees and `values` the numbers they stand for.
 */
libfive_mesh* libfive_tree_render_mesh_vars(libfive_tree tree, libfive_region3 R, float res,
                                            const libfive_tree* vars, const float* values, int count);

/*
 *  The same for a shape with variables: `vars` (count of them) are the variable trees and `values` the
 *  numbers they stand for (without them every variable reads as 0).
 */
void libfive_tree_eval_points_vars(libfive_tree t, const float* xyz, int n, float* out,
                                   const libfive_tree* vars, const float* values, int count);

/*
 *  Deletes a tree.  If binding in a higher-level language, call this in
 *  a destructor / finalizer to avoid leaking memory
 */
void libfive_tree_delete(libfive_tree ptr);

/*
 *  Shapes made of points (see libfive/fields/point_shapes.hpp).  pos: 3n numbers, smooth: n of -1 (what the shape says), 0 (a corner) or 1 (a spline
 *  point), turned: n of 0/1, rotate: 3n degrees, scale: n numbers (how strongly a spline leaves each point: 1 is Catmull-Rom; may be null), normal: 3 numbers
 *  (the normal of the plane of a face: the points' rotation is then one angle, the z number of rotate, about it; null for a line in space), radius: n numbers (> 0 at
 *  a corner: a round corner, an exact arc of that radius takes its place; may be null).
 *  The line through them is written to out_vertices (3 numbers each), out_owner (the control each
 *  vertex is after) and out_t (how far along towards the next, 0 to 1), up to `capacity` vertices; the number of vertices is returned (more than
 *  capacity: nothing is written, and that many are needed).  `arc_pieces` is how many pieces an arc is cut into for a quarter turn (0: only its two ends, the chord)
 */
int libfive_pointshape_polyline(const double* pos, const int* smooth, const int* turned, const double* rotate, const double* scale, const double* radius,
                                const double* normal, int n, int smooth_default, int closed, int pieces, int arc_pieces,
                                double* out_vertices, int* out_owner, double* out_t, int capacity);
/*  The round corners (arcs) of the same points, as 11 numbers each: the control, the two ends of the arc (a, b: 3 numbers each), its centre (3) and its radius as made
 *  (smaller than asked where it would run into the next arc).  Up to `capacity` arcs; the number of arcs is returned (more than capacity: nothing is written)  */
int libfive_pointshape_fillets(const double* pos, const int* smooth, const double* radius, const double* normal, int n, int smooth_default, int closed,
                               double* out, int capacity);
/*  The plane through the first three points that are not on a line: frame = origin, u, v (9 numbers); false when there is none  */
bool libfive_pointshape_plane(const double* pos, int n, double* frame);
/*  The distance to the closed polygon `loop` (2n numbers: their position along u and along v of `frame`, or x and y when frame is null), negative
 *  inside; the distance to the line through the vertices (3n numbers)  */

/*
 *  Fields of a shape: mode 0..2 = x/y/z of the unit normal, 3 = the
 *  gradient's length, 4..6 = raw gradient; the mean curvature (central
 *  differences of step h).
 */
libfive_tree libfive_field_gradient(libfive_tree t, int mode);
libfive_tree libfive_field_curvature(libfive_tree t, float h);
/*  A field through n scattered samples (xyz: 3n floats, values: n floats),
 *  inverse-distance weighted over the k nearest; and seeded Perlin noise  */
libfive_tree libfive_field_points(const float* xyz, const float* values, int n, int k,
                                  float power);
libfive_tree libfive_field_noise(float scale, int octaves, unsigned seed, float gain,
                                 float lacunarity);
/*  Cellular (Worley) noise at one scale: mode 0 the distance to the nearest point of a jittered grid, 1 the distance from a wall between cells (F2 - F1), 2 the
 *  distance to the second nearest point; about -1 .. 1.  jitter 0 .. 1: 0 is a regular grid  */
libfive_tree libfive_field_cellular(float scale, unsigned seed, int mode, float jitter);

/*  Debug: print the native stack of the first access violation (Windows)  */
void libfive_debug_crash_handler(void);

/*  Serializes the given tree to a file, return true on success.
 *  The file format is not archival, and may change without notice */
bool libfive_tree_save(libfive_tree ptr, const char* filename);

/*  Can the whole tree be kept in a file and read back?  (Every oracle in it knows how to save itself.)  libfive_tree_save
 *  refuses a tree that cannot.  */
bool libfive_tree_can_save(libfive_tree ptr);

/*
 *  Which of the coordinates a tree depends on: bit 0 for x, bit 1 for y, bit 2 for z (a tree that holds an oracle,
 *  which is a field of all of space, has all three).  A shape of no z is a 2D profile.
 */
int libfive_tree_axes(libfive_tree ptr);

/*  Deserializes a tree from a file. */
libfive_tree libfive_tree_load(const char* filename);

/*  A patch of a surface, found by walking over it from a seed: the flood fill of a CAD program, from the field alone (its value
 *  and gradient: no mesh).  `seed3` is a point on or near the surface; the walk spreads over the surface in steps of `spacing`
 *  while it stays within `angle_degrees` of the seed's own direction (mode 0) or turns less than `angle_degrees` for every 10 mm of the walk (mode 1), and within
 *  `max_radius` (<= 0: no limit) of the seed; `lo3`..`hi3` is the box of the body.  Returns the samples of the patch's surface
 *  (about `spacing` apart, with the normals) or NULL with libfive_surface_last_error() set; free it with
 *  libfive_surface_patch_delete.  libfive_points_distance makes the field of a set of points: the distance to the nearest.  */
typedef struct libfive_surface_patch {
    float* points;          /*  3 floats a sample  */
    float* normals;
    uint32_t count;
    double seed_point[3];   /*  where the seed is on the surface  */
    double seed_distance;
    double spacing;
    int32_t stopped;        /*  1: the walk was cut short (too many samples)  */
} libfive_surface_patch;

libfive_surface_patch* libfive_surface_select(libfive_tree body, const libfive_tree* vars, const float* values, int var_count,
                                              const double* lo3, const double* hi3, const double* seed3,
                                              double angle_degrees, int mode, double max_radius, double spacing);
void libfive_surface_patch_delete(libfive_surface_patch* p);
libfive_tree libfive_points_distance(const float* xyz, uint32_t count);
/*  Why the last libfive_surface_select / libfive_points_* failed  */
const char* libfive_surface_last_error(void);

/*  The surface the samples of a patch make, as a field: the height above it along the normals (`normals`, 3 floats a sample), zero on it,
 *  positive on the side they face, blended over `sigma`.  A surface and nothing else: no body behind it, so nothing of a thickness.  */
libfive_tree libfive_points_surface(const float* xyz, const float* normals, uint32_t count, double sigma);

/*  Triangle-mesh import (.stl binary / ASCII, .obj): the returned tree is
 *  the exact signed distance to the triangles (negative inside), after
 *  welding, cleaning and re-orienting them; every coordinate is multiplied
 *  by `scale`.  Returns NULL on failure; libfive_import_mesh_last_message()
 *  then says why (and after a success, summarises the mesh).  `info` may
 *  be NULL.  */
typedef struct libfive_mesh_import_info {
    uint32_t triangles;
    uint32_t vertices;
    uint32_t components;          /*  connected shells  */
    uint32_t boundary_edges;      /*  edges of a single triangle (holes)  */
    uint32_t nonmanifold_edges;   /*  edges of more than two triangles  */
    uint32_t reoriented;          /*  triangles whose winding was flipped  */
    uint32_t dropped;             /*  degenerate / duplicate triangles  */
    uint8_t watertight;
    uint8_t winding_sign;         /*  winding number used where the sign is unclear  */
    libfive_region3 bounds;
} libfive_mesh_import_info;

libfive_tree libfive_import_mesh(const char* filename, float scale,
                                 libfive_mesh_import_info* info);

/*  The unsigned distance to the triangles with selected[i] != 0 (an open patch of a surface has no
 *  inside).  NULL on failure.  */
libfive_tree libfive_mesh_patch(const float* xyz, uint32_t vertex_count, const uint32_t* tri,
                                uint32_t tri_count, const uint8_t* selected, libfive_mesh_import_info* info);

/*  The same from triangles in memory: `xyz` holds 3 * vertex_count floats,
 *  `tri` 3 * tri_count vertex indices (0-based).  */
libfive_tree libfive_mesh_from_arrays(const float* xyz, uint32_t vertex_count,
                                      const uint32_t* tri, uint32_t tri_count,
                                      float scale, libfive_mesh_import_info* info);
const char* libfive_import_mesh_last_message(void);

/*  Executes the remapping operation returning a tree
 *  q(x, y, z) = p(x'(x, y, z), y'(x, y, z), z'(x, y, z)) */
libfive_tree libfive_tree_remap(libfive_tree p,
        libfive_tree x, libfive_tree y, libfive_tree z);

/*  The field p evaluated at the point (x'(x, y, z), y'(x, y, z), z'(x, y, z)):
 *  the same field as libfive_tree_remap, evaluated in another way.  A remap is
 *  expanded into a copy of p for each use; a call keeps p where it is (it is
 *  compiled once into a tape of its own and every call runs that tape), so a
 *  field that is asked at many places is not copied for each.  */
libfive_tree libfive_tree_call(libfive_tree p,
        libfive_tree x, libfive_tree y, libfive_tree z);

/*  The partial derivative of p with respect to x (axis 0), y (1) or z (2), as a tree of its own: the symbolic derivative, by the rules of
 *  calculus (see libfive/tree/derivative.hpp).  A native field (an oracle) inside p has no formula: with oracle_step > 0 its partial is the
 *  central difference over that step; with 0 the result is NULL.  NULL too for an axis that is not 0, 1 or 2, and for a tree whose calls are nested deeper than
 *  max_call_depth (a derivative costs several times what the field does for every level of nesting; -1: no limit).  */
libfive_tree libfive_tree_partial(libfive_tree p, int axis, float oracle_step, int max_call_depth);

/*
 *  Returns an optimized version of the given tree
 */
libfive_tree libfive_tree_optimized(libfive_tree t);

/*
 *  Returns a C string representing the tree in Scheme style
 *  (e.g. "(+ 1 2 x y)" )
 *
 *  The caller is responsible for freeing the string with libfive_free()
 */
char* libfive_tree_print(libfive_tree t);

/*
 *  An exact key of the tree's structure (two separately built trees that are
 *  the same expression have the same key; see libfive/tree/content_key.hpp),
 *  as text.  Unlike the printed tree it writes every constant in full and
 *  tells oracles and free variables apart.  Free with libfive_free_str.
 */
char* libfive_tree_content_key(libfive_tree t);

/*
 *  The key the render cache keeps a shape's mesh by (libfive::treePersistentKey of the tree as built, not optimized: free
 *  variables count by their value, `values` of the `count` variables `vars`; an oracle by what it holds), as text,
 *  or NULL when the tree holds something no other run could recognise (a solved analysis, a variable with no
 *  value).  Free with libfive_free_str.
 */
char* libfive_tree_persistent_key(libfive_tree t, const libfive_tree* vars, const float* values, int count);

/*
 *  The numbers of a tree that place its surfaces (a plane's offset, a radius,
 *  a box's faces: see libfive/tree/expose.hpp), which Studio can make
 *  draggable.  libfive_tree_expose_count says how many there are,
 *  libfive_tree_expose_values writes their values (that many floats), and
 *  libfive_tree_expose returns the tree with each of them replaced by the
 *  given tree (usually a free variable), in the same order -- or NULL when
 *  `count` is not the number there are.
 */
int libfive_tree_expose_count(libfive_tree t);
void libfive_tree_expose_values(libfive_tree t, float* out);
libfive_tree libfive_tree_expose(libfive_tree t, libfive_tree* with, int count);

/*
 *  Frees a string allocated by libfive (probably by libfive_tree_print
 */
void libfive_free_str(char* ptr);

////////////////////////////////////////////////////////////////////////////////

/*
 *  Renders a tree to a set of contours
 *
 *  R is a region that will be subdivided into an octree.  For clean
 *  triangles, it should be near-cubical, but that isn't a hard requirement
 *
 *  res should be approximately half the model's smallest feature size;
 *  subdivision halts when all sides of the region are below it.
 *
 *  The returned struct must be freed with libfive_contours_delete
 */
libfive_contours* libfive_tree_render_slice(libfive_tree tree,
                                            libfive_region2 R,
                                            float z, float res);
/*
 *  Renders a tree to a set of contours, similar to libfive_tree_render_slice,
 *  except the contours are 3D points (see the libfive_contour3 struct) above.
 */
libfive_contours3* libfive_tree_render_slice3(libfive_tree tree,
                                              libfive_region2 R,
                                              float z, float res);

/*
 *  Renders and saves a slice to a file
 *
 *  See argument details in libfive_tree_render_slice
 */
void libfive_tree_save_slice(libfive_tree tree, libfive_region2 R,
                             float z, float res, const char* f);

/*
 *  Renders a tree to a set of triangles
 *
 *  R is a region that will be subdivided into an octree.  For clean
 *  triangles, it should be near-cubical, but that isn't a hard requirement
 *
 *  res should be approximately half the model's smallest feature size;
 *  subdivision halts when all sides of the region are below it.
 *
 *  The returned struct must be freed with libfive_mesh_delete
 */
libfive_mesh* libfive_tree_render_mesh(libfive_tree tree,
                                       libfive_region3 R, float res);
/*
 * Same as libfive_tree_render_mesh, but forces single-threaded meshing to
 * play nicely with FFI.
 */
libfive_mesh* libfive_tree_render_mesh_st(libfive_tree tree,
                                       libfive_region3 R, float res);
/*
 * Debug/diagnostic only: same as libfive_tree_render_mesh, but lets the
 * caller pick the meshing algorithm (0=dual contouring, 1=iso simplex,
 * 2=hybrid) and max_err (cell-merging tolerance; -1 disables merging).
 */
libfive_mesh* libfive_tree_render_mesh_algo(libfive_tree tree,
                                       libfive_region3 R, float res,
                                       int algo, double max_err, int workers);
/*
 *  Renders to an alternate mesh format, see description of
 *  libfive_mesh_coords above.  The returned struct must be freed with
 *  libfive_mesh_coords_delete.
 */
libfive_mesh_coords* libfive_tree_render_mesh_coords(libfive_tree tree,
                                                     libfive_region3 R,
                                                     float res);

/*
 *  Renders and saves a mesh to a file
 *
 *  Returns true on success, false otherwise
 *  See argument details in libfive_tree_render_mesh
 */
bool libfive_tree_save_mesh(libfive_tree tree, libfive_region3 R,
                            float res, const char* f);

/*
 *  Renders and saves a mesh to a file
 *
 *  Returns true on success, false otherwise
 *  Second argument is an evaluator
 *  See other argument details in libfive_tree_render_mesh
 */
bool libfive_evaluator_save_mesh(libfive_evaluator evaluator, libfive_region3 R,
                                 const char *f);

/*
 *  Renders and saves multiple meshes mesh to a file
 *
 *  Returns true on success, false otherwise
 *
 *  Arguments are equivalent to Studio's resolution and quality
 *  settings.  In particular quality is a value q such that we
 *  collapse cells when the QEF error is below 10**(-q)
 *
 *  trees is a null-terminated list (since libfive_tree is a pointer
 *  under the hood).
 */
bool libfive_tree_save_meshes(
        libfive_tree trees[], libfive_region3 R,
        float res, float quality, const char* f);

/*
 *  Renders a 2D slice of pixels at the given Z height
 *
 *  The returned struct must be freed with libfive_pixels_delete
 */
libfive_pixels* libfive_tree_render_pixels(libfive_tree tree,
                                           libfive_region2 R,
                                           float z, float res);

/*
 *  Constructs a new evaluator
 */
libfive_evaluator libfive_tree_evaluator(libfive_tree tree, libfive_vars vars);

/*
 *  Updates the variables of the evaluator
 */
bool libfive_evaluator_update_vars(libfive_evaluator eval_tree, libfive_vars vars);

/*
 *  Deletes (first) evaluator.  TODO: if settings.workers > 1
 */
void libfive_evaluator_delete(libfive_evaluator ptr);

/*
 *  Returns the human-readable tag associated with this build,
 *  or the empty string if there is no such tag
 */
const char* libfive_git_version(void);

/*
 *  Returns the 7-character git hash associated with this build,
 *  with a trailing '+' if there are local (uncommitted) modifications
 */
const char* libfive_git_revision(void);

/*
 *  Returns the name of the branch associated with this build
 */
const char* libfive_git_branch(void);

#ifdef __cplusplus
}
#endif
