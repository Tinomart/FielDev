/*
FielDev: field-driven design

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
*/
#include <QLinearGradient>
#include <QPainter>
#include <QPainterPath>
#include <QPixmap>
#include <cmath>
#include <functional>

#include "fieldev/icons.hpp"

namespace FielDev {
namespace Icons {

namespace {

const QColor kInk(0xe4, 0xde, 0xcb);        // (cream: they sit on the dark top dock)
const QColor kAccent(0xff, 0xc9, 0x3c);       // (sunshine)

// Drawn on a 24 x 24 grid at 3x, so it stays sharp on any screen
QIcon make(std::function<void(QPainter&)> draw)
{
    QIcon icon;
    for (int pass = 0; pass < 2; ++pass)
    {
        QPixmap px(72, 72);
        px.fill(Qt::transparent);
        QPainter p(&px);
        p.setRenderHint(QPainter::Antialiasing);
        p.scale(3, 3);
        if (pass == 1) p.setOpacity(0.35);
        draw(p);
        p.end();
        px.setDevicePixelRatio(3);
        icon.addPixmap(px, pass == 0 ? QIcon::Normal : QIcon::Disabled);
    }
    return icon;
}

QPen ink(double w = 1.6)
{
    return QPen(kInk, w, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin);
}

}   // namespace

QIcon newFile()
{
    return make([](QPainter& p) {
        p.setPen(QPen(QColor(0xff, 0xff, 0xff), 2.2, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.drawLine(QPointF(12, 5), QPointF(12, 19));
        p.drawLine(QPointF(5, 12), QPointF(19, 12));
    });
}

QIcon open()
{
    return make([](QPainter& p) {
        p.setPen(ink());
        QPainterPath f;
        f.moveTo(3.5, 7.5);
        f.lineTo(3.5, 18.5);
        f.lineTo(20.5, 18.5);
        f.lineTo(20.5, 9);
        f.lineTo(11, 9);
        f.lineTo(9.3, 6.5);
        f.lineTo(3.5, 6.5);
        f.closeSubpath();
        QColor tint = kAccent;
        tint.setAlpha(45);
        p.setBrush(tint);
        p.drawPath(f);
    });
}

QIcon importFile()
{
    return make([](QPainter& p) {
        p.setPen(ink());
        QPainterPath tray;
        tray.moveTo(4, 14);
        tray.lineTo(4, 19.5);
        tray.lineTo(20, 19.5);
        tray.lineTo(20, 14);
        p.drawPath(tray);
        p.setPen(QPen(kAccent, 1.8, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.drawLine(QPointF(12, 3.5), QPointF(12, 14));
        p.drawLine(QPointF(7.8, 9.8), QPointF(12, 14));
        p.drawLine(QPointF(16.2, 9.8), QPointF(12, 14));
    });
}

QIcon dropArrow()
{
    return make([](QPainter& p) {
        p.setPen(QPen(kInk, 2.4, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
        p.drawLine(QPointF(7, 9.5), QPointF(12, 14.5));
        p.drawLine(QPointF(17, 9.5), QPointF(12, 14.5));
    });
}

QIcon logo(int size)
{
    // The mark (the same as the application's icon): the F of the field lines, bold and playful -- a cream F that leans forward, two thick bands of peach round it like the contour lines of a
    // field, on a teal tile.  Bold on purpose: it is looked at 16 pixels wide
    QPixmap px(size * 2, size * 2);
    px.fill(Qt::transparent);
    QPainter p(&px);
    p.setRenderHint(QPainter::Antialiasing);
    p.scale(size * 2 / 24.0, size * 2 / 24.0);
    QPainterPath tile;
    tile.addRoundedRect(QRectF(0.5, 0.5, 23, 23), 5.5, 5.5);
    QLinearGradient bg(0, 0, 24, 24);
    bg.setColorAt(0, QColor(0x9c, 0xee, 0xe2));
    bg.setColorAt(1, QColor(0x2a, 0xae, 0xae));
    p.fillPath(tile, bg);
    p.setClipPath(tile);
    // (the F: a stem and two arms, each a rounded bar; a grown copy of the three is a contour line of the field round it)
    const QRectF parts[3] = {QRectF(6.9, 4.4, 5.1, 15.2), QRectF(6.9, 4.4, 10.7, 4.1), QRectF(6.9, 10.7, 8.9, 3.9)};
    const auto grown = [&](double d) {
        QPainterPath path;
        for (const QRectF& r : parts) path.addRoundedRect(r.adjusted(-d, -d, d, d), 1.7 + d, 1.7 + d);
        return path.simplified();
    };
    p.save();
    p.translate(12, 12);
    p.rotate(6);
    p.translate(-12, -12);
    p.fillPath(grown(2.35 + 1.45).subtracted(grown(2.35)), QColor(255, 214, 176));
    p.fillPath(grown(5.15 + 1.45).subtracted(grown(5.15)), QColor(255, 170, 122));
    const QColor ink(0x12, 0x45, 0x52);
    p.fillPath(grown(0.55), ink);
    p.fillPath(grown(0.0), QColor(255, 248, 240));
    p.restore();
    // (a sparkle at the top right)
    QPolygonF star;
    for (int k = 0; k < 8; ++k)
    {
        const double a = M_PI / 4 * k, r = k % 2 == 0 ? 1.9 : 0.5;
        star << QPointF(19.6 + r * std::cos(a), 4.6 + r * std::sin(a));
    }
    p.setClipping(false);
    p.setPen(Qt::NoPen);
    p.setBrush(QColor(255, 255, 255, 245));
    p.drawPolygon(star);
    p.end();
    px.setDevicePixelRatio(2);
    return QIcon(px);
}

}   // namespace Icons
}   // namespace FielDev
