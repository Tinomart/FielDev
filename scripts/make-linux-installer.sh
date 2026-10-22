#!/usr/bin/env bash
# Makes the installer of the Linux package: ONE file that unpacks FielDev where the user wants it and puts it in the application menu.
#
#   scripts/make-linux-installer.sh <FielDev-version-linux-x64.tar.gz> <installer.run> [version]
#
# The installer is a shell script with the package appended to it (so it needs nothing but a shell, tar and gzip, which every system has).
# What the user does:
#
#   sh FielDev-0.6.0-linux-x64-installer.run                     installs for the current user into ~/.local/share/FielDev, with a menu entry
#                                                                and the command `fieldev` in ~/.local/bin (no administrator rights)
#   sudo sh FielDev-0.6.0-linux-x64-installer.run --system       installs for everyone into /opt/FielDev, the menu entry in /usr/share/applications
#   sh FielDev-0.6.0-linux-x64-installer.run --prefix DIR        installs into DIR
#   sh FielDev-0.6.0-linux-x64-installer.run --uninstall         removes what an installation made
#
# The installation is one folder (the package as it is) plus the menu entry and the command; `uninstall.sh` in the folder removes exactly those.
set -euo pipefail

ARCHIVE="${1:?usage: make-linux-installer.sh <package.tar.gz> <installer.run> [version]}"
OUTFILE="${2:?usage: make-linux-installer.sh <package.tar.gz> <installer.run> [version]}"
VERSION="${3:-}"
[ -f "$ARCHIVE" ] || { echo "no such package: $ARCHIVE"; exit 1; }

{
cat <<'HEADER'
#!/bin/sh
# FielDev installer. Run it with `sh <this file>` (options: --prefix DIR, --system, --no-menu, --uninstall, --help).
set -e

NAME=FielDev
PREFIX=""
SYSTEM=0
MENU=1
UNINSTALL=0
VERSION="@VERSION@"

usage() {
    cat <<EOF
FielDev $VERSION installer

  sh $0                       install for the current user (~/.local/share/FielDev, menu entry, command 'fieldev')
  sh $0 --system              install for everyone (/opt/FielDev; needs administrator rights: run it with sudo)
  sh $0 --prefix DIR          install into DIR
  sh $0 --no-menu             do not make the menu entry and the command
  sh $0 --uninstall           remove an installation made by this installer (with --system or --prefix: that one)

FielDev needs nothing else installed: Qt, Python and its libraries are in the package.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --prefix) PREFIX="$2"; shift ;;
        --prefix=*) PREFIX="${1#--prefix=}" ;;
        --system) SYSTEM=1 ;;
        --no-menu) MENU=0 ;;
        --uninstall) UNINSTALL=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option $1 (see --help)"; exit 2 ;;
    esac
    shift
done

if [ "$SYSTEM" = 1 ]; then
    [ -n "$PREFIX" ] || PREFIX=/opt/FielDev
    APPS=/usr/share/applications
    ICONS=/usr/share/icons/hicolor/256x256/apps
    BIN=/usr/local/bin
    if [ "$(id -u)" != 0 ]; then
        echo "A system-wide installation needs administrator rights: run  sudo sh $0 --system"
        exit 1
    fi
else
    DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
    [ -n "$PREFIX" ] || PREFIX="$DATA/FielDev"
    APPS="$DATA/applications"
    ICONS="$DATA/icons/hicolor/256x256/apps"
    BIN="$HOME/.local/bin"
