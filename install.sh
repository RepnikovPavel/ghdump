#!/bin/sh
# ghdump installer: copies the script to a bin directory on PATH.
# Usage:
#   ./install.sh              # installs to ~/.local/bin
#   ./install.sh /some/dir    # installs to /some/dir
#   sudo ./install.sh /usr/local/bin   # system-wide
set -e

DEST="${1:-$HOME/.local/bin}"
SRC="$(dirname "$0")/dont_read_me_src/ghdump.py"

mkdir -p "$DEST"
cp "$SRC" "$DEST/ghdump"
chmod +x "$DEST/ghdump"
echo "installed: $DEST/ghdump"
case ":$PATH:" in
    *":$DEST:"*) ;;
    *) echo "note: $DEST is not on your PATH" ;;
esac
