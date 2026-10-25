/*
FielDev: field-driven design

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
*/
#pragma once

#include <QColor>
#include <QFrame>
#include <QList>
#include <QString>

class QGridLayout;
class QLabel;
class QToolButton;
class QWidget;

namespace FielDev {

/*  One of the library's material presets (`material_presets()`): what the swatch of the card is drawn from -- the colour as a screen shows it, how metallic and how rough the material is,
    whether it is see-through, whether it glows  */
struct MaterialPreset
{
    QString name;
    QColor color = QColor(200, 200, 200);
    double metallic = 0.0;
    double roughness = 0.5;
    bool clear = false;
    bool glow = false;
};

/*
 *  The card of materials, in the viewport's top-right corner (as the symmetry's): a swatch for each preset of the library.  A swatch is dragged onto a model of the viewport or a
 *  row of the model tree and the model has that material; a click on a swatch gives the material to the models that are selected.
 */
class MaterialsPanel : public QFrame
{
    Q_OBJECT
public:
    explicit MaterialsPanel(QWidget* parent = nullptr);

    /*  The mime type a swatch is dragged as: its data is the name of the preset  */
    static QString mimeType();

    void setPresets(const QList<MaterialPreset>& presets);
    bool hasPresets() const { return m_have; }
    /*  Where the card sits: top-right, under the other cards  */
    void reposition() { place(); }

signals:
    void presetsRequested();                // (the card is shown and has none yet: the window fills it from the library)
    void applyRequested(QString preset);    // (a click on a swatch: the models that are selected get it)
    void closeRequested();

protected:
    bool eventFilter(QObject* obj, QEvent* e) override;
    void showEvent(QShowEvent* e) override;
    void place();

    QToolButton* m_header;
    QToolButton* m_close;
    QWidget* m_body;
    QGridLayout* m_grid;
    QLabel* m_hint;
    bool m_collapsed = false;
    bool m_have = false;
};

}   // namespace FielDev
