/*
libfive: a CAD kernel for modeling with implicit functions
Copyright (C) 2017  Matt Keeter

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#include <cstring>
#include <algorithm>
#include <array>
#include <chrono>
#include <map>
#include <cmath>
#include <queue>
#include <limits>
#include <mutex>
#include <thread>
#include <vector>
#include <iostream>
#include <fstream>
#include <sstream>

#include "libfive.h"

#include "libfive/tree/opcode.hpp"
#include "libfive/tree/tree.hpp"
#include "libfive/tree/data.hpp"
#include "libfive/tree/content_key.hpp"
#include "libfive/tree/derivative.hpp"
#include "libfive/tree/expose.hpp"
#include "libfive/eval/default_vars.hpp"
#include "libfive/oracle/oracle_clause.hpp"
#include "libfive/fields/point_shapes.hpp"

#include "libfive/eval/eval_deriv_array.hpp"
#include "libfive/eval/eval_interval.hpp"

#include "libfive/render/brep/region.hpp"
#include "libfive/render/brep/contours.hpp"
#include "libfive/render/brep/mesh.hpp"
#include "libfive/render/brep/settings.hpp"

#include "libfive/render/discrete/voxels.hpp"
#include "libfive/render/discrete/heightmap.hpp"

#include "libfive/mesh_import/mesh_import.hpp"
#include "libfive/run_progress.hpp"
#include "libfive/fields/surface_select.hpp"
#include "libfive/fields/field_oracles.hpp"

using namespace libfive;

void libfive_contours_delete(libfive_contours* cs)
{
    for (unsigned i=0; i < cs->count; ++i)
    {
        delete [] cs->cs[i].pts;
    }
    delete [] cs->cs;
    delete cs;
}

void libfive_contours3_delete(libfive_contours3* cs)
{
    for (unsigned i=0; i < cs->count; ++i)
    {
        delete [] cs->cs[i].pts;
    }
    delete [] cs->cs;
    delete cs;
}

void libfive_mesh_delete(libfive_mesh* m)
{
    delete [] m->verts;
    delete [] m->tris;
    delete m;
}

void libfive_mesh_coords_delete(libfive_mesh_coords* m)
{
    delete [] m->verts;
    delete [] m->coord_indices;
    delete m;
}

void libfive_pixels_delete(libfive_pixels* m)
{
    delete [] m->pixels;
    delete m;
}

void libfive_vars_delete(libfive_vars* vs)
{
    delete [] vs->vars;
    delete [] vs->values;
    delete vs;
}

int libfive_opcode_enum(const char* op)
{
    auto o = Opcode::fromScmString(op);
    return (o == Opcode::INVALID || o == Opcode::LAST_OP) ? -1 : o;
}

int libfive_opcode_args(int op)
{
    return (op >= 0 && op < Opcode::LAST_OP)
        ? Opcode::args(Opcode::Opcode(op))
        : -1;
}

////////////////////////////////////////////////////////////////////////////////

libfive_tree libfive_tree_x() { return Tree::X().release(); }
libfive_tree libfive_tree_y() { return Tree::Y().release(); }
libfive_tree libfive_tree_z() { return Tree::Z().release(); }

libfive_tree libfive_tree_const(float f) { return Tree(f).release(); }
libfive_tree libfive_tree_var() { return Tree::var().release(); }

bool libfive_tree_is_var(libfive_tree t)
{
    return t->op() == Opcode::VAR_FREE;
}

void libfive_tree_set_var_value(libfive_tree t, float value)
{
    if (t && t->op() == Opcode::VAR_FREE) DefaultVars::set(t, value);
}

float libfive_tree_get_const(libfive_tree t, bool* success)
{
    if (t->op() == Opcode::CONSTANT)
    {
        if (success) { *success = true; }
        return t->value();
    }
    if (success) { *success = false; }
    return 0;
}

static bool opcode_is_valid(int op, size_t expected_args)
{
    return op >= 0 &&
           op < Opcode::LAST_OP &&
           Opcode::args(Opcode::Opcode(op)) == expected_args;
}

libfive_tree libfive_tree_nullary(int op)
{
    return opcode_is_valid(op, 0)
        ? Tree::nullary(Opcode::Opcode(op)).release()
        : nullptr;
}

libfive_tree libfive_tree_unary(int op, libfive_tree a)
{
    return (opcode_is_valid(op, 1) && a != nullptr)
        ? Tree::unary(Opcode::Opcode(op), Tree(a)).release()
        : nullptr;
}

libfive_tree libfive_tree_binary(int op, libfive_tree a, libfive_tree b)
{
    return (opcode_is_valid(op, 2) && a != nullptr && b != nullptr)
        ? Tree::binary(Opcode::Opcode(op), Tree(a), Tree(b)).release()
        : nullptr;
}

const void* libfive_tree_id(libfive_tree t)
{
    return static_cast<const void*>(t);
}

void libfive_tree_delete(libfive_tree ptr)
{
    // Reclaim the ptr (without incrementing the refcount), which
    // then decrements the refcount when the Tree destructor is run.
    Tree::reclaim(ptr);
}

namespace {
bool canKeep(const Tree& t)
{
    const Tree flat = t.flatten(true, Tree::Calls::Keep);      // (kept: walk() of a tree with remaps points into a flattened copy)
    for (auto& n : flat.walk_deep())        // (and the fields that calls call)
    {
        if (n->op() != Opcode::ORACLE) continue;
        if (!OracleClause::canSerialize(n->oracle_clause().name())) return false;
        for (const auto& d : n->oracle_clause().dependencies())
            if (!canKeep(d)) return false;
    }
    return true;
}
}

bool libfive_tree_can_save(libfive_tree ptr)
{
    return canKeep(Tree(ptr));
}

int libfive_tree_axes(libfive_tree ptr)
{
    int mask = 0;
    // (a call depends on the coordinates through its arguments only: the field that it calls has coordinates of its own, which are not walked)
    const Tree flat = Tree(ptr).flatten(true, Tree::Calls::Keep);      // (kept: walk() of a tree with remaps points into a flattened copy)
    for (auto& n : flat.walk())
    {
        switch (n->op())
        {
            case Opcode::VAR_X: mask |= 1; break;
            case Opcode::VAR_Y: mask |= 2; break;
            case Opcode::VAR_Z: mask |= 4; break;
            case Opcode::ORACLE: mask |= 7; break;      // (a mesh, a data field: at any point of space)
            default: break;
        }
    }
    return mask;
}
bool libfive_tree_save(libfive_tree ptr, const char* filename)
{
    if (!canKeep(Tree(ptr)))
    {
        std::cerr << "libfive_tree_save: the tree holds an oracle that cannot be saved" << std::endl;
        return false;
    }
    std::ofstream out;
    out.open(filename, std::ios::out|std::ios::binary);
    if (out.is_open())
    {
        Tree(ptr).serialize(out);
        return true;
    }
    else
    {
        std::cerr << "libfive_tree_save: could not open file" << std::endl;
        return false;
    }
}

libfive_tree libfive_tree_load(const char* filename)
{
    auto t = Tree::load(filename);
    if (t.id() && t.is_valid())
    {
        return t.release();
    }
    else
    {
        std::cerr <<  "libfive_tree_load: could not open file" << std::endl;
        return nullptr;
    }
}

namespace {
    thread_local std::string g_mesh_last_message;
}

static libfive_tree finishMeshImport(Tree t, bool ok, const std::string& error,
                                     const mesh::MeshImportInfo& mi,
                                     libfive_mesh_import_info* info);

libfive_tree libfive_import_mesh(const char* filename, float scale,
                                 libfive_mesh_import_info* info)
{
    bool ok = false;
    std::string error;
    mesh::MeshImportInfo mi;
    Tree t = mesh::importMeshTree(filename, scale, mi, ok, error);
    return finishMeshImport(std::move(t), ok, error, mi, info);
}

libfive_tree libfive_mesh_from_arrays(const float* xyz, uint32_t vertex_count,
                                      const uint32_t* tri, uint32_t tri_count,
                                      float scale, libfive_mesh_import_info* info)
{
    bool ok = false;
    std::string error;
    mesh::MeshImportInfo mi;
    Tree t = mesh::meshTreeFromArrays(xyz, vertex_count, tri, tri_count, scale, mi, ok, error);
    return finishMeshImport(std::move(t), ok, error, mi, info);
}

libfive_tree libfive_mesh_patch(const float* xyz, uint32_t vertex_count, const uint32_t* tri,
                                uint32_t tri_count, const uint8_t* selected, libfive_mesh_import_info* info)
{
    bool ok = false;
    std::string error;
    mesh::MeshImportInfo mi;
    Tree t = mesh::patchTreeFromArrays(xyz, vertex_count, tri, tri_count, selected, mi, ok, error);
    return finishMeshImport(std::move(t), ok, error, mi, info);
}

static libfive_tree finishMeshImport(Tree t, bool ok, const std::string& error,
                                     const mesh::MeshImportInfo& mi,
                                     libfive_mesh_import_info* info)
{
    if (!ok)
    {
        g_mesh_last_message = error;
        return nullptr;
    }

    std::ostringstream msg;
    msg << mi.triangles << " triangles, " << mi.components << " shell"
        << (mi.components == 1 ? "" : "s");
    if (mi.watertight)
    {
        msg << ", watertight";
    }
    else
    {
        msg << "; NOT watertight (" << mi.boundaryEdges << " open edge"
            << (mi.boundaryEdges == 1 ? "" : "s") << ", " << mi.nonManifoldEdges
            << " non-manifold): inside/outside is estimated";
    }
    if (mi.reoriented)
    {
        msg << "; " << mi.reoriented << " triangle" << (mi.reoriented == 1 ? "" : "s")
            << " re-oriented";
    }
    if (mi.dropped)
    {
        msg << "; " << mi.dropped << " degenerate/duplicate triangle"
            << (mi.dropped == 1 ? "" : "s") << " dropped";
    }
    g_mesh_last_message = msg.str();

    if (info)
    {
        info->triangles = static_cast<uint32_t>(mi.triangles);
        info->vertices = static_cast<uint32_t>(mi.vertices);
        info->components = static_cast<uint32_t>(mi.components);
        info->boundary_edges = static_cast<uint32_t>(mi.boundaryEdges);
        info->nonmanifold_edges = static_cast<uint32_t>(mi.nonManifoldEdges);
        info->reoriented = static_cast<uint32_t>(mi.reoriented);
        info->dropped = static_cast<uint32_t>(mi.dropped);
        info->watertight = mi.watertight;
        info->winding_sign = mi.windingSign;
        info->bounds.X = {static_cast<float>(mi.lower[0]), static_cast<float>(mi.upper[0])};
        info->bounds.Y = {static_cast<float>(mi.lower[1]), static_cast<float>(mi.upper[1])};
        info->bounds.Z = {static_cast<float>(mi.lower[2]), static_cast<float>(mi.upper[2])};
    }
    return t.release();
}

const char* libfive_import_mesh_last_message(void)
{
    return g_mesh_last_message.c_str();
}

libfive_tree libfive_tree_remap(libfive_tree p, libfive_tree x, libfive_tree y, libfive_tree z)
{
    return Tree(p).remap(Tree(x), Tree(y), Tree(z)).release();
}

libfive_tree libfive_tree_call(libfive_tree p, libfive_tree x, libfive_tree y, libfive_tree z)
{
    return Tree(p).call(Tree(x), Tree(y), Tree(z)).release();
}

libfive_tree libfive_tree_partial(libfive_tree t, int axis, float oracle_step, int max_call_depth)
{
    const Tree out = libfive::partial_derivative(Tree(t), axis, oracle_step, max_call_depth);
    if (!out.is_valid())
    {
        return nullptr;
    }
    return Tree(out).release();
}

libfive_tree libfive_tree_optimized(libfive_tree t) {
    return Tree(t).optimized().release();
}

float libfive_tree_eval_f(libfive_tree t, libfive_vec3 p)
{
    ArrayEvaluator e((Tree(t)));
    return e.value({p.x, p.y, p.z});
}

namespace {
// Runs fn(first, last) over [0, n) in parallel chunks
template <typename F>
void parallelChunks(size_t n, size_t minChunk, F fn)
{
    const size_t hw = std::max(1u, std::thread::hardware_concurrency());
    const size_t threads = std::min(hw, std::max<size_t>(1, n / minChunk));
    if (threads <= 1)
    {
        fn(size_t(0), n);
        return;
    }
    std::vector<std::thread> pool;
    const size_t per = (n + threads - 1) / threads;
    for (size_t t = 0; t < threads; ++t)
    {
        const size_t a = t * per, b = std::min(n, a + per);
        if (a >= b) break;
        pool.emplace_back([&fn, a, b]() { fn(a, b); });
    }
    for (auto& th : pool) th.join();
}
}   // anonymous namespace

bool libfive_tree_grid_stats(libfive_tree t, const float* lower3, const float* upper3,
                             int nx, int ny, int nz, double* out9)
{
    if (!t || !lower3 || !upper3 || !out9 || nx < 1 || ny < 1 || nz < 1) return false;
    const Tree tree(t);
    const size_t total = size_t(nx) * ny * nz;
    const float h[3] = {(upper3[0] - lower3[0]) / nx, (upper3[1] - lower3[1]) / ny,
                        (upper3[2] - lower3[2]) / nz};
    std::mutex lock;
    double acc[9] = {0, 0, 0, 0, std::numeric_limits<double>::infinity(),
                     -std::numeric_limits<double>::infinity(), 0, 0, 0};
    parallelChunks(total, 1 << 16, [&](size_t first, size_t last) {
        ArrayEvaluator e(tree);
        const size_t N = ArrayEvaluator::N;
        double a[9] = {0, 0, 0, 0, std::numeric_limits<double>::infinity(),
                       -std::numeric_limits<double>::infinity(), 0, 0, 0};
        Eigen::Vector3f pts[LIBFIVE_EVAL_ARRAY_SIZE];
        for (size_t start = first; start < last; start += N)
        {
            const size_t count = std::min(N, last - start);
            for (size_t k = 0; k < count; ++k)
            {
                const size_t idx = start + k;
                const size_t i = idx % nx, j = (idx / nx) % ny, kk = idx / (size_t(nx) * ny);
                pts[k] = Eigen::Vector3f(lower3[0] + (i + 0.5f) * h[0], lower3[1] + (j + 0.5f) * h[1],
                                         lower3[2] + (kk + 0.5f) * h[2]);
                e.set(pts[k], k);
            }
            const auto vs = e.values(count);
            for (size_t k = 0; k < count; ++k)
            {
                const float v = vs(k);
                if (v < a[4]) a[4] = v;
                if (v > a[5]) a[5] = v;
                if (v < 0)
                {
                    a[0] += 1;
                    for (int c = 0; c < 3; ++c)
                    {
                        a[1 + c] += pts[k][c];
                        a[6 + c] += double(pts[k][c]) * pts[k][c];
                    }
                }
            }
        }
        std::lock_guard<std::mutex> g(lock);
        for (int c = 0; c < 4; ++c) acc[c] += a[c];
        for (int c = 6; c < 9; ++c) acc[c] += a[c];
        acc[4] = std::min(acc[4], a[4]);
        acc[5] = std::max(acc[5], a[5]);
    });
    for (int c = 0; c < 9; ++c) out9[c] = acc[c];
    return true;
}

libfive_interval libfive_tree_eval_r(libfive_tree t, libfive_region3 r)
{
    IntervalEvaluator e((Tree(t)));
    auto i = e.eval({r.X.lower, r.Y.lower, r.Z.lower},
                    {r.X.upper, r.Y.upper, r.Z.upper});
    return {i.lower(), i.upper()};
}

// (`vars`: the values of the tree's variables -- a shape made with var()s is not where its numbers are 0)
static bool bounds_impl(const Tree& root, const std::map<Tree::Id, float>& vars, libfive_region3 search,
                        int max_evals, float max_seconds, libfive_region3* out, int* open, float rel_tol = 1e-3f, bool refine = true)
{
    using V = Eigen::Vector3f;
    IntervalEvaluator e(root, vars);
    int evals = 0;
    const auto start = std::chrono::steady_clock::now();
    auto outOfBudget = [&]() {
        if (evals > max_evals) return true;
        // (the clock is read at every evaluation: one evaluation of the field of a sweep takes tens of milliseconds, and the 256 that went by between two readings were
        // seconds past a budget of a few milliseconds -- in the GUI's thread)
        if (max_seconds > 0)
        {
            const std::chrono::duration<float> dt = std::chrono::steady_clock::now() - start;
            if (dt.count() > max_seconds) return true;
        }
        return false;
    };

    struct Box { V lo, hi; };
    const V lo0(search.X.lower, search.Y.lower, search.Z.lower);
    const V hi0(search.X.upper, search.Y.upper, search.Z.upper);

    // Points certainly inside the shape ("witnesses"), per side the most
    // extreme one found so far
    float witness[6];
    bool have_witness = false;
    auto sample = [&](const V& p) {
        ++evals;
        if (!(e.eval(p, p).upper() <= 0)) return;
        if (!have_witness)
        {
            for (int s=0; s < 6; ++s) witness[s] = p[s / 2];
            have_witness = true;
        }
        for (int a=0; a < 3; ++a)
        {
            witness[2 * a] = std::min(witness[2 * a], p[a]);
            witness[2 * a + 1] = std::max(witness[2 * a + 1], p[a]);
        }
    };

    // For one side: best-first search over boxes that may contain interior,
    // most extreme first.  Done when the most extreme remaining box can't
    // beat the best witness by more than `tol` (or, without witnesses, when
    // that box is smaller than `tol`).  The answer is conservative.
    auto side = [&](const V& lo, const V& hi, int s, float tol, float& result) {
        const int a = s / 2;
        const bool upper = s % 2;
        auto key = [&](const Box& b) { return upper ? -b.hi[a] : b.lo[a]; };
        auto later = [&](const Box& x, const Box& y) { return key(x) > key(y); };
        std::priority_queue<Box, std::vector<Box>, decltype(later)> q(later);
        q.push({lo, hi});
        while (!q.empty())
        {
            if (outOfBudget()) return false;
            const Box b = q.top();
            q.pop();
            const float k = key(b);
            if (have_witness)
            {
                const float w = upper ? -witness[s] : witness[s];
                if (k >= w - tol)
                {
                    result = upper ? -k : k;
                    return true;
                }
            }
            ++evals;
            if (e.eval(b.lo, b.hi).lower() > 0) continue;
            const V size = b.hi - b.lo;
            int d;
            if (size.maxCoeff(&d) <= tol)
            {
                result = upper ? b.hi[a] : b.lo[a];
                return true;
            }
            sample((b.lo + b.hi) / 2);
            // Also try the middle of the box's extreme face, which moves
            // the witness towards the side being searched
            V f = (b.lo + b.hi) / 2;
            f[a] = upper ? b.hi[a] - 0.25f * size[a] : b.lo[a] + 0.25f * size[a];
            sample(f);
            // Halve along the searched axis while that keeps the box from
            // becoming a thin slab (whose intervals would be loose), else
            // along its longest side
            if (size[a] >= 0.125f * size[d]) d = a;
            const float mid = 0.5f * (b.lo[d] + b.hi[d]);
            Box c1 = b, c2 = b;
            c1.hi[d] = mid;
            c2.lo[d] = mid;
            q.push(c1);
            q.push(c2);
        }
        return false;
    };

    auto pass = [&](const V& lo, const V& hi, float tol, float result[6]) {
        ++evals;
        if (e.eval(lo, hi).lower() > 0) return false;
        for (int s=0; s < 6; ++s)
        {
            if (!side(lo, hi, s, tol, result[s])) return false;
        }
        return true;
    };

    float fine[6];
    const float tol0 = rel_tol * (hi0 - lo0).maxCoeff();
    if (!pass(lo0, hi0, tol0, fine)) return false;

    // Refine inside the box found so far, relative to the shape's own size,
    // until that stops tightening it
    float tol = tol0;
    for (int i=0; refine && i < 8; ++i)
    {
        V lo1(fine[0], fine[2], fine[4]), hi1(fine[1], fine[3], fine[5]);
        lo1 = (lo1.array() - tol).matrix().cwiseMax(lo0);
        hi1 = (hi1.array() + tol).matrix().cwiseMin(hi0);
        // (floored by float precision at the shape's coordinates)
        const float mag = std::max({1.0f, lo1.cwiseAbs().maxCoeff(), hi1.cwiseAbs().maxCoeff()});
        const float next = std::max(1e-3f * (hi1 - lo1).maxCoeff(), 1e-6f * mag);
        if (next > 0.5f * tol) break;
        float refined[6];
        if (!pass(lo1, hi1, next, refined)) break;      // keep the coarser box
        std::copy(refined, refined + 6, fine);
        tol = next;
    }

    if (out)
    {
        out->X = {fine[0], fine[1]};
        out->Y = {fine[2], fine[3]};
        out->Z = {fine[4], fine[5]};
    }
    if (open)
    {
        *open = 0;
        for (int s=0; s < 6; ++s)
        {
            const int a = s / 2;
            const float edge = (s % 2) ? hi0[a] : lo0[a];
            if (std::abs(fine[s] - edge) <= tol0)
            {
                *open |= 1 << s;
            }
        }
    }
    return true;
}

bool libfive_tree_bounds(libfive_tree t, libfive_region3 search, int max_evals,
                         float max_seconds, libfive_region3* out, int* open)
{
    return bounds_impl(Tree(t), {}, search, max_evals, max_seconds, out, open);
}

bool libfive_tree_bounds_vars(libfive_tree t, libfive_region3 search, int max_evals, float max_seconds,
                              libfive_region3* out, int* open,
                              const libfive_tree* vars, const float* values, int count)
{
    std::map<Tree::Id, float> m;
    for (int i = 0; i < count; ++i) m[static_cast<Tree::Id>(vars[i])] = values[i];
    return bounds_impl(Tree(t), m, search, max_evals, max_seconds, out, open);
}

bool libfive_tree_bounds_vars_coarse(libfive_tree t, libfive_region3 search, int max_evals, float max_seconds, float rel_tol,
                                     libfive_region3* out, int* open,
                                     const libfive_tree* vars, const float* values, int count)
{
    std::map<Tree::Id, float> m;
    for (int i = 0; i < count; ++i) m[static_cast<Tree::Id>(vars[i])] = values[i];
    return bounds_impl(Tree(t), m, search, max_evals, max_seconds, out, open, rel_tol, false);
}

float libfive_tree_interval_lower(libfive_tree t, libfive_region3 box,
                                  const libfive_tree* vars, const float* values, int count)
{
    std::map<Tree::Id, float> m;
    for (int i = 0; i < count; ++i) m[static_cast<Tree::Id>(vars[i])] = values[i];
    IntervalEvaluator e(Tree(t), m);
    return e.eval({box.X.lower, box.Y.lower, box.Z.lower},
                  {box.X.upper, box.Y.upper, box.Z.upper}).lower();
}

libfive_tree libfive_tree_copy(libfive_tree t)
{
    return Tree(t).release();
}

void libfive_run_begin(int steps)
{
    libfive::run_progress::beginScript(steps);
}

void libfive_run_step(int index, const char* label)
{
    libfive::run_progress::setStep(index, label ? label : "");
}

void libfive_run_step_line(int line)
{
    libfive::run_progress::setStepLine(line);
}

void libfive_run_end(void)
{
    libfive::run_progress::endScript();
}

void libfive_run_task_begin(const char* name)
{
    libfive::run_progress::pushTask(name ? name : "");
}

void libfive_run_task_set(double fraction, const char* detail)
{
    libfive::run_progress::setTask(fraction, detail ? detail : "");
}

void libfive_run_task_span(double a, double b)
{
    libfive::run_progress::spanTask(a, b);
}

void libfive_run_task_end(void)
{
    libfive::run_progress::popTask();
}

void libfive_tree_eval_points_vars(libfive_tree t, const float* xyz, int n, float* out,
                                   const libfive_tree* vars, const float* values, int count)
{
    if (!t || n <= 0) return;
    const Tree tree(t);
    std::map<Tree::Id, float> m;
    for (int i = 0; i < count; ++i) m[static_cast<Tree::Id>(vars[i])] = values[i];
    parallelChunks(size_t(n), 4096, [&](size_t first, size_t last) {
        ArrayEvaluator e(tree, m);
        const size_t N = ArrayEvaluator::N;
        for (size_t start = first; start < last; start += N)
        {
            const size_t count_ = std::min(N, last - start);
            for (size_t k = 0; k < count_; ++k)
            {
                const float* p = xyz + 3 * (start + k);
                e.set(Eigen::Vector3f(p[0], p[1], p[2]), k);
            }
            const auto vs = e.values(count_);
            for (size_t k = 0; k < count_; ++k) out[start + k] = vs(k);
        }
    });
}

void libfive_tree_eval_points(libfive_tree t, const float* xyz, int n, float* out)
{
    if (!t || n <= 0) return;
    const Tree tree(t);
    parallelChunks(size_t(n), 4096, [&](size_t first, size_t last) {
        ArrayEvaluator e(tree);
        const size_t N = ArrayEvaluator::N;
        for (size_t start = first; start < last; start += N)
        {
            const size_t count = std::min(N, last - start);
            for (size_t k = 0; k < count; ++k)
            {
                const float* p = xyz + 3 * (start + k);
                e.set(Eigen::Vector3f(p[0], p[1], p[2]), k);
            }
            const auto vs = e.values(count);
            for (size_t k = 0; k < count; ++k) out[start + k] = vs(k);
        }
    });
}

namespace {
std::string surface_error;     // (libfive_surface_last_error)
}   // anonymous namespace

const char* libfive_surface_last_error(void)
{
    return surface_error.c_str();
}

libfive_surface_patch* libfive_surface_select(libfive_tree body, const libfive_tree* vars, const float* values, int var_count,
                                              const double* lo3, const double* hi3, const double* seed3,
                                              double angle_degrees, int mode, double max_radius, double spacing)
{
    surface_error.clear();
    if (!body || !lo3 || !hi3 || !seed3)
    {
        surface_error = "no body, or no seed";
        return nullptr;
    }
    std::map<Tree::Id, float> m;
    for (int i = 0; i < var_count; ++i) m[static_cast<Tree::Id>(vars[i])] = values[i];
    libfive::surface::SurfacePatch patch;
    std::string error;
    if (!libfive::surface::selectSurfacePatch(Tree(body), m, Eigen::Vector3d(seed3[0], seed3[1], seed3[2]), angle_degrees, mode,
                                              max_radius, spacing, Eigen::Vector3d(lo3[0], lo3[1], lo3[2]),
                                              Eigen::Vector3d(hi3[0], hi3[1], hi3[2]), patch, error))
    {
        surface_error = error;
        return nullptr;
    }
    auto* out = new libfive_surface_patch;
    out->count = uint32_t(patch.points.size());
    out->points = new float[3 * patch.points.size()];
    out->normals = new float[3 * patch.points.size()];
    for (size_t i = 0; i < patch.points.size(); ++i)
        for (int k = 0; k < 3; ++k)
        {
            out->points[3 * i + size_t(k)] = float(patch.points[i][k]);
            out->normals[3 * i + size_t(k)] = float(patch.normals[i][k]);
        }
    for (int k = 0; k < 3; ++k) out->seed_point[k] = patch.seedPoint[k];
    out->seed_distance = patch.seedDistance;
    out->spacing = patch.spacing;
    out->stopped = patch.stopped ? 1 : 0;
    return out;
}

void libfive_surface_patch_delete(libfive_surface_patch* p)
{
    if (!p) return;
    delete[] p->points;
    delete[] p->normals;
    delete p;
}

libfive_tree libfive_points_surface(const float* xyz, const float* normals, uint32_t count, double sigma)
{
    surface_error.clear();
    if (!xyz || !normals || count == 0 || !(sigma > 0))
    {
        surface_error = "no points, or no width for the surface they make";
        return nullptr;
    }
    std::vector<Eigen::Vector3d> pts(count), nrm(count);
    for (uint32_t i = 0; i < count; ++i)
    {
        pts[i] = Eigen::Vector3d(xyz[3 * i], xyz[3 * i + 1], xyz[3 * i + 2]);
        nrm[i] = Eigen::Vector3d(normals[3 * i], normals[3 * i + 1], normals[3 * i + 2]);
    }
    return libfive::surface::orientedPointsTree(pts, nrm, sigma).release();
}

libfive_tree libfive_points_distance(const float* xyz, uint32_t count)
{
    surface_error.clear();
    if (!xyz || !count)
    {
        surface_error = "there are no points";
        return nullptr;
    }
    std::vector<Eigen::Vector3d> pts;
    pts.reserve(count);
    for (uint32_t i = 0; i < count; ++i) pts.emplace_back(xyz[3 * i], xyz[3 * i + 1], xyz[3 * i + 2]);
    return libfive::surface::pointsDistanceTree(pts).release();
}

static std::vector<libfive::pointshapes::Control> pointshapeControls(const double* pos, const int* smooth, const int* turned, const double* rotate, const double* scale,
                                                                       const double* radius, const double* normal, int n)
{
    std::vector<libfive::pointshapes::Control> controls(size_t(std::max(0, n)));
    for (int i = 0; i < n; ++i)
    {
        auto& c = controls[size_t(i)];
        c.pos = Eigen::Vector3d(pos[3 * i], pos[3 * i + 1], pos[3 * i + 2]);
        c.smooth = smooth ? smooth[i] : -1;
        c.turned = turned && turned[i];
        if (rotate) c.rotate = Eigen::Vector3d(rotate[3 * i], rotate[3 * i + 1], rotate[3 * i + 2]);
        if (scale) c.scale = scale[i];
        if (radius) c.radius = radius[i];
        if (normal)
        {
            c.planar = true;
            c.normal = Eigen::Vector3d(normal[0], normal[1], normal[2]);
        }
    }
    return controls;
}

int libfive_pointshape_polyline(const double* pos, const int* smooth, const int* turned, const double* rotate, const double* scale, const double* radius,
                                const double* normal, int n, int smooth_default, int closed, int pieces, int arc_pieces,
                                double* out_vertices, int* out_owner, double* out_t, int capacity)
{
    const auto controls = pointshapeControls(pos, smooth, turned, rotate, scale, radius, normal, n);
    std::vector<std::pair<int, double>> owners;
    const auto v = libfive::pointshapes::polyline(controls, smooth_default != 0, closed != 0, pieces, &owners, arc_pieces);
    if (int(v.size()) > capacity) return int(v.size());
    for (size_t i = 0; i < v.size(); ++i)
    {
        out_vertices[3 * i] = v[i].x();
        out_vertices[3 * i + 1] = v[i].y();
        out_vertices[3 * i + 2] = v[i].z();
        if (out_owner) out_owner[i] = owners[i].first;
        if (out_t) out_t[i] = owners[i].second;
    }
    return int(v.size());
}

int libfive_pointshape_fillets(const double* pos, const int* smooth, const double* radius, const double* normal, int n, int smooth_default, int closed,
                               double* out, int capacity)
{
    const auto controls = pointshapeControls(pos, smooth, nullptr, nullptr, nullptr, radius, normal, n);
    const auto arcs = libfive::pointshapes::fillets(controls, smooth_default != 0, closed != 0);
    if (int(arcs.size()) > capacity) return int(arcs.size());
    for (size_t i = 0; i < arcs.size(); ++i)
    {
        const auto& f = arcs[i];
        double* o = out + 11 * i;
        o[0] = double(f.control);
        for (int k = 0; k < 3; ++k)
        {
            o[1 + k] = f.a[k];
            o[4 + k] = f.b[k];
            o[7 + k] = f.centre[k];
        }
        o[10] = f.radius;
    }
    return int(arcs.size());
}

bool libfive_pointshape_plane(const double* pos, int n, double* frame)
{
    std::vector<Eigen::Vector3d> p;
    for (int i = 0; i < n; ++i) p.emplace_back(pos[3 * i], pos[3 * i + 1], pos[3 * i + 2]);
    return libfive::pointshapes::planeOf(p, frame);
}

libfive_tree libfive_field_gradient(libfive_tree t, int mode)
{
    return libfive::fields::gradientField(Tree(t), mode).release();
}

libfive_tree libfive_field_points(const float* xyz, const float* values, int n, int k,
                                  float power)
{
    std::vector<Eigen::Vector3d> pts;
    std::vector<double> vals;
    for (int i = 0; i < n; ++i)
    {
        pts.emplace_back(xyz[3 * i], xyz[3 * i + 1], xyz[3 * i + 2]);
        vals.push_back(values[i]);
    }
    return libfive::fields::pointCloudField(pts, vals, k, power).release();
}

libfive_tree libfive_field_noise(float scale, int octaves, unsigned seed, float gain,
                                 float lacunarity)
{
    return libfive::fields::noiseField(scale, octaves, seed, gain, lacunarity).release();
}

libfive_tree libfive_field_cellular(float scale, unsigned seed, int mode, float jitter)
{
    return libfive::fields::cellularField(scale, seed, mode, jitter).release();
}

libfive_tree libfive_field_curvature(libfive_tree t, float h)
{
    return libfive::fields::curvatureField(Tree(t), h).release();
}

libfive_vec3 libfive_tree_eval_d(libfive_tree t, libfive_vec3 p)
{
    DerivArrayEvaluator e((Tree(t)));
    auto v = e.deriv({p.x, p.y, p.z});
    return {v.x(), v.y(), v.z()};
}

char* libfive_tree_print(libfive_tree t)
{
    std::stringstream ss;
    ss << Tree(t);
    const auto str = ss.str();

    auto out = static_cast<char*>(malloc(str.size() + 1 * sizeof(char)));
    memcpy(out, str.c_str(), str.size() + 1);
    return out;
}

char* libfive_tree_content_key(libfive_tree t)
{
    const auto str = treeContentKey(Tree(t));

    auto out = static_cast<char*>(malloc(str.size() + 1 * sizeof(char)));
    memcpy(out, str.c_str(), str.size() + 1);
    return out;
}

char* libfive_tree_persistent_key(libfive_tree t, const libfive_tree* vars, const float* values, int count)
{
    std::map<Tree::Id, float> m;
    for (int i = 0; i < count; ++i) m[static_cast<Tree::Id>(vars[i])] = values[i];
    // (of the tree as it was built: the optimizer's output differs from run to run in the order of operands)
    const auto str = treePersistentKey(Tree(t), m);
    if (str.empty()) return nullptr;
    auto out = static_cast<char*>(malloc(str.size() + 1 * sizeof(char)));
    memcpy(out, str.c_str(), str.size() + 1);
    return out;
}

int libfive_tree_expose_count(libfive_tree t)
{
    return int(exposableConstants(Tree(t)).size());
}

void libfive_tree_expose_values(libfive_tree t, float* out)
{
    const auto values = exposableConstants(Tree(t));
    for (size_t i = 0; i < values.size(); ++i) out[i] = values[i];
}

libfive_tree libfive_tree_expose(libfive_tree t, libfive_tree* with, int count)
{
    std::vector<Tree> trees;
    for (int i = 0; i < count; ++i) trees.push_back(Tree(with[i]));
    const Tree out = exposeConstants(Tree(t), trees);
    if (out == Tree::invalid()) return nullptr;
    return Tree(out).release();
}

void libfive_free_str(char* ptr) {
    free(ptr);
}

////////////////////////////////////////////////////////////////////////////////

libfive_contours* libfive_tree_render_slice(libfive_tree tree,
        libfive_region2 R, float z, float res)
{
    Region<2> region({R.X.lower, R.Y.lower}, {R.X.upper, R.Y.upper},
            Region<2>::Perp(z));
    BRepSettings settings;
    settings.min_feature = 1/res;
    auto cs = Contours::render(Tree(tree), region, settings);

    auto out = new libfive_contours;
    out->count = cs->contours.size();
    out->cs = new libfive_contour[out->count];

    size_t i=0;
    for (auto& c : cs->contours)
    {
        out->cs[i].count = c.size();
        out->cs[i].pts = new libfive_vec2[c.size()];

        size_t j=0;
        for (auto& pt : c)
        {
            out->cs[i].pts[j++] = {pt.x(), pt.y()};
        }
        i++;
    }

    return out;
}

libfive_contours3* libfive_tree_render_slice3(libfive_tree tree,
                                              libfive_region2 R, float z, float res)
{
    Region<2> region({R.X.lower, R.Y.lower}, {R.X.upper, R.Y.upper},
            Region<2>::Perp(z));
    BRepSettings settings;
    settings.min_feature = 1/res;
    auto cs = Contours::render(Tree(tree), region, settings);

    auto out = new libfive_contours3;
    out->count = cs->contours.size();
    out->cs = new libfive_contour3[out->count];

    size_t i=0;
    for (auto& c : cs->contours)
    {
        out->cs[i].count = c.size();
        out->cs[i].pts = new libfive_vec3[c.size()];

        size_t j=0;
        for (auto& pt : c)
        {
          // each 2D contour point is converted to a 3D point (with
          // this function's z argument as the Z coordinate)
          out->cs[i].pts[j++] = {pt.x(), pt.y(), z};
        }
        i++;
    }

    return out;
}

void libfive_tree_save_slice(libfive_tree tree, libfive_region2 R, float z, float res,
                        const char* f)
{
    Region<2> region({R.X.lower, R.Y.lower}, {R.X.upper, R.Y.upper},
            Region<2>::Perp(z));
    BRepSettings settings;
    settings.min_feature = 1/res;
    auto cs = Contours::render(Tree(tree), region, settings);
    cs->saveSVG(f);
}

libfive_mesh* libfive_tree_render_mesh_(libfive_tree tree, libfive_region3 R,
                                        const BRepSettings& settings,
                                        const std::map<Tree::Id, float>* vars = nullptr)
{
    Region<3> region({R.X.lower, R.Y.lower, R.Z.lower},
                     {R.X.upper, R.Y.upper, R.Z.upper});
    std::unique_ptr<Mesh> ms;
    if (vars && !vars->empty())
    {
        // (one evaluator for each worker, with the numbers of the variables)
        const auto t = Tree(tree).optimized();
        std::vector<Evaluator, Eigen::aligned_allocator<Evaluator>> es;
        es.reserve(settings.workers);
        for (unsigned i = 0; i < settings.workers; ++i)
        {
            es.emplace_back(Evaluator(t, *vars));
        }
        ms = Mesh::render(es.data(), region, settings);
    }
    else
    {
        ms = Mesh::render(Tree(tree), region, settings);
    }
    if (ms.get() == nullptr)
    {
        fprintf(stderr, "libfive_tree_render_mesh: got empty mesh\n");
        return nullptr;
    }

    auto out = new libfive_mesh;
    out->verts = new libfive_vec3[ms->verts.size()];
    out->vert_count = ms->verts.size();
    out->tris = new libfive_tri[ms->branes.size()];
    out->tri_count = ms->branes.size();

    size_t i;

    i=0;
    for (auto& v : ms->verts)
    {
        out->verts[i++] = {v.x(), v.y(), v.z()};
    }

    i=0;
    for (auto& t : ms->branes)
    {
        out->tris[i++] = {(uint32_t)t.x(), (uint32_t)t.y(), (uint32_t)t.z()};
    }

    return out;
}

libfive_mesh* libfive_tree_render_mesh(libfive_tree tree, libfive_region3 R, float res) {
  BRepSettings settings;
  settings.min_feature = 1/res;
  return libfive_tree_render_mesh_(tree, R, settings);
}

libfive_mesh* libfive_tree_render_mesh_vars(libfive_tree tree, libfive_region3 R, float res,
                                            const libfive_tree* vars, const float* values, int count) {
  BRepSettings settings;
  settings.min_feature = 1/res;
  std::map<Tree::Id, float> m;
  for (int i = 0; i < count; ++i) m[static_cast<Tree::Id>(vars[i])] = values[i];
  return libfive_tree_render_mesh_(tree, R, settings, &m);
}

libfive_mesh* libfive_tree_render_mesh_st(libfive_tree tree, libfive_region3 R, float res) {
  BRepSettings settings;
  settings.min_feature = 1/res;
  settings.workers = 1;
  return libfive_tree_render_mesh_(tree, R, settings);
}

libfive_mesh* libfive_tree_render_mesh_algo(libfive_tree tree, libfive_region3 R, float res,
                                             int algo, double max_err, int workers) {
  BRepSettings settings;
  settings.min_feature = 1/res;
  settings.workers = workers;
  settings.max_err = max_err;
  settings.alg = static_cast<BRepAlgorithm>(algo);
  return libfive_tree_render_mesh_(tree, R, settings);
}
 
libfive_mesh_coords* libfive_tree_render_mesh_coords(libfive_tree tree,
                                                     libfive_region3 R,
                                                     float res)
{
    Region<3> region({R.X.lower, R.Y.lower, R.Z.lower},
                     {R.X.upper, R.Y.upper, R.Z.upper});
    BRepSettings settings;
    settings.min_feature = 1/res;
    auto ms = Mesh::render(Tree(tree), region, settings);
    if (ms.get() == nullptr)
    {
        fprintf(stderr, "libfive_tree_render_mesh_coords: got empty mesh\n");
        return nullptr;
    }

    auto out = new libfive_mesh_coords;
    out->verts = new libfive_vec3[ms->verts.size()];
    out->vert_count = ms->verts.size();
    // need 4 times the count of triangles for coordinate indices
    // (3 vertices separated by -1 for each triangle)
    out->coord_indices = new int32_t[4 * ms->branes.size()];
    out->coord_index_count = 4 * ms->branes.size();

    size_t i;

    i=0;
    for (auto& v : ms->verts)
    {
        out->verts[i++] = {v.x(), v.y(), v.z()};
    }

    i=0;
    for (auto& t : ms->branes)
    {
      out->coord_indices[i++] = (int32_t)t.x();
      out->coord_indices[i++] = (int32_t)t.y();
      out->coord_indices[i++] = (int32_t)t.z();
      out->coord_indices[i++] = -1;
    }

    return out;
}

bool libfive_tree_save_mesh(libfive_tree tree, libfive_region3 R, float res, const char* f)
{
    Region<3> region({R.X.lower, R.Y.lower, R.Z.lower},
                     {R.X.upper, R.Y.upper, R.Z.upper});

    BRepSettings settings;
    settings.min_feature = 1/res;
    auto ms = Mesh::render(Tree(tree), region, settings);
    return ms->saveSTL(f);
}

bool libfive_evaluator_save_mesh(libfive_evaluator evaluator, libfive_region3 R, const char *f)
{
    Region<3> region({R.X.lower, R.Y.lower, R.Z.lower},
                     {R.X.upper, R.Y.upper, R.Z.upper});

    BRepSettings settings; // TODO: pass it in as an argument
    settings.workers = 1;  // NOTE: temporary limitation
    auto ms = Mesh::render(evaluator, region, settings);
    return ms->saveSTL(f);
}

bool libfive_tree_save_meshes(
        libfive_tree trees[], libfive_region3 R,
        float res, float quality, const char* f)
{
    Region<3> region({R.X.lower, R.Y.lower, R.Z.lower},
                     {R.X.upper, R.Y.upper, R.Z.upper});

    BRepSettings settings;
    settings.min_feature = 1/res;
    settings.max_err = pow(10, -quality);
    std::list<const libfive::Mesh*> meshes;
    for (unsigned i=0; trees[i] != nullptr; ++i){
        auto ms = Mesh::render(Tree(trees[i]), region, settings);
        meshes.push_back(ms.release());
    }

    const bool out = Mesh::saveSTL(f, meshes);
    for (auto& m : meshes) {
        delete m;
    }
    return out;
}

libfive_pixels* libfive_tree_render_pixels(libfive_tree tree, libfive_region2 R,
                                 float z, float res)
{
    Voxels v({R.X.lower, R.Y.lower, z},
             {R.X.upper, R.Y.upper, z}, res);
    std::atomic_bool abort(false);
    auto h = Heightmap::render(Tree(tree), v, abort);

    libfive_pixels* out = new libfive_pixels;
    out->width = h->depth.cols();
    out->height = h->depth.rows();
    out->pixels = new bool[out->width * out->height];

    size_t i=0;
    for (unsigned y=0; y < out->height; ++y)
    {
        for (unsigned x=0; x < out->width; ++x)
        {
            out->pixels[i++] = !std::isinf(h->depth(y, x));
        }
    }

    return out;
}

libfive_evaluator libfive_tree_evaluator(libfive_tree tree, libfive_vars vars)
{
    std::map<libfive::Tree::Id, float> mapOfVars;
    for (unsigned i = 0; i < vars.size; ++i)
    {
        auto treeId = static_cast<libfive::Tree::Id>(vars.vars[i]);
        mapOfVars.insert(std::make_pair(treeId, vars.values[i]));
    }
    // TODO: For more than one worker
    return new Evaluator(Tree(tree), mapOfVars);
}

bool libfive_evaluator_update_vars(libfive_evaluator eval_tree, libfive_vars vars)
{
    std::map<libfive::Tree::Id, float> mapOfVars;
    for (unsigned i = 0; i < vars.size; ++i)
    {
        auto treeId = static_cast<libfive::Tree::Id>(vars.vars[i]);
        mapOfVars.insert(std::make_pair(treeId, vars.values[i]));
    }

    return eval_tree->updateVars(mapOfVars);
}

void libfive_evaluator_delete(libfive_evaluator ptr)
{
    // TODO: For more than one worker
    std::cout << "libfive_evaluator_delete";
    delete ptr;
}

////////////////////////////////////////////////////////////////////////////////

// These variables are injected into the compiler as definitions
const char* libfive_git_version(void)
{
    return GIT_TAG;
}

const char* libfive_git_revision(void)
{
    return GIT_REV;
}

const char* libfive_git_branch(void)
{
    return GIT_BRANCH;
}

////////////////////////////////////////////////////////////////////////////////
// Debug: on an access violation anywhere in the process, print the faulting
// thread's native stack (function, file:line where debug info exists) to
// stderr.  For tracking down crashes in the multi-threaded mesher.
#ifdef _WIN32
#define NOMINMAX
#include <atomic>
#include <windows.h>
#include <dbghelp.h>
#pragma comment(lib, "dbghelp.lib")

static LONG WINAPI libfiveCrashHandler(EXCEPTION_POINTERS* info)
{
    if (info->ExceptionRecord->ExceptionCode != EXCEPTION_ACCESS_VIOLATION) {
        return EXCEPTION_CONTINUE_SEARCH;
    }
    static std::atomic<bool> once{false};
    if (once.exchange(true)) return EXCEPTION_CONTINUE_SEARCH;
    HANDLE proc = GetCurrentProcess();
    SymSetOptions(SYMOPT_LOAD_LINES | SYMOPT_UNDNAME | SYMOPT_DEFERRED_LOADS);
    SymInitialize(proc, nullptr, TRUE);
    CONTEXT ctx = *info->ContextRecord;
    STACKFRAME64 frame = {};
    frame.AddrPC.Offset = ctx.Rip;    frame.AddrPC.Mode = AddrModeFlat;
    frame.AddrFrame.Offset = ctx.Rbp; frame.AddrFrame.Mode = AddrModeFlat;
    frame.AddrStack.Offset = ctx.Rsp; frame.AddrStack.Mode = AddrModeFlat;
    fprintf(stderr, "[crash] access violation at %p (%s address %p)\n",
            info->ExceptionRecord->ExceptionAddress,
            info->ExceptionRecord->ExceptionInformation[0] ? "writing" : "reading",
            (void*)info->ExceptionRecord->ExceptionInformation[1]);
    for (int k = 0; k < 40; k++) {
        if (!StackWalk64(IMAGE_FILE_MACHINE_AMD64, proc, GetCurrentThread(), &frame, &ctx,
                         nullptr, SymFunctionTableAccess64, SymGetModuleBase64, nullptr)) break;
        char buf[sizeof(SYMBOL_INFO) + 512];
        auto sym = reinterpret_cast<SYMBOL_INFO*>(buf);
        sym->SizeOfStruct = sizeof(SYMBOL_INFO);
        sym->MaxNameLen = 511;
        DWORD64 disp = 0;
        IMAGEHLP_LINE64 line = {};
        line.SizeOfStruct = sizeof(line);
        DWORD ldisp = 0;
        const bool haveSym = SymFromAddr(proc, frame.AddrPC.Offset, &disp, sym);
        const bool haveLine = SymGetLineFromAddr64(proc, frame.AddrPC.Offset, &ldisp, &line);
        fprintf(stderr, "[crash]   #%d %s  %s:%lu\n", k, haveSym ? sym->Name : "?",
                haveLine ? line.FileName : "?", haveLine ? line.LineNumber : 0ul);
    }
    // The code addresses found on the stack as they are, each as module + offset (what a map file of the library names): a jump to a bad address
    // (a call through a freed object) leaves nothing that the walk above can follow
    const DWORD64 sp = info->ContextRecord->Rsp;
    HMODULE ripModule = nullptr;
    GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       reinterpret_cast<LPCSTR>(info->ContextRecord->Rip), &ripModule);
    fprintf(stderr, "[crash] rip %p (%s)\n", reinterpret_cast<void*>(info->ContextRecord->Rip), ripModule ? "in a module" : "in no module");
    int shown = 0;
    for (int k = 0; k < 400 && shown < 40; k++) {
        DWORD64 value = 0;
        if (!ReadProcessMemory(proc, reinterpret_cast<const void*>(sp + 8 * DWORD64(k)), &value, sizeof(value), nullptr)) break;
        MEMORY_BASIC_INFORMATION mbi;
        if (!VirtualQuery(reinterpret_cast<const void*>(value), &mbi, sizeof(mbi))) continue;
        if (!(mbi.Protect & (PAGE_EXECUTE | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY))) continue;
        HMODULE module = nullptr;
        if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                reinterpret_cast<LPCSTR>(value), &module)) continue;
        char name[MAX_PATH] = {};
        GetModuleFileNameA(module, name, MAX_PATH);
        const char* base = strrchr(name, '\\');
        fprintf(stderr, "[crash]   stack+%d: %s+0x%llx\n", 8 * k, base ? base + 1 : name,
                static_cast<unsigned long long>(value - reinterpret_cast<DWORD64>(module)));
        ++shown;
    }
    fflush(stderr);
    return EXCEPTION_CONTINUE_SEARCH;
}

void libfive_debug_crash_handler(void)
{
    AddVectoredExceptionHandler(1, libfiveCrashHandler);
}
#else
void libfive_debug_crash_handler(void) {}
#endif
