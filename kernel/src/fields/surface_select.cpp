/*
libfive: a CAD kernel for modeling with implicit functions

Selecting a patch of a surface (a flood fill over the surface of a field, from its value and gradient alone) and the fields made of
points; see surface_select.hpp.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <map>
#include <memory>
#include <mutex>
#include <numeric>
#include <functional>
#include <queue>
#include <random>
#include <set>
#include <thread>
#include <tuple>
#include <unordered_map>
#include <unordered_set>

#include "libfive/eval/eval_deriv_array.hpp"
#include "libfive/fields/surface_select.hpp"
#include "libfive/oracle/oracle_clause.hpp"
#include "libfive/oracle/oracle_storage.hpp"

namespace libfive {
namespace surface {

using V3 = Eigen::Vector3d;

namespace {

////////////////////////////////////////////////////////////////////////////////
// The field and its gradient

class Field
{
public:
    // The field is evaluated by several threads, each with an evaluator of its own (a Deck holds its oracles: one Deck per thread).  A batch of points is cut into runs of
    // ArrayEvaluator::N points, the way a single evaluator would take it, and the threads take the runs one after another, so that every point gets exactly the value and the
    // gradient it would get from one thread alone.  FIELDEV_SC_THREADS=n sets the number of threads (1: one thread)
    Field(const Tree& t, const std::map<Tree::Id, float>& vars) : tree_(t.optimized()), vars_(vars), e(tree_, vars)
    {
        unsigned n = std::thread::hardware_concurrency();
        if (const char* env = std::getenv("FIELDEV_SC_THREADS")) n = unsigned(std::max(1, std::atoi(env)));
        threads_ = int(std::min(16u, std::max(1u, n)));
    }
    Field(const Field&) = delete;
    Field& operator=(const Field&) = delete;
    ~Field() { stopWorkers(); }

    // how many points the field has been evaluated at so far (for the developer)
    unsigned long long evaluated() const { return evaluated_.load(); }

    void eval(const std::vector<V3>& pts, std::vector<double>& f, std::vector<V3>& g)
    {
        evalRaw(pts, f, g);
        // Where two parts of the field are equal (a point exactly on a flat face of a box is where the distance to it, min(0,
        // the largest of three numbers), has its two parts both zero), the gradient is that of whichever part the evaluator
        // meets first -- and that is not the same in every run, so that the points on a face had a gradient of zero in one and
        // not in the next.  A point that has lost its gradient gets it from differences of the field round it.
        std::vector<size_t> lost;
        for (size_t k = 0; k < pts.size(); ++k)
            if (std::isfinite(f[k]) && !(g[k].norm() > 1e-9)) lost.push_back(k);
        if (lost.empty()) return;
        const double h = 0.01;
        std::vector<V3> around;
        around.reserve(6 * lost.size());
        for (size_t k : lost)
            for (int axis = 0; axis < 3; ++axis)
            {
                V3 d = V3::Zero();
                d[axis] = h;
                around.push_back(pts[k] + d);
                around.push_back(pts[k] - d);
            }
        std::vector<double> fa;
        std::vector<V3> ga;
        evalRaw(around, fa, ga);
        for (size_t j = 0; j < lost.size(); ++j)
        {
            const double* v = &fa[6 * j];
            if (!std::isfinite(v[0] + v[1] + v[2] + v[3] + v[4] + v[5])) continue;
            g[lost[j]] = V3((v[0] - v[1]) / (2 * h), (v[2] - v[3]) / (2 * h), (v[4] - v[5]) / (2 * h));
        }
    }

private:
    struct Job
    {
        const V3* pts = nullptr;
        double* f = nullptr;
        V3* g = nullptr;
        size_t n = 0, chunks = 0;
        std::atomic<size_t> next{0}, done{0};
    };

    static void runChunk(DerivArrayEvaluator& ev, const Job& job, size_t c)
    {
        const size_t N = ArrayEvaluator::N;
        const size_t s = c * N;
        const size_t cnt = std::min(N, job.n - s);
        for (size_t k = 0; k < cnt; ++k) ev.set(job.pts[s + k].cast<float>(), k);
        const auto d = ev.derivs(cnt);
        for (size_t k = 0; k < cnt; ++k)
        {
            job.g[s + k] = V3(double(d(0, k)), double(d(1, k)), double(d(2, k)));
            job.f[s + k] = double(d(3, k));
        }
    }

    void work(DerivArrayEvaluator& ev, Job& job)
    {
        for (;;)
        {
            const size_t c = job.next.fetch_add(1);
            if (c >= job.chunks) return;
            runChunk(ev, job, c);
            if (job.done.fetch_add(1) + 1 == job.chunks)
            {
                std::lock_guard<std::mutex> lock(m_);
                cvDone_.notify_all();
            }
        }
    }

    void startWorkers()
    {
        if (started_) return;
        started_ = true;
        // (the evaluators are made one after another here, the way the renderer makes its own: the tree is already optimized)
        for (int i = 1; i < threads_; ++i)
        {
            try
            {
                extra_.push_back(std::make_unique<DerivArrayEvaluator>(tree_, vars_));
            }
            catch (...)
            {
                break;
            }
        }
        for (auto& ev : extra_)
        {
            DerivArrayEvaluator* p = ev.get();
            workers_.emplace_back([this, p] {
                uint64_t seen = 0;
                for (;;)
                {
                    std::shared_ptr<Job> job;
                    {
                        std::unique_lock<std::mutex> lock(m_);
                        cvWork_.wait(lock, [&] { return quit_ || generation_ != seen; });
                        if (quit_) return;
                        seen = generation_;
                        job = job_;
                    }
                    if (job) work(*p, *job);
                }
            });
        }
    }

    void stopWorkers()
    {
        {
            std::lock_guard<std::mutex> lock(m_);
            quit_ = true;
        }
        cvWork_.notify_all();
        for (auto& w : workers_) w.join();
        workers_.clear();
    }

    void evalRaw(const std::vector<V3>& pts, std::vector<double>& f, std::vector<V3>& g)
    {
        f.resize(pts.size());
        g.resize(pts.size());
        evaluated_ += pts.size();
        const size_t N = ArrayEvaluator::N;
        const size_t chunks = (pts.size() + N - 1) / N;
        auto job = std::make_shared<Job>();
        job->pts = pts.data();
        job->f = f.data();
        job->g = g.data();
        job->n = pts.size();
        job->chunks = chunks;
        if (threads_ <= 1 || chunks < 3)
        {
            for (size_t c = 0; c < chunks; ++c) runChunk(e, *job, c);
            return;
        }
        startWorkers();
        {
            std::lock_guard<std::mutex> lock(m_);
            job_ = job;
            ++generation_;
        }
        cvWork_.notify_all();
        work(e, *job);
        std::unique_lock<std::mutex> lock(m_);
        cvDone_.wait(lock, [&] { return job->done.load() == job->chunks; });
    }

    Tree tree_;
    std::map<Tree::Id, float> vars_;
    DerivArrayEvaluator e;
    int threads_ = 1;
    bool started_ = false;
    std::vector<std::unique_ptr<DerivArrayEvaluator>> extra_;
    std::vector<std::thread> workers_;
    std::mutex m_;
    std::condition_variable cvWork_, cvDone_;
    std::shared_ptr<Job> job_;
    uint64_t generation_ = 0;
    bool quit_ = false;
    std::atomic<unsigned long long> evaluated_{0};
};

////////////////////////////////////////////////////////////////////////////////
// Onto the surface

// Points moved along the gradient to where the field is zero; ok[i] when they got there, n[i] the normal there
void projectToSurface(Field& F, std::vector<V3>& p, std::vector<V3>& n, std::vector<char>& ok, double maxStep, double tol)
{
    ok.assign(p.size(), 0);
    n.assign(p.size(), V3::Zero());
    std::vector<size_t> active(p.size());
    std::iota(active.begin(), active.end(), size_t(0));
    std::vector<V3> pts, g;
    std::vector<double> f;
    for (int it = 0; it < 14 && !active.empty(); ++it)
    {
        pts.clear();
        for (size_t a : active) pts.push_back(p[a]);
        F.eval(pts, f, g);
        std::vector<size_t> next;
        for (size_t k = 0; k < active.size(); ++k)
        {
            const size_t a = active[k];
            const double gn = g[k].norm();
            if (!(gn > 1e-12) || !std::isfinite(f[k])) continue;
            n[a] = g[k] / gn;
            const double dist = f[k] / gn;
            if (std::abs(dist) < tol)
            {
                ok[a] = 1;
                continue;
            }
            p[a] -= n[a] * std::copysign(std::min(std::abs(dist), maxStep), dist);
            next.push_back(a);
        }
        active.swap(next);
    }
}

}   // namespace

////////////////////////////////////////////////////////////////////////////////
// Selecting a patch of a surface: a flood fill over the surface of a field, from the field alone

namespace {

// The samples of a walk, in a hash of cubes: is there one within r of a point?
class SampleHash
{
public:
    SampleHash(const std::vector<V3>& samples, double cell) : pts_(samples), cell_(cell) {}

    void add(size_t index)
    {
        grid_[key(cellOf(pts_[index]))].push_back(uint32_t(index));
    }

    bool near(const V3& p, double r) const
    {
        const std::array<long, 3> c = cellOf(p);
        const double r2 = r * r;
        for (long dx = -1; dx <= 1; ++dx)
            for (long dy = -1; dy <= 1; ++dy)
                for (long dz = -1; dz <= 1; ++dz)
                {
                    const auto it = grid_.find(key({c[0] + dx, c[1] + dy, c[2] + dz}));
                    if (it == grid_.end()) continue;
                    for (uint32_t i : it->second)
                        if ((pts_[i] - p).squaredNorm() < r2) return true;
                }
        return false;
    }

private:
    std::array<long, 3> cellOf(const V3& p) const
    {
        return {long(std::floor(p.x() / cell_)), long(std::floor(p.y() / cell_)), long(std::floor(p.z() / cell_))};
    }
    static uint64_t key(const std::array<long, 3>& c)
    {
        const uint64_t m = (uint64_t(1) << 21) - 1;
        return ((uint64_t(c[0] + (1 << 20)) & m) << 42) | ((uint64_t(c[1] + (1 << 20)) & m) << 21) | (uint64_t(c[2] + (1 << 20)) & m);
    }

    const std::vector<V3>& pts_;
    double cell_;
    std::unordered_map<uint64_t, std::vector<uint32_t>> grid_;
};

// Two unit vectors that span the plane normal to n
void tangents(const V3& n, V3& a, V3& b)
{
    const V3 axis = std::abs(n.x()) < 0.6 ? V3(1, 0, 0) : (std::abs(n.y()) < 0.6 ? V3(0, 1, 0) : V3(0, 0, 1));
    a = n.cross(axis).normalized();
    b = n.cross(a).normalized();
}

}   // namespace

bool selectSurfacePatch(const Tree& body, const std::map<Tree::Id, float>& vars, const V3& seed, double angleDegrees, int mode,
                        double maxRadius, double spacing, const V3& lo, const V3& hi, SurfacePatch& out, std::string& error)
{
    out = SurfacePatch();
    if (!(spacing > 0) || !std::isfinite(spacing))
    {
        error = "the spacing of the samples must be positive";
        return false;
    }
    if (!(angleDegrees > 0) || angleDegrees > 90.0)
    {
        error = "the angle is between 0 and 90 degrees";
        return false;
    }
    const V3 diag = hi - lo;
    if (!diag.allFinite() || diag.minCoeff() <= 0 || diag.maxCoeff() / spacing > 1.0e6)
    {
        error = "the part is too big for samples this close (more than a million along its length): raise the spacing";
        return false;
    }
    Field F(body, vars);
    const double s = spacing;
    const double cosLimit = std::cos(angleDegrees * M_PI / 180.0);

    // the seed, moved along the gradient onto the surface
    std::vector<V3> p0{seed}, n0;
    std::vector<char> ok0;
    projectToSurface(F, p0, n0, ok0, diag.norm(), 1e-4 * s);
    if (!ok0[0] || !p0[0].allFinite())
    {
        error = "no surface was found near the seed: put it on, or close to, the part";
        return false;
    }
    out.spacing = s;
    out.seedPoint = p0[0];
    out.seedDistance = (p0[0] - seed).norm();
    out.points.push_back(p0[0]);
    out.normals.push_back(n0[0]);
    const V3 nSeed = n0[0];

    // the lowest and highest corners of what may be reached: a little past the box, which only bounds the search
    const V3 boxLo = lo - V3::Constant(2 * s), boxHi = hi + V3::Constant(2 * s);

    SampleHash hash(out.points, 0.7 * s);
    hash.add(0);
    std::vector<size_t> frontier{0};
    // (the sample every sample was reached from: the smooth walk measures how far the surface has turned along the way back)
    std::vector<size_t> cameFrom{size_t(-1)};
    // How tightly the surface may bend in the smooth mode: `angle` degrees within this length of the walk (a curvature limit that
    // does not depend on how close the samples are: a limit per step would be a limit on the triangles of a mesh, and a rounded
    // skin never turns that much in a step)
    const double kSmoothLength = 10.0;
    const int smoothSteps = std::max(1, int(std::lround(kSmoothLength / s)));
    const double noiseFloor = std::min(angleDegrees, 10.0);       // (the normals of a mesh jump by a few degrees from facet to facet)
    const size_t kMax = 4000000;
    std::vector<V3> cand, cn;
    std::vector<size_t> parent;
    std::vector<char> ok;
    while (!frontier.empty())
    {
        cand.clear();
        parent.clear();
        for (size_t f : frontier)
        {
            const V3 p = out.points[f];
            V3 a, b;
            tangents(out.normals[f], a, b);
            for (int k = 0; k < 8; ++k)
            {
                const double t = k * M_PI / 4.0;
                const V3 q = p + s * (std::cos(t) * a + std::sin(t) * b);
                if (hash.near(q, 0.55 * s)) continue;              // (the surface there is taken already: nothing to look at)
                cand.push_back(q);
                parent.push_back(f);
            }
        }
        if (cand.empty()) break;
        std::vector<V3> start = cand;
        projectToSurface(F, cand, cn, ok, s, 2e-3 * s);
        std::vector<size_t> next;
        for (size_t i = 0; i < cand.size(); ++i)
        {
            if (!ok[i] || !cand[i].allFinite()) continue;
            const V3& q = cand[i];
            // (a point that the walk had to carry far to the surface is past an edge or a gap: the surface does not go on there)
            if ((q - start[i]).norm() > 0.6 * s) continue;
            if ((q.array() < boxLo.array()).any() || (q.array() > boxHi.array()).any()) continue;
            if (maxRadius > 0 && (q - out.seedPoint).norm() > maxRadius) continue;
            const V3& nq = cn[i];
            double c, limit = cosLimit;
            if (mode == 0)
                c = nq.dot(nSeed);
            else
            {
                // the sample about kSmoothLength back along the walk (or the seed, if the walk is not that long yet): the surface may have
                // turned `angle` degrees for every kSmoothLength of the way between them
                size_t a = parent[i];
                int steps = 1;
                while (steps < smoothSteps && cameFrom[a] != size_t(-1))
                {
                    a = cameFrom[a];
                    ++steps;
                }
                const double allowed = std::min(179.0, std::max(noiseFloor, angleDegrees * (steps * s) / kSmoothLength));
                limit = std::cos(allowed * M_PI / 180.0);
                c = nq.dot(out.normals[a]);
            }
            if (!(c >= limit)) continue;
            if (hash.near(q, 0.7 * s)) continue;
            out.points.push_back(q);
            out.normals.push_back(nq);
            cameFrom.push_back(parent[i]);
            hash.add(out.points.size() - 1);
            next.push_back(out.points.size() - 1);
            if (out.points.size() >= kMax)
            {
                out.stopped = true;
                break;
            }
        }
        if (out.stopped) break;
        frontier.swap(next);
    }
    return true;
}

// The distance to the nearest of a set of points, as a field: a kd-tree of the points, so that a point of the field and a box
// of space are answered by looking at the few that are near
namespace {

struct PointCloud
{
    std::vector<V3> p;
    std::vector<V3> n;              // (the normals, for a cloud of oriented points: see orientedPointsTree)
    double sigma = 0;               // (and the width of the blend of their planes)
    struct Node
    {
        V3 lo = V3::Zero(), hi = V3::Zero();
        int left = -1, right = -1;
        uint32_t start = 0, count = 0;
    };
    std::vector<Node> nodes;
    std::vector<uint32_t> order;
    std::string key;

    void build()
    {
        order.resize(p.size());
        std::iota(order.begin(), order.end(), uint32_t(0));
        nodes.clear();
        nodes.reserve(p.size() / 4 + 16);
        make(0, uint32_t(p.size()));
        // (a hash of the points to a thousandth, in the order of the tree: what the cloud is, not how it was found)
        uint64_t h = 1469598103934665603ull;
        std::vector<std::array<int64_t, 3>> r;
        r.reserve(p.size());
        for (const V3& q : p) r.push_back({int64_t(std::llround(q.x() * 1000)), int64_t(std::llround(q.y() * 1000)), int64_t(std::llround(q.z() * 1000))});
        std::sort(r.begin(), r.end());
        for (const auto& a : r)
            for (int64_t v : a)
            {
                h ^= uint64_t(v);
                h *= 1099511628211ull;
            }
        char buf[64];
        std::snprintf(buf, sizeof(buf), "points#%016llx#%zu", static_cast<unsigned long long>(h), p.size());
        key = buf;
    }

    int make(uint32_t start, uint32_t count)
    {
        Node n;
        n.start = start;
        n.count = count;
        n.lo = V3::Constant(1e300);
        n.hi = V3::Constant(-1e300);
        for (uint32_t i = start; i < start + count; ++i)
        {
            n.lo = n.lo.cwiseMin(p[order[i]]);
            n.hi = n.hi.cwiseMax(p[order[i]]);
        }
        const int index = int(nodes.size());
        nodes.push_back(n);
        if (count <= 8) return index;
        const V3 ext = n.hi - n.lo;
        int axis = 0;
        if (ext.y() > ext[axis]) axis = 1;
        if (ext.z() > ext[axis]) axis = 2;
        if (!(ext[axis] > 0)) return index;
        const uint32_t half = count / 2;
        std::nth_element(order.begin() + start, order.begin() + start + half, order.begin() + start + count,
                         [&](uint32_t a, uint32_t b) { return p[a][axis] < p[b][axis]; });
        const int l = make(start, half);
        const int r = make(start + half, count - half);
        nodes[size_t(index)].left = l;
        nodes[size_t(index)].right = r;
        return index;
    }

    static double boxDistance2(const V3& q, const V3& lo, const V3& hi)
    {
        const V3 d = (lo - q).cwiseMax(V3::Zero()).cwiseMax((q - hi).cwiseMax(V3::Zero()));
        return d.squaredNorm();
    }

    // the squared distance to the nearest point, and which
    void nearest(const V3& q, int node, double& best, uint32_t& who) const
    {
        const Node& n = nodes[size_t(node)];
        if (boxDistance2(q, n.lo, n.hi) >= best) return;
        if (n.left < 0)
        {
            for (uint32_t i = n.start; i < n.start + n.count; ++i)
            {
                const double d = (p[order[i]] - q).squaredNorm();
                if (d < best)
                {
                    best = d;
                    who = order[i];
                }
            }
            return;
        }
        const Node& a = nodes[size_t(n.left)];
        const Node& b = nodes[size_t(n.right)];
        const bool first = boxDistance2(q, a.lo, a.hi) <= boxDistance2(q, b.lo, b.hi);
        nearest(q, first ? n.left : n.right, best, who);
        nearest(q, first ? n.right : n.left, best, who);
    }

    // the points within sqrt(r2) of q
    void within(const V3& q, double r2, int node, std::vector<uint32_t>& out) const
    {
        const Node& nd = nodes[size_t(node)];
        if (boxDistance2(q, nd.lo, nd.hi) > r2) return;
        if (nd.left < 0)
        {
            for (uint32_t i = nd.start; i < nd.start + nd.count; ++i)
                if ((p[order[i]] - q).squaredNorm() <= r2) out.push_back(order[i]);
            return;
        }
        within(q, r2, nd.left, out);
        within(q, r2, nd.right, out);
    }

    // the squared distance from a box to the nearest point of the cloud
    void boxNearest(const V3& lo, const V3& hi, int node, double& best) const
    {
        const Node& n = nodes[size_t(node)];
        // (the boxes' own distance: the cloud's node box and the query box)
        const V3 gap = (n.lo - hi).cwiseMax(V3::Zero()).cwiseMax((lo - n.hi).cwiseMax(V3::Zero()));
        if (gap.squaredNorm() >= best) return;
        if (n.left < 0)
        {
            for (uint32_t i = n.start; i < n.start + n.count; ++i)
                best = std::min(best, boxDistance2(p[order[i]], lo, hi));
            return;
        }
        boxNearest(lo, hi, n.left, best);
        boxNearest(lo, hi, n.right, best);
    }
};

class PointCloudOracle : public OracleStorage<>
{
public:
    explicit PointCloudOracle(std::shared_ptr<const PointCloud> c) : cloud(std::move(c)) {}

    void evalInterval(Interval& out) override
    {
        const V3 lo = lower.cast<double>(), hi = upper.cast<double>();
        const V3 c = 0.5 * (lo + hi);
        const double r = 0.5 * (hi - lo).norm();
        double bestBox = std::numeric_limits<double>::infinity();
        cloud->boxNearest(lo, hi, 0, bestBox);
        double best = std::numeric_limits<double>::infinity();
        uint32_t who = 0;
        cloud->nearest(c, 0, best, who);
        out = Interval(float(std::sqrt(bestBox)), float(std::sqrt(best) + r));
    }

    void evalPoint(float& out, size_t index) override
    {
        double best = std::numeric_limits<double>::infinity();
        uint32_t who = 0;
        cloud->nearest(points.col(index).matrix().cast<double>(), 0, best, who);
        out = float(std::sqrt(best));
    }

    void checkAmbiguous(Eigen::Block<Eigen::Array<bool, 1, LIBFIVE_EVAL_ARRAY_SIZE>, 1, Eigen::Dynamic> /* out */) override {}

    void evalFeatures(boost::container::small_vector<Feature, 4>& out) override
    {
        const V3 q = points.col(0).matrix().cast<double>();
        double best = std::numeric_limits<double>::infinity();
        uint32_t who = 0;
        cloud->nearest(q, 0, best, who);
        const V3 away = q - cloud->p[who];
        const double len = away.norm();
        out.push_back(Feature(len > 1e-12 ? Eigen::Vector3f((away / len).cast<float>()) : Eigen::Vector3f(0, 0, 0)));
    }