fi
case "$PREFIX" in /*) ;; *) PREFIX="$(pwd)/$PREFIX" ;; esac

# --- uninstall
if [ "$UNINSTALL" = 1 ]; then
    if [ -x "$PREFIX/uninstall.sh" ]; then
        "$PREFIX/uninstall.sh"
    else
        echo "No FielDev installation made by this installer in $PREFIX"
        exit 1
    fi
    exit 0
fi

# --- a folder that is not ours is never touched
if [ -e "$PREFIX" ] && [ ! -f "$PREFIX/.fieldev-install" ]; then
    echo "$PREFIX exists and is not a FielDev installation: nothing was changed."
    echo "Choose another place with --prefix DIR."
    exit 1
fi

# --- where the package starts in this file
START=$(grep -a -n '^__FIELDEV_PACKAGE_BELOW__$' "$0" | head -n 1 | cut -d: -f1)
[ -n "$START" ] || { echo "this installer is damaged (no package in it)"; exit 1; }

echo "Installing FielDev $VERSION into $PREFIX ..."
OLD=""
if [ -d "$PREFIX" ]; then
    # (an upgrade: the old files are put aside, and removed when the new ones are in place)
    OLD="$PREFIX.old.$$"
    mv "$PREFIX" "$OLD"
fi
mkdir -p "$PREFIX"
if ! tail -n +"$((START + 1))" "$0" | tar -xzf - -C "$PREFIX" --strip-components=1; then
    echo "Unpacking failed: the installer file may be incomplete."
    rm -rf "$PREFIX"
    [ -n "$OLD" ] && mv "$OLD" "$PREFIX"
    exit 1
fi
[ -n "$OLD" ] && rm -rf "$OLD"
chmod +x "$PREFIX/FielDev" "$PREFIX/run.sh" 2>/dev/null || true
echo "$VERSION" > "$PREFIX/.fieldev-install"

# --- the menu entry, the icon and the command
if [ "$MENU" = 1 ]; then
    mkdir -p "$APPS" "$ICONS" "$BIN"
    ICON=fieldev
    if [ -f "$PREFIX/fieldev.png" ]; then
        cp -f "$PREFIX/fieldev.png" "$ICONS/fieldev.png"
    else
        ICON=""
    fi
    cat > "$APPS/fieldev.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=FielDev
GenericName=Field-driven design
Comment=CAD and simulation made of fields
Exec="$PREFIX/FielDev" %f
Terminal=false
Categories=Graphics;Engineering;Science;
StartupWMClass=FielDev
MimeType=application/x-fieldevapp;
EOF
    [ -z "$ICON" ] || echo "Icon=$ICON" >> "$APPS/fieldev.desktop"
    # (the file type of FielDev apps: a double click on a .fieldevapp opens it in its form)
    MIME="$(dirname "$APPS")/mime"
    mkdir -p "$MIME/packages"
    cat > "$MIME/packages/application-x-fieldevapp.xml" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-fieldevapp">
    <comment>FielDev app</comment>
    <glob pattern="*.fieldevapp"/>
    <icon name="fieldev"/>
  </mime-type>
</mime-info>
XML
    command -v update-mime-database >/dev/null 2>&1 && update-mime-database "$MIME" >/dev/null 2>&1 || true
    command -v xdg-mime >/dev/null 2>&1 && xdg-mime default fieldev.desktop application/x-fieldevapp >/dev/null 2>&1 || true
    ln -sf "$PREFIX/FielDev" "$BIN/fieldev"
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" >/dev/null 2>&1 || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t "$(dirname "$(dirname "$ICONS")")" >/dev/null 2>&1 || true
fi

# --- what removes it again: the folder, the menu entry, the command
cat > "$PREFIX/uninstall.sh" <<EOF
#!/bin/sh
# Removes the FielDev installation in $PREFIX and the menu entry and command that came with it.
[ -f "$PREFIX/.fieldev-install" ] || { echo "$PREFIX is not a FielDev installation"; exit 1; }
rm -f "$APPS/fieldev.desktop" "$ICONS/fieldev.png" "$(dirname "$APPS")/mime/packages/application-x-fieldevapp.xml"
[ "\$(readlink "$BIN/fieldev" 2>/dev/null)" = "$PREFIX/FielDev" ] && rm -f "$BIN/fieldev"
rm -rf "$PREFIX"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" >/dev/null 2>&1 || true
echo "FielDev was removed."
EOF
chmod +x "$PREFIX/uninstall.sh"

echo
if [ "$MENU" = 1 ]; then
    echo "Done. Start FielDev from the application menu, or with the command  fieldev  (or $PREFIX/FielDev)."
    case ":$PATH:" in *":$BIN:"*) ;; *) echo "($BIN is not in your PATH: add it to use the command, or start FielDev from the menu.)" ;; esac
else
    echo "Done. Start FielDev with  $PREFIX/FielDev"
fi
echo "To remove it:  $PREFIX/uninstall.sh"
exit 0
__FIELDEV_PACKAGE_BELOW__
HEADER
} | sed "s/@VERSION@/${VERSION:-unknown}/" > "$OUTFILE"

cat "$ARCHIVE" >> "$OUTFILE"
chmod +x "$OUTFILE"
echo "== installer: $OUTFILE ($(du -h "$OUTFILE" | cut -f1))"
