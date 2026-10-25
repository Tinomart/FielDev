/*
FielDev: field-driven design

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
*/
#include <algorithm>

#include <QApplication>
#include <QDrag>
#include <QEvent>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QIcon>
#include <QLabel>
#include <QMimeData>
#include <QMouseEvent>
#include <QPainter>
#include <QPixmap>
#include <QRadialGradient>
#include <QToolButton>
#include <QVBoxLayout>

#include "fieldev/carddrag.hpp"
#include "fieldev/i18n.hpp"
#include "fieldev/materialspanel.hpp"

namespace FielDev {

namespace {

QColor mixed(const QColor& a, const QColor& b, double t)
{
    t = std::max(0.0, std::min(1.0, t));
    return QColor::fromRgbF(a.redF() * (1 - t) + b.redF() * t, a.greenF() * (1 - t) + b.greenF() * t, a.blueF() * (1 - t) + b.blueF() * t,
                            a.alphaF() * (1 - t) + b.alphaF() * t);
}

// A ball in the colour of the preset, lit from above left: a metal with a hard bright spot and a dark rim, a rough thing soft, glass see-through with a bright edge, a glowing one with a halo
QPixmap ballOf(const MaterialPreset& p, int size)
{
    QPixmap pm(size, size);
    pm.fill(Qt::transparent);
    QPainter g(&pm);
    g.setRenderHint(QPainter::Antialiasing, true);
    const QRectF r(3, 3, size - 6, size - 6);
    if (p.glow)
    {
        QRadialGradient halo(r.center(), size * 0.5);
        halo.setColorAt(0.55, QColor(255, 220, 140, 150));
        halo.setColorAt(1.0, QColor(255, 220, 140, 0));
        g.setPen(Qt::NoPen);
        g.setBrush(halo);
        g.drawEllipse(QRectF(0, 0, size, size));
    }
    const bool metal = p.metallic > 0.5;
    const double shine = metal ? 0.9 - 0.55 * p.roughness : 0.6 * (1.0 - p.roughness);
    QColor lit = mixed(p.color, Qt::white, shine);
    QColor body = p.color;
    QColor dark = mixed(p.color, Qt::black, metal ? 0.75 : 0.5);
    if (p.clear)
    {
        lit.setAlpha(150);
        body.setAlpha(110);
        dark.setAlpha(160);
    }
    QRadialGradient grad(r.center() + QPointF(-r.width() * 0.2, -r.height() * 0.22), r.width() * (metal ? 0.6 : 0.8));
    grad.setColorAt(0.0, lit);
    grad.setColorAt(metal ? 0.3 : 0.45, body);
    grad.setColorAt(1.0, dark);
    g.setPen(QPen(p.clear ? QColor(235, 245, 250, 200) : QColor(0, 0, 0, 90), 1.2));
    g.setBrush(grad);
    g.drawEllipse(r);
    return pm;
}

// A swatch: a ball and the name of the material.  Pulled, it is a drag of the name (what a model of the viewport or a row of the tree takes); clicked, it is the button of the card
class Swatch : public QToolButton
{
public:
    Swatch(const MaterialPreset& p, QWidget* parent) : QToolButton(parent), m_name(p.name), m_ball(ballOf(p, 40))
    {
        setObjectName("MaterialSwatch");
        setIcon(QIcon(m_ball));
        setIconSize(QSize(40, 40));
        setText(p.name);
        setToolButtonStyle(Qt::ToolButtonTextUnderIcon);
        setFixedSize(62, 66);
        setCursor(Qt::OpenHandCursor);
        setToolTip(T("%1 (%2 metal, %3 rough): drag it onto a model, or click it to give it to the models that are selected")
                       .arg(p.name, QString::number(p.metallic, 'f', 1), QString::number(p.roughness, 'f', 2)));
    }

protected:
    void mousePressEvent(QMouseEvent* e) override
    {
        m_press = e->pos();
        m_dragging = false;
        QToolButton::mousePressEvent(e);
    }
    void mouseMoveEvent(QMouseEvent* e) override
    {
        if ((e->buttons() & Qt::LeftButton) && !m_dragging && (e->pos() - m_press).manhattanLength() >= QApplication::startDragDistance())
        {
            m_dragging = true;
            setDown(false);
            auto drag = new QDrag(this);
            auto mime = new QMimeData;
            mime->setData(MaterialsPanel::mimeType(), m_name.toUtf8());
            mime->setText(m_name);
            drag->setMimeData(mime);
            drag->setPixmap(m_ball);
            drag->setHotSpot(QPoint(m_ball.width() / 2, m_ball.height() / 2));
            drag->exec(Qt::CopyAction);
            return;
        }
        QToolButton::mouseMoveEvent(e);
    }

private:
    QString m_name;
    QPixmap m_ball;
    QPoint m_press;
    bool m_dragging = false;
};

}   // namespace

QString MaterialsPanel::mimeType()
{
    return QStringLiteral("application/x-fielddev-material");
}

MaterialsPanel::MaterialsPanel(QWidget* parent)
    : QFrame(parent), m_header(new QToolButton), m_close(new QToolButton), m_body(new QWidget), m_grid(new QGridLayout), m_hint(new QLabel)
{
    setObjectName("MaterialsPanel");
    setAttribute(Qt::WA_StyledBackground, true);
    // (the look of the symmetry's card)
    setStyleSheet(
        "#MaterialsPanel { background: rgba(72, 116, 118, 222);"
        "  border: 1px solid rgba(147, 161, 161, 90); border-radius: 6px; }"
        "QLabel { color: #93a1a1; font-size: 8pt; }"
        "QToolButton#MaterialSwatch { color: #eee8d5; background: rgba(147, 161, 161, 22);"
        "  border: 1px solid rgba(147, 161, 161, 50); border-radius: 5px; padding: 2px; font-size: 7pt; }"
        "QToolButton#MaterialSwatch:hover { background: rgba(147, 161, 161, 70); border-color: rgba(238, 232, 213, 150); }"
        "QToolButton#MaterialSwatch:pressed { background: rgba(211, 54, 130, 120); }"
        "QToolButton#MaterialsHeader { color: #eee8d5; background: transparent; border: none; font-weight: bold;"
        "  font-size: 9pt; padding: 3px 4px; }"
        "QToolButton#MaterialsClose { color: #93a1a1; background: transparent; border: none;"
        "  padding: 2px 5px; font-size: 9pt; }"
        "QToolButton#MaterialsClose:hover { color: #eee8d5; }");

    m_header->setObjectName("MaterialsHeader");
    m_header->setText(QString(QChar(0x25be)) + "  " + T("Materials"));
    m_header->setCursor(Qt::PointingHandCursor);
    m_header->setToolTip(T("Collapse / expand"));
    m_close->setObjectName("MaterialsClose");
    m_close->setText(QString(QChar(0x2715)));
    m_close->setToolTip(T("Close the card (View > Materials brings it back)"));
    auto head = new QHBoxLayout;
    head->setContentsMargins(0, 0, 0, 0);
    head->setSpacing(4);
    head->addWidget(m_header);
    head->addStretch();
    head->addWidget(m_close);

    m_hint->setWordWrap(true);
    m_hint->setText(T("Drag a material onto a model, or click one to give it to what is selected."));
    m_grid->setContentsMargins(0, 0, 0, 0);
    m_grid->setSpacing(3);
    auto body = new QVBoxLayout(m_body);
    body->setContentsMargins(0, 0, 0, 0);
    body->setSpacing(4);
    body->addWidget(m_hint);
    body->addLayout(m_grid);

    auto layout = new QVBoxLayout(this);
    layout->setContentsMargins(7, 4, 7, 7);
    layout->setSpacing(2);
    layout->addLayout(head);
    layout->addWidget(m_body);
    setMinimumWidth(340);
    resize(350, 100);

    new CardController(this, "materials", m_header, QSize(300, 60));
    connect(m_header, &QToolButton::clicked, this, [this] {
        m_collapsed = !m_collapsed;
        m_body->setVisible(!m_collapsed);
        m_header->setText(QString(QChar(m_collapsed ? 0x25b8 : 0x25be)) + m_header->text().mid(1));
        CardController::collapse(this, m_collapsed, m_header->sizeHint().height() + 14);
        place();
    });
    connect(m_close, &QToolButton::clicked, this, &MaterialsPanel::closeRequested);
    if (parent) parent->installEventFilter(this);
}

void MaterialsPanel::setPresets(const QList<MaterialPreset>& presets)
{
    while (QLayoutItem* item = m_grid->takeAt(0))
    {
        delete item->widget();
        delete item;
    }
    const int columns = 5;
    int k = 0;
    for (const MaterialPreset& p : presets)
    {
        auto swatch = new Swatch(p, m_body);
        swatch->setProperty("preset", p.name);
        swatch->show();                     // (the card is shown already: a swatch made now is shown by the next turn of the event loop, after the card has been sized by what is in it)
        connect(swatch, &QToolButton::clicked, this, [this, name = p.name] { emit(applyRequested(name)); });
        m_grid->addWidget(swatch, k / columns, k % columns);
        ++k;
    }
    m_have = !presets.isEmpty();
    m_body->layout()->activate();
    layout()->activate();
    if (!CardController::sized(this)) resize(350, std::max(minimumSizeHint().height(), sizeHint().height()));
    place();
}

bool MaterialsPanel::eventFilter(QObject* obj, QEvent* e)
{
    if (obj == parentWidget() && e->type() == QEvent::Resize) place();
    return QFrame::eventFilter(obj, e);
}

void MaterialsPanel::showEvent(QShowEvent* e)
{
    QFrame::showEvent(e);
    if (!m_have) emit(presetsRequested());
    place();
}

void MaterialsPanel::place()
{
    if (!CardController::sized(this)) resize(350, std::max(minimumSizeHint().height(), sizeHint().height()));
    if (parentWidget() && !CardController::moved(this))
    {
        // Top-right, below the orientation triad -- and below the cards that are there too
        int top = 124;
        for (const char* name : {"SectionPanel", "WorkPlanePanel", "SymmetryPanel"})
        {
            if (auto other = parentWidget()->findChild<QWidget*>(name))
                if (other->isVisible()) top = std::max(top, other->geometry().bottom() + 8);
        }
        move(parentWidget()->width() - width() - 8, top);
    }
}

}   // namespace FielDev
