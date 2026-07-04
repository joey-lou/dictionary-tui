#!/usr/bin/env bash
# Tag the current main tip and push — triggers the app release workflow.
# Cargo.toml is updated by CI from the tag; no manual version bump needed.
#
# Usage:
#   ./scripts/release-app.sh 0.1.2
#   ./scripts/release-app.sh v0.1.2

set -euo pipefail

RAW="${1:?Usage: release-app.sh X.Y.Z}"
VERSION="${RAW#v}"
TAG="v${VERSION}"

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$ ]]; then
  echo "Version must be semver: X.Y.Z (got: $RAW)" >&2
  exit 1
fi

git fetch origin main
LOCAL="$(git rev-parse HEAD)"
MAIN="$(git rev-parse origin/main)"
if [[ "$LOCAL" != "$MAIN" ]]; then
  echo "Release tags must be created on the latest main tip." >&2
  echo "  HEAD: $LOCAL" >&2
  echo "  main: $MAIN" >&2
  exit 1
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag $TAG already exists" >&2
  exit 1
fi

CURRENT="$(grep -m1 '^version' Cargo.toml | sed -E 's/version *= *"([^"]+)".*/\1/')"
if [[ "$(printf '%s\n' "$VERSION" "$CURRENT" | sort -V | head -1)" == "$VERSION" && "$VERSION" != "$CURRENT" ]]; then
  echo "Refusing to release $TAG: Cargo.toml is already at $CURRENT" >&2
  exit 1
fi

git tag "$TAG"
git push origin "$TAG"
echo "Pushed $TAG — release workflow will build, publish, and sync Cargo.toml on main."
