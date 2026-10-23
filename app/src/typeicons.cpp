/*
FielDev: field-driven design
Derived from Studio, a simple GUI for the libfive CAD kernel

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
*/
#include <cmath>
#include <functional>

#include <QHash>
#include <QPainter>
#include <QPainterPath>
#include <QPixmap>
#include <QPolygonF>
#include <QRadialGradient>

#include "fieldev/i18n.hpp"
#include "fieldev/typeicons.hpp"

namespace FielDev {
namespace TypeIcons {

namespace {

const double kPi = 3.14159265358979323846;

struct Kind { QString label; QColor color; };

// (the same as fieldev/kinds.py says; the interpreter's own list replaces them when it has been asked)
QHash<QString, Kind>& kinds()
{
    static QHash<QString, Kind> k = {
        {"solid",      {"3D shape",     QColor("#3fa9ff")}},
        {"curve",      {"1D shape",     QColor("#b9a7ff")}},
        {"profile",    {"2D shape",     QColor("#1fd6b0")}},
        {"field",      {"Field",        QColor("#9be04a")}},
        {"surface",    {"Surface",      QColor("#c58bff")}},
        {"point",      {"Point",        QColor("#ffc93c")}},
        {"points",     {"Point set",    QColor("#ff9f43")}},
        {"import",     {"Import",       QColor("#1cc9c0")}},
        {"symmetry",   {"Symmetry",     QColor("#d33682")}},
        {"block",      {"Custom block", QColor("#9fb4ff")}},
        // (not kinds of model: the parts of the right-click menus that are not primitives)
        {"operation",  {"Operation",    QColor("#ff9ec7")}},
        {"shapes",     {"Parametric shape", QColor("#6e9bff")}},
        {"python",     {"Python",       QColor("#8b7bff")}},
        // (the Characters menu)
        {"character",  {"Character",    QColor("#ffcf4a")}},
        {"armature",   {"Armature",     QColor("#7fd1ff")}},
        {"feature",    {"Feature model", QColor("#ff8fc2")}},
    };
    return k;
}

QHash<QString, QIcon>& cache()
{
    static QHash<QString, QIcon> c;
    return c;
}

// Line-art at 2x, as the other icons of the model tree are
QIcon draw(std::function<void(QPainter&)> paint)
{
    QPixmap px(32, 32);
    px.fill(Qt::transparent);
    QPainter p(&px);
    p.setRenderHint(QPainter::Antialiasing);
    p.scale(2, 2);
    paint(p);
    p.end();
    px.setDevicePixelRatio(2);
    return QIcon(px);
}

QColor alpha(QColor c, int a)
{
    c.setAlpha(a);
    return c;
}

void drawKind(QPainter& p, const QString& type, const QColor& c)
{
    if (type == "curve")
    {
        // a line through points: a spline with its two ends marked
        QPainterPath path;
        path.moveTo(2.4, 11.2);
        path.cubicTo(5.0, 2.6, 9.4, 14.2, 13.6, 4.8);
        p.setPen(QPen(c, 1.9, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.setBrush(Qt::NoBrush);
        p.drawPath(path);
        p.setPen(Qt::NoPen);
        p.setBrush(c);
        p.drawEllipse(QPointF(2.4, 11.2), 1.7, 1.7);
        p.drawEllipse(QPointF(13.6, 4.8), 1.7, 1.7);
    }
    else if (type == "profile")
    {
        // a flat shape: a square with its fill
        p.setPen(QPen(c, 1.9, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.setBrush(alpha(c, 150));
        p.drawRoundedRect(QRectF(2.8, 2.8, 10.4, 10.4), 1.6, 1.6);
    }
    else if (type == "field")
    {
        // a value at every point: a soft disc, solid in the middle
        QRadialGradient g(QPointF(8, 8), 7);
        g.setColorAt(0.0, c);
        g.setColorAt(0.55, alpha(c, 150));
        g.setColorAt(1.0, alpha(c, 25));
        p.setPen(Qt::NoPen);
        p.setBrush(g);
        p.drawEllipse(QPointF(8, 8), 7, 7);
    }
    else if (type == "surface")
    {
        // an open sheet seen at an angle, with a wave across it
        QPolygonF sheet({QPointF(1.5, 11.5), QPointF(5.2, 3.5), QPointF(14.5, 3.5), QPointF(10.8, 11.5)});
        p.setPen(QPen(c, 1.9, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.setBrush(alpha(c, 140));
        p.drawPolygon(sheet);
        QPainterPath wave;
        wave.moveTo(3.4, 8.6);
        wave.cubicTo(5.6, 4.8, 8.4, 11.2, 12.6, 6.4);
        p.setBrush(Qt::NoBrush);
        p.drawPath(wave);
    }
    else if (type == "point")
    {
        p.setPen(QPen(alpha(c, 200), 1.3, Qt::SolidLine, Qt::RoundCap));
        p.drawLine(QPointF(8, 1.6), QPointF(8, 4.6));
        p.drawLine(QPointF(8, 11.4), QPointF(8, 14.4));
        p.drawLine(QPointF(1.6, 8), QPointF(4.6, 8));
        p.drawLine(QPointF(11.4, 8), QPointF(14.4, 8));
        p.setPen(Qt::NoPen);
        p.setBrush(c);
        p.drawEllipse(QPointF(8, 8), 2.7, 2.7);
    }
    else if (type == "points")
    {
        // a set of points: a scatter
        p.setPen(Qt::NoPen);
        p.setBrush(c);
        const QPointF dots[7] = {QPointF(3.4, 4.2), QPointF(8.2, 2.8), QPointF(12.6, 5.6), QPointF(6.0, 8.6), QPointF(11.0, 10.8),
                                 QPointF(3.6, 12.6), QPointF(8.6, 13.0)};
        for (int k = 0; k < 7; ++k) p.drawEllipse(dots[k], k % 3 == 0 ? 1.9 : 1.5, k % 3 == 0 ? 1.9 : 1.5);
    }
    else if (type == "import")
    {
        // a file read in: an open box
        p.setPen(QPen(c, 1.9));
        p.setBrush(Qt::NoBrush);
        p.drawRect(QRectF(3, 5, 8, 8));
        p.drawLine(QPointF(3, 5), QPointF(6, 2));
        p.drawLine(QPointF(11, 5), QPointF(14, 2));
        p.drawLine(QPointF(6, 2), QPointF(14, 2));
        p.drawLine(QPointF(14, 2), QPointF(14, 10));
        p.drawLine(QPointF(11, 13), QPointF(14, 10));
    }
    else if (type == "symmetry")
    {
        // mirror planes: a mirror (dashed line) with a shape and its image either side of it
        p.setPen(QPen(c, 1.9, Qt::DashLine, Qt::RoundCap));
        p.drawLine(QPointF(8, 1.2), QPointF(8, 14.8));
        p.setPen(QPen(c, 1.9, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.setBrush(alpha(c, 165));
        QPolygonF left;
        left << QPointF(2.2, 4.0) << QPointF(6.4, 8.0) << QPointF(2.2, 12.0);
        p.drawPolygon(left);
        p.setBrush(Qt::NoBrush);
        QPolygonF right;
        right << QPointF(13.8, 4.0) << QPointF(9.6, 8.0) << QPointF(13.8, 12.0);
        p.drawPolygon(right);
    }
    else if (type == "armature")
    {
        // nodes joined into a chain, the way an armature is: a fat line through three dots
        const QPointF nodes[3] = {QPointF(3.2, 12.6), QPointF(7.4, 7.0), QPointF(12.8, 4.0)};
        p.setPen(QPen(alpha(c, 170), 3.4, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.setBrush(Qt::NoBrush);
        p.drawPolyline(QPolygonF({nodes[0], nodes[1], nodes[2]}));
        p.setPen(QPen(QColor(0x2b, 0x1d, 0x5c), 1.2));
        p.setBrush(c);
        for (const QPointF& n : nodes) p.drawEllipse(n, 2.1, 2.1);
    }
    else if (type == "character")
    {
        // a little head with a face
        const QColor ink(0x2b, 0x1d, 0x5c);
        p.setPen(QPen(ink, 1.2));
        p.setBrush(c);
        p.drawEllipse(QPointF(8, 8.4), 6.0, 5.6);
        p.setPen(Qt::NoPen);
        p.setBrush(ink);
        p.drawEllipse(QPointF(5.9, 7.4), 1.0, 1.25);
        p.drawEllipse(QPointF(10.1, 7.4), 1.0, 1.25);
        p.setBrush(Qt::NoBrush);
        p.setPen(QPen(ink, 1.1, Qt::SolidLine, Qt::RoundCap));
        p.drawArc(QRectF(5.6, 8.6, 4.8, 3.4), 200 * 16, 140 * 16);
    }
    else if (type == "feature")
    {
        // two rings with the stitches between them: the features of a feature model
        p.setBrush(Qt::NoBrush);
        p.setPen(QPen(alpha(c, 200), 1.1, Qt::SolidLine, Qt::RoundCap));
        for (int k = 0; k < 8; ++k)
        {
            const double a = kPi / 4 * k;
            p.drawLine(QPointF(8 + 3.8 * std::cos(a), 8 + 2.4 * std::sin(a)), QPointF(8 + 6.4 * std::cos(a), 8 + 4.2 * std::sin(a)));
        }
        p.setPen(QPen(c, 1.8));
        p.drawEllipse(QPointF(8, 8), 6.4, 4.2);
        p.drawEllipse(QPointF(8, 8), 3.8, 2.4);
    }
    else if (type == "operation")
    {
        // what is done to a model: a cog
        p.setPen(QPen(c, 2.3, Qt::SolidLine, Qt::RoundCap));
        for (int k = 0; k < 8; ++k)
        {
            const double a = kPi / 4 * k;
            p.drawLine(QPointF(8 + 5.3 * std::cos(a), 8 + 5.3 * std::sin(a)), QPointF(8 + 7.0 * std::cos(a), 8 + 7.0 * std::sin(a)));
        }
        p.setPen(QPen(c, 1.9));
        p.setBrush(Qt::NoBrush);
        p.drawEllipse(QPointF(8, 8), 3.9, 3.9);
    }
    else if (type == "shapes")
    {
        // a shape made with parameters, more than a primitive: a plate with a round hole through it
        QPainterPath plate;
        plate.addRoundedRect(QRectF(2.4, 2.4, 11.2, 11.2), 2.6, 2.6);
        QPainterPath hole;
        hole.addEllipse(QPointF(8, 8), 3.1, 3.1);
        p.setPen(QPen(c, 1.9, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.setBrush(alpha(c, 165));
        p.drawPath(plate.subtracted(hole));
        p.setBrush(Qt::NoBrush);
        p.drawEllipse(QPointF(8, 8), 3.1, 3.1);
    }
    else if (type == "block")
    {
        // a block of your own: a brick with a function's f on it
        p.setPen(QPen(c, 1.9, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.setBrush(alpha(c, 130));
        p.drawRoundedRect(QRectF(2.4, 3.4, 11.2, 9.2), 1.8, 1.8);
        QPainterPath f;
        f.moveTo(9.6, 5.4);
        f.quadTo(7.6, 4.9, 7.6, 7.0);
        f.lineTo(7.6, 11.0);
        f.moveTo(6.1, 8.2);
        f.lineTo(9.4, 8.2);
        p.setBrush(Qt::NoBrush);
        p.setPen(QPen(c.lighter(150), 1.4, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.drawPath(f);
    }
    else if (type == "python")
    {
        // plain code: a tile with the letters of the language
        p.setPen(QPen(c, 1.9));
        p.setBrush(alpha(c, 130));
        p.drawRoundedRect(QRectF(1.8, 2.8, 12.4, 10.4), 2.4, 2.4);
        QFont f = p.font();
        f.setPixelSize(8);
        f.setBold(true);
        p.setFont(f);
        p.setPen(c.lighter(150));
        p.drawText(QRectF(1.8, 2.8, 12.4, 10.4), Qt::AlignCenter, QStringLiteral("py"));
    }
    else
    {
        // a solid: a cube, lit from above
        const QPointF top(8, 1.8), ur(13.4, 4.9), lr(13.4, 11.1), bottom(8, 14.2), ll(2.6, 11.1), ul(2.6, 4.9), mid(8, 8);
        p.setPen(Qt::NoPen);
        p.setBrush(c.lighter(135));
        p.drawPolygon(QPolygonF({top, ur, mid, ul}));
        p.setBrush(c);
        p.drawPolygon(QPolygonF({ul, mid, bottom, ll}));
        p.setBrush(c.darker(135));
        p.drawPolygon(QPolygonF({ur, lr, bottom, mid}));
    }
}

// The mark of a custom block: a small badge at the lower right with a function's f
void drawBlockMark(QPainter& p)
{
    p.setPen(QPen(QColor(0x16, 0x4c, 0x5e), 1.6));
    p.setBrush(QColor(0xee, 0xe8, 0xd5));
    p.drawEllipse(QPointF(12.2, 12.2), 3.4, 3.4);
    QPainterPath f;
    f.moveTo(13.4, 10.0);
    f.quadTo(12.1, 9.6, 12.1, 11.0);
    f.lineTo(12.1, 14.4);
    f.moveTo(11.0, 11.9);
    f.lineTo(13.3, 11.9);
    p.setBrush(Qt::NoBrush);
    p.setPen(QPen(QColor(0x16, 0x4c, 0x5e), 1.05, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
    p.drawPath(f);
}

}   // anonymous namespace

QColor color(const QString& type)
{
    auto it = kinds().constFind(type);
    return it == kinds().constEnd() ? kinds()["solid"].color : it->color;
}

QString label(const QString& type)
{
    auto it = kinds().constFind(type);
    return it == kinds().constEnd() ? type : T(it->label);
}

QIcon icon(const QString& type, bool block)
{
    const QString key = type + (block ? "+block" : "");
    auto it = cache().constFind(key);
    if (it != cache().constEnd()) return *it;
    const QColor c = color(type);
    QIcon made = draw([&](QPainter& p) {
        drawKind(p, type, c);
        if (block) drawBlockMark(p);
    });
    cache().insert(key, made);
    return made;
}

void setKinds(const QJsonObject& given)
{
    bool changed = false;
    for (auto it = given.constBegin(); it != given.constEnd(); ++it)
    {
        const QJsonObject o = it.value().toObject();
        Kind& k = kinds()[it.key()];
        const QColor c(o["color"].toString());
        if (c.isValid() && c != k.color) { k.color = c; changed = true; }
        if (o.contains("label")) k.label = o["label"].toString();
    }
    if (changed) cache().clear();
}

}   // namespace TypeIcons
}   // namespace FielDev
