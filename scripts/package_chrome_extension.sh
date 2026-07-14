#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXT_DIR="$ROOT_DIR/chrome-extension"
DIST_DIR="$ROOT_DIR/dist"

python3 -m json.tool "$EXT_DIR/manifest.json" >/dev/null
node --check "$EXT_DIR/popup.js" >/dev/null
node --check "$EXT_DIR/content.js" >/dev/null
node --check "$EXT_DIR/smart-cta.js" >/dev/null

VERSION="$(python3 - <<'PY'
import json
from pathlib import Path
manifest = json.loads(Path("chrome-extension/manifest.json").read_text())
print(manifest["version"])
PY
)"

mkdir -p "$DIST_DIR"
ZIP_PATH="$DIST_DIR/qsx-strategy-score-chrome-v${VERSION}.zip"
rm -f "$ZIP_PATH"

(
  cd "$EXT_DIR"
  zip -r "$ZIP_PATH" . \
    -x@.webstoreignore \
    -x ".webstoreignore"
)

echo "$ZIP_PATH"
