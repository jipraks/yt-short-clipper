#!/usr/bin/env bash
set -e

TARGET_TRIPLE="x86_64-pc-windows-msvc"
ROOT="$(realpath "$(dirname "$0")/..")"
SPEC="$ROOT/build/spec/sidecar.spec"
BINARY_DIR="$ROOT/src-tauri/binaries"
WORK_DIR="$ROOT/build/sidecar"
SPEC_DIR="$ROOT/build/spec"
NAME="ytclip-sidecar-$TARGET_TRIPLE"

mkdir -p "$BINARY_DIR" "$WORK_DIR" "$SPEC_DIR"

/opt/hermes/.venv/bin/python -m PyInstaller --clean --noconfirm --distpath "$BINARY_DIR" --workpath "$WORK_DIR" "$SPEC"

EXE="$BINARY_DIR/$NAME"
if [[ ! -f "$EXE" ]]; then
    echo "Sidecar binary was not created: $EXE" >&2
    exit 1
fi

echo "$EXE"