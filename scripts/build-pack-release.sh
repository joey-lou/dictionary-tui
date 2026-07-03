#!/usr/bin/env bash
# Build pack release tarballs and regenerate packs/catalog.json.
#
# Usage:
#   ./scripts/build-pack-release.sh [RELEASE_TAG]
#
# Example:
#   ./scripts/build-pack-release.sh packs-v1.0.0
#
# Outputs:
#   dist/<pack-id>.tar.gz
#   packs/catalog.json (updated URLs and checksums)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RELEASE_TAG="${1:-packs-v1.0.0}"
REPO="${GITHUB_REPOSITORY:-joey-lou/dictionary-tui}"
DIST="$ROOT/dist"
PACKS_DIR="$ROOT/packs"

mkdir -p "$DIST"

PACK_IDS=(webster1913-en xinhua-zh-zh cc-cedict)
PACK_NAMES=(
  "Webster's 1913"
  "新华字典 Xinhua (中中)"
  "CC-CEDICT (中英)"
)

entries=()
for i in "${!PACK_IDS[@]}"; do
  id="${PACK_IDS[$i]}"
  archive="$DIST/${id}.tar.gz"
  echo "Building $archive …"
  if tar --version 2>/dev/null | grep -qi gnu; then
    tar --sort=name --owner=0 --group=0 --mtime='@0' -czf "$archive" -C "$PACKS_DIR" "$id"
  else
    # BSD tar (macOS): best-effort; prefer running this script on Linux for releases.
    COPYFILE_DISABLE=1 tar -czf "$archive" -C "$PACKS_DIR" "$id"
  fi
  sha256="$(shasum -a 256 "$archive" | awk '{print $1}')"
  size="$(stat -f%z "$archive" 2>/dev/null || stat -c%s "$archive")"
  url="https://github.com/${REPO}/releases/download/${RELEASE_TAG}/${id}.tar.gz"
  name="${PACK_NAMES[$i]}"
  entries+=("    {
      \"id\": \"${id}\",
      \"name\": \"${name}\",
      \"url\": \"${url}\",
      \"sha256\": \"${sha256}\",
      \"size\": ${size}
    }")
  echo "  sha256=$sha256  size=$size"
done

catalog="$PACKS_DIR/catalog.json"
{
  echo "{"
  echo "  \"release_tag\": \"${RELEASE_TAG}\","
  echo "  \"repository\": \"${REPO}\","
  echo "  \"packs\": ["
  printf '%s,\n' "${entries[@]}" | sed '$ s/,$//'
  echo "  ]"
  echo "}"
} > "$catalog"

echo ""
echo "Wrote $catalog"
echo "Upload dist/*.tar.gz to GitHub Release ${RELEASE_TAG}"
