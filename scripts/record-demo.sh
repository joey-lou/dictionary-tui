#!/usr/bin/env bash
# Record assets/demo.gif with VHS (run from Terminal.app).
#
#   brew install vhs
#   ./scripts/record-demo.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v vhs >/dev/null; then
  echo "Install VHS: brew install vhs" >&2
  exit 1
fi

rm -f assets/demo.gif
vhs scripts/demo.tape
echo "Wrote assets/demo.gif ($(du -h assets/demo.gif | cut -f1))"