private:
    std::shared_ptr<const PointCloud> cloud;
};

class PointCloudClause : public OracleClause
{
public:
    explicit PointCloudClause(std::shared_ptr<const PointCloud> c) : cloud(std::move(c)) {}
    std::unique_ptr<Oracle> getOracle() const override { return std::make_unique<PointCloudOracle>(cloud); }
    std::string name() const override { return "PointCloudDistance"; }
    std::string contentKey() const override { return cloud->key; }
    std::string persistentKey() const override { return cloud->key; }

private:
    std::shared_ptr<const PointCloud> cloud;
};

// The field of a SURFACE made of oriented points (the samples of a walk over it, each with the normal of the surface there): at a point, its
// height above the surface along the normal -- the mean of (q - p).n over the samples p near it, weighted by how near they are and by how
// little their normal turns from that of the nearest one (so that a sharp edge is not rounded off).  It is zero on the surface, positive
// on the side the normals face.  The surface alone: nothing that lies behind it is in the field, so it has no thickness to find
double orientedValue(const PointCloud& c, const V3& q, V3* grad)
{
    double best = std::numeric_limits<double>::infinity();
    uint32_t who = 0;
    c.nearest(q, 0, best, who);
    const V3 n0 = c.n[who];
    std::vector<uint32_t> near;
    const double R = 3.0 * c.sigma;
    c.within(q, R * R, 0, near);
    double sw = 0, sf = 0;
    V3 sn = V3::Zero();
    for (uint32_t i : near)
    {
        const double a = c.n[i].dot(n0);
        if (!(a > 0)) continue;
        const V3 d = q - c.p[i];
        const double w = std::exp(-d.squaredNorm() / (c.sigma * c.sigma)) * std::pow(a, 6.0);
        sw += w;
        sf += w * d.dot(c.n[i]);
        sn += w * c.n[i];
    }
    if (!(sw > 1e-12))
    {
        if (grad) *grad = n0;
        return (q - c.p[who]).dot(n0);
    }
    if (grad) *grad = sn.norm() > 1e-12 ? V3(sn.normalized()) : n0;
    return sf / sw;
}

