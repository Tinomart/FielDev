/*
libfive: a CAD kernel for modeling with implicit functions

Selecting a patch of a surface from the field alone, and fields made of points (surface_select.cpp).

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#pragma once

#include <array>
#include <cstdint>
#include <map>
#include <string>
#include <vector>

#include <Eigen/Eigen>

#include "libfive/tree/tree.hpp"

namespace libfive {
namespace surface {

/*  A patch of the surface of a body that a flood fill from `seed` reaches, found from the field alone: its value and gradient
 *  (no mesh of the body is made).  The seed is moved along the gradient onto the surface (where the field is zero), and the walk
 *  spreads from there over the surface in steps of `spacing`: from every sample, eight steps along the surface (in its tangent
 *  plane), each carried onto the surface again.  A step is taken where
 *      mode 0 (flat)     the surface there faces within `angleDegrees` of the way it faces at the seed
 *      mode 1 (smooth)   the surface has turned less than `angleDegrees` for every 10 mm of the walk, from the sample about 10 mm
 *                        back (or from the seed, if the walk is shorter): a limit on how tightly it bends -- a cylinder, a fillet, a
 *                        rounded skin are followed; a tight bend, or a sharp edge, stops it
 *  and, if `maxRadius` > 0, is within it of the seed's place on the surface.  The surface is followed, not the space: where the
 *  surface is not there (past an edge, across a gap) a step finds nothing to land on, however thin the part is.  `lo`..`hi` is the
 *  box of the body (the walk stays inside it).  The result is samples of the surface of the patch, about `spacing` apart, with
 *  the surface normal at each.  */
struct SurfacePatch
{
    std::vector<Eigen::Vector3d> points, normals;
    Eigen::Vector3d seedPoint = Eigen::Vector3d::Zero();    // where the seed is on the surface
    double seedDistance = 0;                                // how far from it the seed was
    double spacing = 0;
    bool stopped = false;                                   // the walk was cut short (too many samples)
};
bool selectSurfacePatch(const Tree& body, const std::map<Tree::Id, float>& vars, const Eigen::Vector3d& seed,
                        double angleDegrees, int mode, double maxRadius, double spacing, const Eigen::Vector3d& lo,
                        const Eigen::Vector3d& hi, SurfacePatch& out, std::string& error);

/*  The distance to the nearest of a set of points, as a field (a tree): a kd-tree answers a point or a box of space by looking
 *  at the few points near it.  Kept (the render cache) by a hash of the points rounded to a thousandth.  */
Tree pointsDistanceTree(const std::vector<Eigen::Vector3d>& points);

/*  The field of a surface made of oriented points: the height above it along the normal, zero on it, positive on the side the normals face
 *  -- a surface and nothing else, no body behind it.  Blended over `sigma` (about the spacing of the points); a sharp edge is kept.  */
Tree orientedPointsTree(const std::vector<Eigen::Vector3d>& points, const std::vector<Eigen::Vector3d>& normals, double sigma);

}   // namespace surface
}   // namespace libfive
