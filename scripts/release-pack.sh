#!/usr/bin/env bash
# Tag a pack release on main and push — rolls back locally on tag push failure.
#
# Usage:
#   ./scripts/release-pack.sh 1.1.0
#   ./scripts/release-pack.sh packs-v1.1.0
#   ./scripts/release-pack.sh 1.1.0 --dry-run
#   ./scripts/release-pack.sh 1.1.0 --wait

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DRY_RUN=false
WAIT_WORKFLOW=false
RAW_TAG=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --wait) WAIT_WORKFLOW=true ;;
    *)
      if [[ -z "$RAW_TAG" ]]; then
        RAW_TAG="$arg"
      else
        echo "Unexpected argument: $arg" >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$RAW_TAG" ]]; then
  echo "Usage: release-pack.sh {X.Y.Z|packs-vX.Y.Z} [--dry-run] [--wait]" >&2
  exit 1
fi

# shellcheck source=scripts/release-preflight.sh
source "$ROOT/scripts/release-preflight.sh"

TAG=""
VERSION=""
if [[ "$RAW_TAG" == packs-v* ]]; then
  TAG="$RAW_TAG"
  VERSION="${RAW_TAG#packs-v}"
else
  VERSION="$RAW_TAG"
  TAG="packs-v${RAW_TAG}"
fi
STATE="none"

rollback() {
  local code=$?
  [[ "$code" -eq 0 ]] && return 0
  if [[ "$DRY_RUN" == true ]]; then
    return "$code"
  fi
  if [[ "$STATE" == "tagged" ]]; then
    echo "" >&2
    echo "Pack release failed — deleting local tag ${TAG}." >&2
    git tag -d "$TAG" >/dev/null 2>&1 || true
  fi
  return "$code"
}

trap rollback EXIT

main() {
  cd "$ROOT"

  if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$ ]]; then
    echo "Pack version must be semver X.Y.Z (got: ${VERSION})" >&2
    exit 1
  fi

  echo "Preflight…"
  release_require_main_clean_synced
  release_require_ci_green "$RELEASE_SHA"

  local pack_count
  pack_count="$(find "$ROOT/packs" -mindepth 1 -maxdepth 1 -type d -exec test -f '{}/manifest.json' \; -print | wc -l)"
  if [[ "$pack_count" -eq 0 ]]; then
    echo "No packs with manifest.json under packs/" >&2
    exit 1
  fi

  release_require_tag_free "$TAG"

  echo ""
  echo "Pack release plan:"
  echo "  Tag:   $TAG"
  echo "  Packs: $pack_count directories"
  echo "  Commit: ${RELEASE_SHA:0:7}"

  if [[ "$DRY_RUN" == true ]]; then
    echo ""
    echo "Dry run — validating pack build…"
    chmod +x "$ROOT/scripts/build-pack-release.sh"
    "$ROOT/scripts/build-pack-release.sh" "$TAG"
    git checkout -- "$ROOT/packs/catalog.json"
    rm -rf "$ROOT/dist"
    echo "Dry run complete — no tag pushed."
    trap - EXIT
    exit 0
  fi

  git tag -a "$TAG" -m "Pack release ${VERSION}"
  STATE="tagged"

  if ! git push origin "$TAG"; then
    echo "Tag push failed for ${TAG}" >&2
    exit 1
  fi

  STATE="done"
  trap - EXIT
  echo ""
  echo "Pushed ${TAG} — workflow will build tarballs and sync packs/catalog.json."
  echo "https://github.com/${REPO}/actions/workflows/release.yml"

  if [[ "$WAIT_WORKFLOW" == true ]]; then
    release_wait_for_workflow "$TAG"
  fi
}

main
