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
#include <QDateTime>
#include <QFileOpenEvent>
#include <QThread>
#include <QTimer>
#include <QSettings>

#include <chrono>
#include <cstdio>
#include <cstdlib>

#include "fieldev/app.hpp"
#include "fieldev/args.hpp"
#include "fieldev/i18n.hpp"
#include "fieldev/icons.hpp"
#include "fieldev/theme.hpp"

namespace FielDev {

App::App(int& argc, char** argv)
    : QApplication(argc, argv)
{
    if (std::getenv("FIELDEV_TIMING"))
    {
        // How late the window's thread answers (the lag a user feels, whether it is busy or has no processor): a timer that should fire
        // every 10 ms says when it fired late
        auto* beat = new QTimer(this);
        beat->setInterval(10);
        connect(beat, &QTimer::timeout, this, [] {
            static auto last = std::chrono::steady_clock::now();
            const auto now = std::chrono::steady_clock::now();
            const double late = 1000.0 * std::chrono::duration<double>(now - last).count() - 10.0;
            last = now;
            if (late > 40)
                fprintf(stderr, "[at %lld ms] [gui] the window's thread answered %.0f ms late\n", (long long)(QDateTime::currentMSecsSinceEpoch() % 100000000), late);
        });
        beat->start();
    }
    // The Python package loads the kernel's libraries itself: point it at the ones
    // this program already uses, so both share their state (an import's progress,
    // the tessellation cache)
    if (!qEnvironmentVariableIsSet("FIELDEV_DIR"))
        qputenv("FIELDEV_DIR", QCoreApplication::applicationDirPath().toLocal8Bit());

    // The language of the program's own words: the setting, or the language of the computer (before any window is made)
    i18n::load();

    // The folder of the custom blocks that was chosen in Settings (the Python package reads it from the environment)
    if (!qEnvironmentVariableIsSet("FIELDEV_BLOCKS"))
    {
        const QString blocks = QSettings().value("blocks-folder").toString();
        if (!blocks.isEmpty()) qputenv("FIELDEV_BLOCKS", blocks.toLocal8Bit());
    }

    if (QFontDatabase::addApplicationFont(":/font/Inconsolata.otf") == -1) {
        std::cerr << "App: could not add application font";
    }

    Theme::apply(*this);
    setWindowIcon(Icons::logo(64));

    const Arguments args(this);
    if (args.app)
    {
        // A FielDev app: the form of its inputs, not the editor
        appWindow.reset(new AppWindow(args.appPath, args.appPresets, args.appRun));
        if (appWindow->isOpen()) appWindow->show();
        else QTimer::singleShot(0, this, &QCoreApplication::quit);
        return;
    }
    window.reset(new Window(args));
}

bool App::event(QEvent *event)
{
    if (event->type() == QEvent::FileOpen && window) {
        QFileOpenEvent *openEvent = static_cast<QFileOpenEvent*>(event);
        window->openFile(openEvent->file());
    }

    return QApplication::event(event);
}

bool App::notify(QObject* receiver, QEvent* e)
{
    // (with FIELDEV_TIMING: what kept the window's thread, and for how long)
    static const bool timing = std::getenv("FIELDEV_TIMING") != nullptr;
    static int depth = 0;
    if (!timing || QThread::currentThread() != thread()) return QApplication::notify(receiver, e);
    // (what the log says of the event is taken before it is delivered: the handler may delete the receiver -- a single-shot timer does -- and the event too)
    const int type = int(e->type());
    const char* cls = receiver ? receiver->metaObject()->className() : "?";
    const QByteArray name = receiver ? receiver->objectName().toUtf8() : QByteArray();
    const auto t0 = std::chrono::steady_clock::now();
    ++depth;
    const bool r = QApplication::notify(receiver, e);
    --depth;
    const double ms = 1000.0 * std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    if (ms > 30)
        fprintf(stderr, "[at %lld ms] [gui] %*sthe window's thread was busy %.0f ms with event %d of %s \"%s\"\n",
                (long long)(QDateTime::currentMSecsSinceEpoch() % 100000000), depth * 2, "", ms, type, cls, name.constData());
    return r;
}

}   // namespace FielDev
