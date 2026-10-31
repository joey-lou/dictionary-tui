#!/usr/bin/env bash
# Tag the next app release from the latest v* tag and push it.
# Cargo.toml stays at 0.0.0-dev; CI writes the tag version before build/publish.
#
# Usage:
#   ./scripts/release-app.sh patch
#   ./scripts/release-app.sh minor
#   ./scripts/release-app.sh major
#   ./scripts/release-app.sh 0.2.0
#   ./scripts/release-app.sh patch --dry-run
#   ./scripts/release-app.sh patch --wait   # watch Release workflow after push

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CARGO_TOML="$ROOT/Cargo.toml"
DRY_RUN=false
WAIT_WORKFLOW=false
BUMP_KIND=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --wait) WAIT_WORKFLOW=true ;;
    patch|minor|major) BUMP_KIND="$arg" ;;
    *)
      if [[ -z "$BUMP_KIND" ]]; then
        BUMP_KIND="$arg"
      else
        echo "Unexpected argument: $arg" >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$BUMP_KIND" ]]; then
  echo "Usage: release-app.sh {patch|minor|major|X.Y.Z} [--dry-run] [--wait]" >&2
  exit 1
fi

# shellcheck source=scripts/release-preflight.sh
source "$ROOT/scripts/release-preflight.sh"

TAG=""
STATE="none"

rollback() {
  local code=$?
  [[ "$code" -eq 0 ]] && return 0
  if [[ "$DRY_RUN" == true ]]; then
    return "$code"
  fi

  echo "" >&2
  echo "Release failed — rolling back the local tag." >&2
  if [[ "$STATE" == "tagged" ]]; then
    git tag -d "$TAG" >/dev/null 2>&1 || true
  fi
  return "$code"
}

trap rollback EXIT

read_version() {
  local tag
  tag="$(git tag -l 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -1)"
  if [[ -z "$tag" ]]; then
    echo "No v* release tag found to bump" >&2
    exit 1
  fi
  echo "${tag#v}"
}

crate_version() {
  grep -m1 '^version' "$CARGO_TOML" | sed -E 's/version *= *"([^"]+)".*/\1/'
}

bump_version() {
  local current="$1" kind="$2"
  local base="${current%%-*}"
  local suffix=""
  if [[ "$current" == *-* ]]; then
    suffix="-${current#*-}"
  fi

  IFS=. read -r major minor patch <<< "$base"
  major="${major:-0}"
  minor="${minor:-0}"
  patch="${patch:-0}"

  case "$kind" in
    patch) patch=$((patch + 1)) ;;
    minor) minor=$((minor + 1)); patch=0 ;;
    major) major=$((major + 1)); minor=0; patch=0 ;;
    *)
      if [[ ! "$kind" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$ ]]; then
        echo "Version must be patch, minor, major, or semver X.Y.Z (got: $kind)" >&2
        exit 1
      fi
      if [[ "$(printf '%s\n' "$kind" "$current" | sort -V | head -1)" == "$kind" && "$kind" != "$current" ]]; then
        echo "Refusing to downgrade: $kind < $current" >&2
        exit 1
      fi
      if [[ "$kind" == "$current" ]]; then
        echo "Version already $current in Cargo.toml" >&2
        exit 1
      fi
      echo "$kind"
      return
      ;;
  esac

  echo "${major}.${minor}.${patch}${suffix}"
}

main() {
  cd "$ROOT"

  echo "Preflight…"
  release_require_main_clean_synced
  release_require_rust_toolchain
  release_require_ci_green "$RELEASE_SHA"

  local current new_version
  current="$(read_version)"
  new_version="$(bump_version "$current" "$BUMP_KIND")"
  TAG="v${new_version}"

  release_require_tag_free "$TAG"
  release_require_crates_io_version_free "$new_version"
  release_run_cargo_checks
  release_verify_crate_package "$(crate_version)"

  echo ""
  echo "Release plan:"
  echo "  Latest tag: v${current} → ${TAG}"
  echo "  Cargo.toml stays at $(crate_version); CI sets ${new_version} from the tag"

  if [[ "$DRY_RUN" == true ]]; then
    echo ""
    echo "Dry run only — no changes made."
    trap - EXIT
    exit 0
  fi

  git tag -a "$TAG" -m "Release ${new_version}"
  STATE="tagged"

  if ! git push origin "$TAG"; then
    echo "Tag push failed. The local tag was left in place; delete it with: git tag -d $TAG" >&2
    trap - EXIT
    exit 1
  fi

  STATE="done"
  trap - EXIT
  echo ""
  echo "Released $TAG — workflow will build binaries and publish to crates.io."
  echo "https://github.com/${REPO}/actions/workflows/release.yml"

  if [[ "$WAIT_WORKFLOW" == true ]]; then
    release_wait_for_workflow "$TAG"
  fi
}

main