class OrientedPointsOracle : public OracleStorage<>
{
public:
    explicit OrientedPointsOracle(std::shared_ptr<const PointCloud> c) : cloud(std::move(c)) {}

    void evalInterval(Interval& out) override
    {
        const V3 lo = lower.cast<double>(), hi = upper.cast<double>();
        const V3 mid = 0.5 * (lo + hi);
        const double r = 0.5 * (hi - lo).norm();
        double best = std::numeric_limits<double>::infinity();
        uint32_t who = 0;
        cloud->nearest(mid, 0, best, who);
        // (the height above the surface is at most the distance to the samples that count)
        const double u = 3.0 * cloud->sigma + std::sqrt(best) + r;
        out = Interval(float(-u), float(u));
    }

    void evalPoint(float& out, size_t index) override
    {
        out = float(orientedValue(*cloud, points.col(index).matrix().cast<double>(), nullptr));
    }

    void checkAmbiguous(Eigen::Block<Eigen::Array<bool, 1, LIBFIVE_EVAL_ARRAY_SIZE>, 1, Eigen::Dynamic> /* out */) override {}

    void evalFeatures(boost::container::small_vector<Feature, 4>& out) override
    {
        V3 g = V3::Zero();
        orientedValue(*cloud, points.col(0).matrix().cast<double>(), &g);
        out.push_back(Feature(Eigen::Vector3f(g.cast<float>())));
    }

private:
    std::shared_ptr<const PointCloud> cloud;
};

