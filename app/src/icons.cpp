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
    // The mark (the same as the application's icon): a friendly block with a face, on a sunny tile
    QPixmap px(size * 2, size * 2);
    px.fill(Qt::transparent);
    QPainter p(&px);
    p.setRenderHint(QPainter::Antialiasing);
    p.scale(size * 2 / 24.0, size * 2 / 24.0);
    QLinearGradient sun(0, 0, 0, 24);
    sun.setColorAt(0, QColor(0xff, 0xd6, 0x66));
    sun.setColorAt(1, QColor(0xff, 0x6f, 0x91));
    p.setPen(Qt::NoPen);
    p.setBrush(sun);
    p.drawRoundedRect(QRectF(0.5, 0.5, 23, 23), 5.5, 5.5);
    const QColor ink(0x2b, 0x1d, 0x5c);
    p.setPen(QPen(ink, 0.7, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin));
    QPolygonF side, top;
    side << QPointF(17.8, 10.3) << QPointF(20.8, 7.3) << QPointF(20.8, 17.9) << QPointF(17.8, 20.9);
    top << QPointF(7.0, 10.3) << QPointF(17.8, 10.3) << QPointF(20.8, 7.3) << QPointF(10.0, 7.3);
    p.setBrush(QColor(0x1f, 0x9a, 0x96));
    p.drawPolygon(side);
    p.setBrush(QColor(0x8f, 0xf0, 0xd8));
    p.drawPolygon(top);
    p.setBrush(QColor(0x2e, 0xc4, 0xb6));
    p.drawRect(QRectF(7.0, 10.3, 10.8, 10.6));
    // (the face)
    p.setPen(Qt::NoPen);
    p.setBrush(Qt::white);
    p.drawEllipse(QPointF(10.2, 14.2), 1.5, 1.75);
    p.drawEllipse(QPointF(15.0, 14.2), 1.5, 1.75);
    p.setBrush(ink);
    p.drawEllipse(QPointF(10.4, 14.5), 0.75, 0.9);
    p.drawEllipse(QPointF(15.2, 14.5), 0.75, 0.9);
    p.setBrush(Qt::NoBrush);
    p.setPen(QPen(ink, 0.55, Qt::SolidLine, Qt::RoundCap));
    p.drawArc(QRectF(10.6, 15.2, 3.6, 2.8), 200 * 16, 140 * 16);
    p.end();
    px.setDevicePixelRatio(2);
    return QIcon(px);
}

}   // namespace Icons
}   // namespace FielDev
