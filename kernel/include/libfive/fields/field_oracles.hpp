/*
libfive: a CAD kernel for modeling with implicit functions

Fields derived from another shape's field: its gradient (surface normals)
and the mean curvature; and noise and scattered-sample fields.
Each is a new field (a Tree) evaluated through an oracle that runs the
original shape's evaluator.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
*/
#pragma once

#include <map>
#include <vector>
#include <Eigen/Eigen>

#include "libfive/tree/tree.hpp"

namespace libfive {
namespace fields {

/*  mode 0..2: x / y / z of the unit normal (the normalized gradient);
 *  3: the gradient's length; 4..6: x / y / z of the raw gradient  */
Tree gradientField(const Tree& t, int mode);

/*  Mean curvature (1/mm, positive where convex), from the divergence of the
 *  unit normal with central differences of step h  */
Tree curvatureField(const Tree& t, double h);

/*  A field through scattered samples: inverse-distance weighting (with the
 *  given power) of the k nearest samples  */
Tree pointCloudField(const std::vector<Eigen::Vector3d>& points,
                     const std::vector<double>& values, int k, double power);

/*  Seeded Perlin noise (fractal sum of octaves), about -1 .. 1; `scale` is
 *  the size of the largest features  */
Tree noiseField(double scale, int octaves, unsigned seed, double gain, double lacunarity);
/*  Cellular (Worley) noise at one scale: mode 0 the distance to the nearest point of a jittered grid, 1 the distance from a wall between cells (F2 - F1), 2 the distance to
 *  the second nearest; about -1 .. 1  */
Tree cellularField(double scale, unsigned seed, int mode, double jitter);

}   // namespace fields
}   // namespace libfive
