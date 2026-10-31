#!/usr/bin/env bash
# Set dictionary-tui crate version in Cargo.toml and Cargo.lock (release CI only).
#
#   ./scripts/set-crate-version.sh 0.1.2
#
# main keeps version = "0.0.0-dev"; tags drive real release versions in CI.
set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "usage: $0 VERSION" >&2
  exit 1
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$ ]]; then
  echo "invalid semver: $VERSION" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if command -v cargo-set-version >/dev/null 2>&1 || cargo set-version --help >/dev/null 2>&1; then
  cargo set-version "$VERSION"
else
  if [[ "$(uname)" == Darwin ]]; then
    sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" Cargo.toml
    sed -i '' "/^name = \"dictionary-tui\"$/,/^version = / s/^version = \".*\"/version = \"$VERSION\"/" Cargo.lock
  else
    sed -i "s/^version = \".*\"/version = \"$VERSION\"/" Cargo.toml
    sed -i "/^name = \"dictionary-tui\"$/,/^version = / s/^version = \".*\"/version = \"$VERSION\"/" Cargo.lock
  fi
fi

echo "Set crate version to $VERSION"
