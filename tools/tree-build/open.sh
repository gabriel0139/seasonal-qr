#!/bin/sh
# Open a season's diorama in the Blender UI for visual tweaking: npm run tree:open -- <season>
# Not headless, so finish() skips the slot cloud and the export: the committed assets are left alone.
set -e
season=${1:?usage: npm run tree:open -- <season>   (sakura, autumn, ...)}
script="$(dirname "$0")/$season.py"
[ -f "$script" ] || { echo "no season script $script" >&2; exit 1; }
exec "${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}" -P "$script"
