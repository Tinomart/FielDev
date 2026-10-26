#pragma once

#include <Eigen/Core>

#include <algorithm>
#include <cmath>
#include <vector>

namespace FielDev
{

// The signed distance from a point to a closed outline in a plane -- the cross-section of a sweep -- negative inside it (the even-odd rule), exact: the field of a profile has the very same number.
// The mesher asks for it millions of times, and a loop over every segment of the outline for each of them was three quarters of the time it took to mesh an armature.  So the plane round the
// outline is cut into a grid of cells, and each cell keeps only the segments that can be the nearest to a point in it: those no farther from the middle of the cell than the nearest one is, plus the
// diagonal of the cell (the nearest segment of any point in the cell is within that), and whether the middle of the cell is inside.  A point is told apart from the middle of its cell by the segments
// it crosses on the way there, which are all in the list (they cross the cell).  A point outside the grid takes the loop over every segment.
class OutlineIndex
{
public:
    // `poly`: the outline, closed (the last point joins the first)
    void build(const std::vector<Eigen::Vector2d>& poly)
    {
        const size_t n = poly.size();
        edges_.resize(n);
        double lox = 1e300, hix = -1e300, loy = 1e300, hiy = -1e300;
        for (size_t i = 0; i < n; ++i)
        {
            const Eigen::Vector2d& a = poly[i];
            const Eigen::Vector2d& b = poly[(i + 1) % n];
            Edge& e = edges_[i];
            e.ax = a.x();
            e.ay = a.y();
            e.bx = b.x();
            e.by = b.y();
            e.dx = e.bx - e.ax;
            e.dy = e.by - e.ay;
            const double l2 = e.dx * e.dx + e.dy * e.dy;
            e.inv = l2 > 0 ? 1.0 / l2 : 0.0;
            lox = std::min(lox, a.x());
            hix = std::max(hix, a.x());
            loy = std::min(loy, a.y());
            hiy = std::max(hiy, a.y());
        }
        lists_.clear();
        start_.clear();
        inside_.clear();
        nx_ = ny_ = 0;
        const double w = hix - lox, h = hiy - loy, side = std::max(w, h);
        if (n < 3 || !(side > 0) || !std::isfinite(side)) return;
        // (the cells reach past the outline by half its size: a point a few cells of the mesher outside the surface is still in the grid)
        const double margin = 0.5 * side;
        x0_ = lox - margin;
        y0_ = loy - margin;
        cell_ = (side + 2.0 * margin) / kCells;
        inv_ = 1.0 / cell_;
        nx_ = std::min(kCells, std::max(1, int(std::ceil((w + 2.0 * margin) / cell_))));
        ny_ = std::min(kCells, std::max(1, int(std::ceil((h + 2.0 * margin) / cell_))));
        const double half = 0.5 * std::sqrt(2.0) * cell_;           // (half the diagonal of a cell)
        start_.assign(size_t(nx_) * size_t(ny_) + 1, 0);
        inside_.assign(size_t(nx_) * size_t(ny_), 0);
        std::vector<double> d2(n);
        for (int j = 0; j < ny_; ++j)
            for (int i = 0; i < nx_; ++i)
            {
                const double mx = x0_ + (i + 0.5) * cell_, my = y0_ + (j + 0.5) * cell_;
                double best = 1e300;
                for (size_t k = 0; k < n; ++k)
                {
                    d2[k] = segment2(edges_[k], mx, my);
                    best = std::min(best, d2[k]);
                }
                const double reach = std::sqrt(best) + 2.0 * half + 1e-9;
                for (size_t k = 0; k < n; ++k)
                    if (d2[k] <= reach * reach) lists_.push_back(edges_[k]);
                const size_t c = size_t(j) * size_t(nx_) + size_t(i);
                // (whether the middle is inside: the segments it crosses on the way from a point far outside, found by the very test that tells a point from the middle later, so that a middle that lies
                // exactly on a segment is on the same side of it in both)
                const double farx = lox - 4.0 * side - 1.0, fary = my + 0.3141592653589793 * side;
                bool in = false;
                for (const Edge& e : edges_)
                    if (crosses(e, farx, fary, mx, my)) in = !in;
                inside_[c] = in ? 1 : 0;
                start_[c + 1] = lists_.size();
            }
    }

    double signedDistance(double x, double y) const
    {
        const double fx = (x - x0_) * inv_, fy = (y - y0_) * inv_;
        if (!(fx >= 0 && fy >= 0 && fx < nx_ && fy < ny_)) return slow(x, y);
        const int i = int(fx), j = int(fy);
        const size_t c = size_t(j) * size_t(nx_) + size_t(i);
        const double rx = x0_ + (i + 0.5) * cell_, ry = y0_ + (j + 0.5) * cell_;
        bool inside = inside_[c] != 0;
        double best = 1e300;
        for (size_t k = start_[c], last = start_[c + 1]; k < last; ++k)
        {
            const Edge& e = lists_[k];
            best = std::min(best, segment2(e, x, y));
            if (crosses(e, x, y, rx, ry)) inside = !inside;           // (each segment the way from the point to the middle of its cell crosses turns inside and outside round)
        }
        return inside ? -std::sqrt(best) : std::sqrt(best);
    }

private:
    struct Edge
    {
        double ax = 0, ay = 0, bx = 0, by = 0, dx = 0, dy = 0, inv = 0;       // (inv: 1 / the squared length, 0 for a segment of no length)
    };
    static constexpr int kCells = 32;

    static double segment2(const Edge& e, double x, double y)
    {
        const double t = std::max(0.0, std::min(1.0, ((x - e.ax) * e.dx + (y - e.ay) * e.dy) * e.inv));
        const double px = e.ax + t * e.dx - x, py = e.ay + t * e.dy - y;
        return px * px + py * py;
    }

    // Whether the segment `e` crosses the way from (px, py) to (rx, ry): its two ends are on two sides of the way, and the two ends of the way on two sides of the segment.  "Not above" counts as one side
    // everywhere, so that the two segments that meet at a corner are told apart from the same side, and a way through a corner, or to a point on a segment, is counted as it would be if the point were
    // moved a hair to that side
    static bool crosses(const Edge& e, double px, double py, double rx, double ry)
    {
        const double ux = rx - px, uy = ry - py;
        const double ca = ux * (e.ay - py) - uy * (e.ax - px), cb = ux * (e.by - py) - uy * (e.bx - px);
        if ((ca > 0) == (cb > 0)) return false;
        const double sp = e.dx * (py - e.ay) - e.dy * (px - e.ax), sr = e.dx * (ry - e.ay) - e.dy * (rx - e.ax);
        return (sp > 0) != (sr > 0);
    }

    double slow(double x, double y) const
    {
        bool inside = false;
        double best = 1e300;
        for (const Edge& e : edges_)
        {
            if ((e.ay > y) != (e.by > y) && x < e.ax + (y - e.ay) * e.dx / e.dy) inside = !inside;
            best = std::min(best, segment2(e, x, y));
        }
        return inside ? -std::sqrt(best) : std::sqrt(best);
    }

    std::vector<Edge> edges_;               // (every segment of the outline)
    std::vector<Edge> lists_;               // (the segments of every cell, one cell after the other)
    std::vector<size_t> start_;             // (where the segments of cell c are in lists_: start_[c] .. start_[c + 1])
    std::vector<unsigned char> inside_;     // (whether the middle of cell c is inside the outline)
    double x0_ = 0, y0_ = 0, cell_ = 1, inv_ = 1;
    int nx_ = 0, ny_ = 0;
};

}   // namespace FielDev
