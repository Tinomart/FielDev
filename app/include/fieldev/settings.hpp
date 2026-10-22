/*
FielDev: field-driven design
Derived from Studio, a simple GUI for the libfive CAD kernel
Copyright (C) 2017  Matt Keeter

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
*/
#pragma once

#include <QObject>
#include <QList>
#include <QPointer>
#include <QString>
#include <QVector3D>
#include <QWidget>
#include <QDoubleSpinBox>
#include <QCheckBox>

namespace FielDev {

/*  A picture to model over: a reference_image(...) of the script.  It stands in the plane through `center` that `u` (the picture's right) and `v` (its up) span, `height` mm
 *  tall (0: as tall as the render region is along `v`); the width follows the picture.  Not a model: it is drawn behind them in the viewport and nothing is exported of it  */
struct ReferenceImage
{
    QString path;
    QVector3D center;
    QVector3D u{1, 0, 0};
    QVector3D v{0, 0, 1};
    float height = 0;
    float opacity = 0.5f;
    float scale = 1;                // (the scale of the gizmo of the point that is its middle: the picture is that much larger than `height` says)
    bool flip = false;
    bool visible = true;

    bool operator==(const ReferenceImage& o) const
    {
        return path == o.path && center == o.center && u == o.u && v == o.v && height == o.height && opacity == o.opacity && scale == o.scale && flip == o.flip && visible == o.visible;
    }
    bool operator!=(const ReferenceImage& o) const { return !(*this == o); }
};

struct Settings
{
    /*
     *  Useful constructor
     */
    Settings(QVector3D min, QVector3D max, float res, float quality);

    /*
     *  Default constructor (produces an object that shouldn't be used)
     */
    Settings() : res(-1), quality(-1) { /* Nothing to do here */ }

    /*
     *  Constructor for sensible settings, used by default in viewport
     */
    static Settings defaultSettings();

    /*
     *  Estimates a reasonable resolution scale for incremental rendering
     */
    int defaultDiv() const;

    QVector3D min;
    QVector3D max;
    float res;
    float quality;

    /*  view.set_bounds(..., auto_scale=True), the default: the region follows the models (the script's numbers are rewritten as they reach out of
     *  it), and every shape that has no resolution of its own is meshed at the scene's resolution scaled by its size next to the region  */
    bool autoScale = true;

    /*  The pictures of the script's reference_image(...) calls.  Not part of the comparison below: they are no reason to render a shape again; the viewport looks at them on its own  */
    QList<ReferenceImage> references;

    bool operator==(const Settings& other) const;
    bool operator!=(const Settings& other) const;
};
} // namespace FielDev
