#!/usr/bin/env bash
# Set Cargo.toml [package].version from a v* release tag.
#
# Usage:
#   ./scripts/set-version-from-tag.sh v0.1.2
#   ./scripts/set-version-from-tag.sh 0.1.2

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:?Usage: set-version-from-tag.sh vX.Y.Z}"
VERSION="${TAG#v}"

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$ ]]; then
  echo "Tag must be semver: vX.Y.Z (got: $TAG)" >&2
  exit 1
fi

CARGO_TOML="$ROOT/Cargo.toml"
CURRENT="$(grep -m1 '^version' "$CARGO_TOML" | sed -E 's/version *= *"([^"]+)".*/\1/')"

if [[ "$VERSION" == "$CURRENT" ]]; then
  echo "Version already $VERSION in Cargo.toml" >&2
  exit 0
fi

if [[ "$(printf '%s\n' "$VERSION" "$CURRENT" | sort -V | head -1)" == "$VERSION" ]]; then
  echo "Refusing to downgrade: tag $VERSION < Cargo.toml $CURRENT" >&2
  exit 1
fi

sed -i -E "s/^version = \".*\"/version = \"${VERSION}\"/" "$CARGO_TOML"
echo "Set Cargo.toml version: $CURRENT → $VERSION"
