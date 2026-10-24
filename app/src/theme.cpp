/*
FielDev: field-driven design

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
*/
#include <QApplication>
#include <QPalette>
#include <QStyleFactory>

#include "fieldev/i18n.hpp"
#include "fieldev/theme.hpp"

namespace FielDev {

const QColor Theme::chrome("#e4f4f2");
const QColor Theme::surface("#ffffff");
const QColor Theme::paper("#f8fdfc");
const QColor Theme::gutter("#e9f6f4");
const QColor Theme::border("#b9dcd7");
const QColor Theme::text("#23484f");
const QColor Theme::muted("#5f8a90");
const QColor Theme::accent("#2fb0a8");

void Theme::apply(QApplication& app)
{
    app.setStyle(QStyleFactory::create("Fusion"));

    QPalette p;
    p.setColor(QPalette::Window, chrome);
    p.setColor(QPalette::WindowText, text);
    p.setColor(QPalette::Base, paper);
    p.setColor(QPalette::AlternateBase, gutter);
    p.setColor(QPalette::Text, text);
    p.setColor(QPalette::Button, surface);
    p.setColor(QPalette::ButtonText, text);
    p.setColor(QPalette::BrightText, QColor("#ffffff"));
    p.setColor(QPalette::Highlight, accent);
    p.setColor(QPalette::HighlightedText, QColor("#ffffff"));
    p.setColor(QPalette::ToolTipBase, QColor("#fff1e4"));
    p.setColor(QPalette::ToolTipText, QColor("#23484f"));
    p.setColor(QPalette::Mid, muted);
    p.setColor(QPalette::Link, accent);
    p.setColor(QPalette::Disabled, QPalette::Text, QColor("#a7b0b4"));
    p.setColor(QPalette::Disabled, QPalette::WindowText, QColor("#a7b0b4"));
    p.setColor(QPalette::Disabled, QPalette::ButtonText, QColor("#a7b0b4"));
    app.setPalette(p);

    QPalette dark = p;
    dark.setColor(QPalette::Window, QColor("#1f8a8f"));
    dark.setColor(QPalette::Base, QColor("#1f8a8f"));
    dark.setColor(QPalette::WindowText, QColor("#eee8d5"));
    dark.setColor(QPalette::Text, QColor("#eee8d5"));
    dark.setColor(QPalette::ButtonText, QColor("#eee8d5"));
    dark.setColor(QPalette::Disabled, QPalette::Text, QColor("#586e75"));
    dark.setColor(QPalette::Disabled, QPalette::WindowText, QColor("#586e75"));
    dark.setColor(QPalette::Disabled, QPalette::ButtonText, QColor("#586e75"));
    app.setPalette(dark, "QMenu");
    app.setPalette(dark, "QMenuBar");
    app.setPalette(dark, "QStatusBar");

    // (the cards floating in the viewport set their own dark styles; these are the rest)
    app.setStyleSheet(QString(
        "QMenuBar { background: #1f8a8f; color: #eee8d5; border: none; border-bottom: 1px solid rgba(147, 161, 161, 70);"
        "  padding: 1px 8px; font-size: 10pt; }"
        "QMenuBar::item { padding: 5px 12px; margin: 1px 1px; border-radius: 6px; background: transparent; }"
        "QMenuBar::item:selected { background: rgba(255, 255, 255, 60); }"
        "QMenuBar::item:pressed { background: rgba(255, 176, 128, 235); color: #2b1d16; }"
        "QWidget#TopIcons { background: transparent; }"
        "QToolButton#TopButton { border: none; border-radius: 6px; background: transparent; }"
        "QToolButton#TopButton:hover { background: rgba(255, 255, 255, 60); }"
        "QToolButton#TopButton:pressed { background: rgba(255, 176, 128, 235); }"
        "QToolButton#TopArrow { border: none; border-radius: 5px; background: transparent; }"
        "QToolButton#TopArrow:hover { background: rgba(255, 255, 255, 60); }"
        "QToolButton#TopArrow:pressed { background: rgba(255, 176, 128, 235); }"
        "QFrame#TopDivider { color: rgba(147, 161, 161, 80); }"
        "QMenu { background: #1f8a8f; color: #eee8d5; border: 1px solid rgba(147, 161, 161, 100); padding: 4px 0px;"
        "  font-size: 10pt; }"
        "QMenu::item { padding: 6px 30px 6px 26px; margin: 0px 4px; border-radius: 4px; }"
        "QMenu::item:selected { background: rgba(255, 176, 128, 235); color: #2b1d16; }"
        "QMenu::item:disabled { color: #586e75; }"
        "QMenu::separator { height: 1px; background: rgba(147, 161, 161, 70); margin: 4px 10px; }"
        "QStatusBar { background: #1f8a8f; color: #eee8d5; border-top: 1px solid rgba(147, 161, 161, 70); }"
        "QStatusBar::item { border: none; }"
        "QSplitter::handle { background: %2; }"
        "QSplitter::handle:horizontal { width: 1px; }"
        "QSplitter::handle:vertical { height: 1px; }"
        "QToolTip { background-color: #fff1e4; color: #23484f; border: 1px solid #ffb48a; padding: 4px 7px; }"
        "QDialog, QMessageBox { background: %6; }"
        "QPushButton { background: %1; color: %3; border: 1px solid #bcdcd8; border-radius: 5px; padding: 5px 16px; }"
        "QPushButton:hover { border-color: %4; }"
        "QPushButton:pressed { background: #dff4f1; }"
        "QPushButton:default { border-color: %4; }"
        "QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: %1; color: %3; border: 1px solid #bcdcd8;"
        "  border-radius: 4px; padding: 3px 6px; selection-background-color: %4; }"
        "QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: %4; }"
        // (the list that opens from a drop-down in a light window: it took the dark palette of the menus -- #1f8a8f -- under the dark text of the window, and five of the six kinds of the primitives manager could not be read.
        // Here it is the window's own scheme: white, grey border, dark text, the blue of the accent on the item under the cursor.  The drop-downs of the dark cards in the viewport are not in a dialog and keep their own)
        "QDialog QComboBox QAbstractItemView, QDialog QComboBoxPrivateContainer { background: %1; color: %3; border: 1px solid #bcdcd8;"
        "  selection-background-color: %4; selection-color: #ffffff; outline: 0; }"
        "QPlainTextEdit QScrollBar:vertical, QTextBrowser QScrollBar:vertical { background: transparent; width: 11px; margin: 0; }"
        "QPlainTextEdit QScrollBar::handle:vertical, QTextBrowser QScrollBar::handle:vertical {"
        "  background: #bfe3df; border-radius: 4px; min-height: 28px; margin: 2px; }"
        "QPlainTextEdit QScrollBar::handle:vertical:hover, QTextBrowser QScrollBar::handle:vertical:hover { background: #9fd3ce; }"
        "QPlainTextEdit QScrollBar::add-line:vertical, QPlainTextEdit QScrollBar::sub-line:vertical,"
        "QTextBrowser QScrollBar::add-line:vertical, QTextBrowser QScrollBar::sub-line:vertical { height: 0; }"
        "QPlainTextEdit QScrollBar:horizontal { background: transparent; height: 11px; margin: 0; }"
        "QPlainTextEdit QScrollBar::handle:horizontal { background: #bfe3df; border-radius: 4px; min-width: 28px; margin: 2px; }"
        "QPlainTextEdit QScrollBar::add-line:horizontal, QPlainTextEdit QScrollBar::sub-line:horizontal { width: 0; }")
        .arg(surface.name(), border.name(), text.name(), accent.name(), chrome.name()));   // (%6 is the fifth: markers are filled in order)
}

}   // namespace FielDev
