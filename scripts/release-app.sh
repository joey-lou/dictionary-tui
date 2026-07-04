#!/usr/bin/env bash
# Bump Cargo.toml, commit on main, tag, and push — rolls back locally on failure.
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
CARGO_LOCK="$ROOT/Cargo.lock"
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

START_SHA=""
BACKUP_TOML=""
BACKUP_LOCK=""
TAG=""
STATE="none"

rollback() {
  local code=$?
  [[ "$code" -eq 0 ]] && return 0
  if [[ "$DRY_RUN" == true ]]; then
    return "$code"
  fi

  echo "" >&2
  echo "Release failed — rolling back local changes." >&2
  case "$STATE" in
    tagged)
      git tag -d "$TAG" >/dev/null 2>&1 || true
      git reset --hard "$START_SHA"
      ;;
    committed)
      git reset --hard "$START_SHA"
      ;;
    bumped)
      cp "$BACKUP_TOML" "$CARGO_TOML"
      cp "$BACKUP_LOCK" "$CARGO_LOCK"
      ;;
  esac
  return "$code"
}

trap rollback EXIT

read_version() {
  grep -m1 '^version' "$CARGO_TOML" | sed -E 's/version *= *"([^"]+)".*/\1/'
}

set_version() {
  local version="$1"
  sed -i -E "s/^version = \".*\"/version = \"${version}\"/" "$CARGO_TOML"
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
  START_SHA="$(git rev-parse HEAD)"
  BACKUP_TOML="$(mktemp)"
  BACKUP_LOCK="$(mktemp)"
  cp "$CARGO_TOML" "$BACKUP_TOML"
  cp "$CARGO_LOCK" "$BACKUP_LOCK"

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

  echo ""
  echo "Release plan:"
  echo "  Cargo.toml: $current → $new_version"
  echo "  Tag:        $TAG"
  echo "  Commit:     ${START_SHA:0:7} → bump commit on main"

  if [[ "$DRY_RUN" == true ]]; then
    echo ""
    echo "Dry run only — no changes made."
    trap - EXIT
    exit 0
  fi

  set_version "$new_version"
  STATE="bumped"

  release_verify_crate_package "$new_version"

  git add "$CARGO_TOML" "$CARGO_LOCK"
  git commit -m "Bump version to ${new_version}."
  STATE="committed"

  local committed_version
  committed_version="$(read_version)"
  if [[ "$committed_version" != "$new_version" ]]; then
    echo "Internal error: committed version ${committed_version} != ${new_version}" >&2
    exit 1
  fi

  git tag -a "$TAG" -m "Release ${new_version}"
  STATE="tagged"

  git push origin main
  if ! git push origin "$TAG"; then
    echo "" >&2
    echo "Version bump is on origin/main but tag push failed." >&2
    echo "Fix the issue, then run: git push origin $TAG" >&2
    echo "To undo the remote bump (only if release workflow has not run):" >&2
    echo "  git revert HEAD && git push origin main" >&2
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
