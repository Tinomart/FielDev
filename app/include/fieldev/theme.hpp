/*
FielDev: field-driven design

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
*/
#pragma once
#include <QColor>
#include <QString>

class QApplication;

namespace FielDev {

/*
 *  The look of the application: playful, not serious.  The window around the viewport is light --
 *  white bars, a pale lavender background, deep indigo text -- and the cards floating in it
 *  (model tree, section card, legends) are deep indigo; the viewport is a violet sky with the
 *  model in front of it.
 */
namespace Theme
{
    extern const QColor chrome;      // window background, between the bars
    extern const QColor surface;     // bars, menus, dialogs' fields
    extern const QColor paper;       // the editor
    extern const QColor gutter;      // the editor's line-number column
    extern const QColor border;      // hairlines
    extern const QColor text;        // text on light
    extern const QColor muted;       // secondary text on light
    extern const QColor accent;      // selection, focus

    /*  Fusion style, the light palette and the application's style sheet  */
    void apply(QApplication& app);
}

}   // namespace FielDev
