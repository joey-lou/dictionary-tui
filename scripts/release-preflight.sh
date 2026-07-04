#!/usr/bin/env bash
# Shared release preflight checks. Sourced by release-app.sh / release-pack.sh.
#
# Expects ROOT to be set to the repo root before sourcing.

set -euo pipefail

: "${ROOT:?ROOT must be set before sourcing release-preflight.sh}"

REPO="${GITHUB_REPOSITORY:-joey-lou/dictionary-tui}"
CRATE_NAME="${CRATE_NAME:-dictionary-tui}"
MIN_RUST_VERSION="${MIN_RUST_VERSION:-1.88}"

release_require_main_clean_synced() {
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
  RELEASE_SHA="$local_sha"
}

release_require_rust_toolchain() {
  if ! command -v cargo >/dev/null 2>&1; then
    echo "cargo not found in PATH (install Rust ≥ ${MIN_RUST_VERSION})" >&2
    exit 1
  fi
  if ! command -v rustc >/dev/null 2>&1; then
    echo "rustc not found in PATH" >&2
    exit 1
  fi

  local rustc_version
  rustc_version="$(rustc --version | awk '{print $2}')"
  if [[ "$(printf '%s\n' "$rustc_version" "$MIN_RUST_VERSION" | sort -V | head -1)" != "$MIN_RUST_VERSION" ]]; then
    echo "Rust ${MIN_RUST_VERSION}+ required (found ${rustc_version})" >&2
    echo "Run: rustup update stable && rustup default stable" >&2
    exit 1
  fi

  for component in rustfmt clippy; do
    if ! rustup component list --installed 2>/dev/null | grep -q "^${component}-"; then
      echo "Missing rustup component: ${component} (run: rustup component add ${component})" >&2
      exit 1
    fi
  done
}

release_require_ci_green() {
  local sha="${1:?commit sha required}"
  echo "Checking CI status on ${sha:0:7}…"

  if command -v gh >/dev/null 2>&1; then
    local conclusion
    conclusion="$(gh api "repos/${REPO}/commits/${sha}/check-runs" \
      --jq '[.check_runs[] | select(.name != null) | .conclusion] | if length == 0 then "missing" else (if (map(select(. != "success" and . != "skipped")) | length) == 0 then "success" else "failure" end) end' \
      2>/dev/null || echo "unknown")"
    if [[ "$conclusion" != "success" ]]; then
      echo "GitHub CI is not green on this commit (state: ${conclusion})" >&2
      echo "See: https://github.com/${REPO}/actions" >&2
      exit 1
    fi
    echo "  CI: success (gh)"
    return
  fi

  local state
  state="$(curl -sf "https://api.github.com/repos/${REPO}/commits/${sha}/status" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('state','unknown'))" \
    2>/dev/null || echo "unknown")"
  if [[ "$state" != "success" ]]; then
    echo "GitHub CI is not green on this commit (state: ${state})" >&2
    echo "Install gh for richer checks, or verify: https://github.com/${REPO}/actions" >&2
    exit 1
  fi
  echo "  CI: success"
}

release_require_tag_free() {
  local tag="$1"
  if git rev-parse "$tag" >/dev/null 2>&1; then
    echo "Tag $tag already exists locally" >&2
    exit 1
  fi
  if git ls-remote --exit-code --tags origin "$tag" >/dev/null 2>&1; then
    echo "Tag $tag already exists on origin" >&2
    exit 1
  fi
}

release_require_crates_io_version_free() {
  local version="$1"
  if curl -sf "https://crates.io/api/v1/crates/${CRATE_NAME}/${version}" >/dev/null 2>&1; then
    echo "Version ${version} is already published on crates.io" >&2
    exit 1
  fi
  echo "  crates.io: ${version} not published"
}

release_run_cargo_checks() {
  echo "Running cargo fmt, clippy, test…"
  (cd "$ROOT" && cargo fmt -- --check)
  (cd "$ROOT" && cargo clippy -- -D warnings)
  (cd "$ROOT" && cargo test)
}

release_verify_crate_package() {
  local version="$1"
  (cd "$ROOT" && cargo package --allow-dirty --quiet)
  local crate glob size
  glob="${CRATE_NAME}-${version}.crate"
  crate="$(ls -1 "$ROOT"/target/package/"$glob" 2>/dev/null | head -1)"
  if [[ -z "$crate" ]]; then
    echo "cargo package did not produce ${glob}" >&2
    exit 1
  fi
  size="$(stat -c%s "$crate")"
  echo "  crate size: ${size} bytes"
  if [[ "$size" -ge 10485760 ]]; then
    echo "Crate too large for crates.io (limit 10 MB)" >&2
    exit 1
  fi
}

release_wait_for_workflow() {
  local tag="$1"
  if ! command -v gh >/dev/null 2>&1; then
    echo "Install gh to watch the release workflow, or check Actions manually." >&2
    return 0
  fi
  echo "Waiting for Release workflow on ${tag}…"
  local run_id
  for _ in $(seq 1 30); do
    run_id="$(gh run list --workflow release.yml --limit 10 \
      --json databaseId,headBranch,status \
      --jq ".[] | select(.headBranch == \"${tag}\") | .databaseId" 2>/dev/null | head -1)"
    [[ -n "$run_id" ]] && break
    sleep 2
  done
  if [[ -z "$run_id" ]]; then
    echo "Could not find Release workflow run for ${tag}" >&2
    return 1
  fi
  gh run watch "$run_id" --exit-status
}
