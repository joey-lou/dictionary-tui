#!/usr/bin/env bash
# Bump Cargo.toml, commit on main, tag, and push — rolls back locally on failure.
#
# Usage:
#   ./scripts/release-app.sh patch
#   ./scripts/release-app.sh minor
#   ./scripts/release-app.sh major
#   ./scripts/release-app.sh 0.2.0
#   ./scripts/release-app.sh patch --dry-run

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CARGO_TOML="$ROOT/Cargo.toml"
DRY_RUN=false
BUMP_KIND=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
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
  echo "Usage: release-app.sh {patch|minor|major|X.Y.Z} [--dry-run]" >&2
  exit 1
fi

START_SHA=""
BACKUP=""
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
      cp "$BACKUP" "$CARGO_TOML"
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

preflight() {
  if [[ "$(git branch --show-current)" != "main" ]]; then
    echo "Must be on main (current: $(git branch --show-current))" >&2
    exit 1
  fi

  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Working tree must be clean before releasing" >&2
    git status --short >&2
    exit 1
  fi

  git fetch origin main
  local local_sha remote_sha
  local_sha="$(git rev-parse HEAD)"
  remote_sha="$(git rev-parse origin/main)"
  if [[ "$local_sha" != "$remote_sha" ]]; then
    echo "main must match origin/main before releasing" >&2
    echo "  HEAD:   $local_sha" >&2
    echo "  origin: $remote_sha" >&2
    exit 1
  fi

  if ! command -v cargo >/dev/null 2>&1; then
    echo "cargo not found in PATH" >&2
    exit 1
  fi

  echo "Running preflight checks…"
  (cd "$ROOT" && cargo fmt -- --check)
  (cd "$ROOT" && cargo clippy -- -D warnings)
  (cd "$ROOT" && cargo test)
}

main() {
  cd "$ROOT"
  START_SHA="$(git rev-parse HEAD)"
  BACKUP="$(mktemp)"
  cp "$CARGO_TOML" "$BACKUP"

  preflight

  local current new_version
  current="$(read_version)"
  new_version="$(bump_version "$current" "$BUMP_KIND")"
  TAG="v${new_version}"

  if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "Tag $TAG already exists" >&2
    exit 1
  fi

  echo ""
  echo "Release plan:"
  echo "  Cargo.toml: $current → $new_version"
  echo "  Tag:        $TAG"
  echo "  Commit:     $START_SHA → new bump commit on main"

  if [[ "$DRY_RUN" == true ]]; then
    echo ""
    echo "Dry run only — no changes made."
    trap - EXIT
    exit 0
  fi

  set_version "$new_version"
  STATE="bumped"

  (cd "$ROOT" && cargo package --allow-dirty --quiet)
  local size
  size="$(stat -c%s "$ROOT"/target/package/dictionary-tui-*.crate)"
  if [[ "$size" -ge 10485760 ]]; then
    echo "Crate too large for crates.io: $size bytes" >&2
    exit 1
  fi

  git add "$CARGO_TOML" Cargo.lock
  git commit -m "Bump version to ${new_version}."
  STATE="committed"

  git tag "$TAG"
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
}

main