class OrientedPointsClause : public OracleClause
{
public:
    explicit OrientedPointsClause(std::shared_ptr<const PointCloud> c) : cloud(std::move(c)) {}
    std::unique_ptr<Oracle> getOracle() const override { return std::make_unique<OrientedPointsOracle>(cloud); }
    std::string name() const override { return "OrientedPointsSurface"; }
    std::string contentKey() const override { return cloud->key; }
    std::string persistentKey() const override { return cloud->key; }

private:
    std::shared_ptr<const PointCloud> cloud;
};

}   // namespace

Tree orientedPointsTree(const std::vector<V3>& points, const std::vector<V3>& normals, double sigma)
{
    auto cloud = std::make_shared<PointCloud>();
    cloud->p = points;
    cloud->n = normals;
    cloud->sigma = sigma;
    cloud->build();
    // (the points are in the key already; the normals and the width of the blend are what else the field is)
    uint64_t h = 1469598103934665603ull;
    for (const V3& q : normals)
        for (int k = 0; k < 3; ++k)
        {
            h ^= uint64_t(int64_t(std::llround(q[k] * 1000)));
            h *= 1099511628211ull;
        }
    h ^= uint64_t(std::llround(sigma * 1000));
    h *= 1099511628211ull;
    char buf[64];
    std::snprintf(buf, sizeof(buf), "#oriented%016llx", static_cast<unsigned long long>(h));
    cloud->key += buf;
    return Tree(std::make_unique<OrientedPointsClause>(cloud));
}

Tree pointsDistanceTree(const std::vector<V3>& points)
{
    auto cloud = std::make_shared<PointCloud>();
    cloud->p = points;
    cloud->build();
    return Tree(std::make_unique<PointCloudClause>(cloud));
}

}   // namespace surface
}   // namespace libfive
