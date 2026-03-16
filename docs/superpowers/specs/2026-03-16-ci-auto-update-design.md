# CI + Auto-update Automation Design

## Summary

Add CI build verification on PRs, enhance upstream version checking to create auto-PRs with correct hashes, add stale issue cleanup, and automate flake.lock updates.

## 1. CI Build & Test (`.github/workflows/ci.yml`)

**Triggers:** `pull_request` targeting `main`, `workflow_dispatch`

**Jobs:**

### `build-packages`
- Uses: `ubuntu-latest`
- Installs Nix via `DeterminateSystems/nix-installer-action@v16`
- Enables cache via `DeterminateSystems/magic-nix-cache-action@v8`
- Builds all 4 packages in sequence:
  - `nix build .#coolercontrold`
  - `nix build .#coolercontrol-ui-data`
  - `nix build .#coolercontrol-gui`
  - `nix build .#coolerctl` (runs 19 pytest tests via checkPhase)

Note: `coolercontrol-gui` requires `qt6.qtwebengine` which is heavy. If CI times out, it can be moved to a separate `build-gui` job with a longer timeout, or omitted with a comment noting the limitation.

### `flake-check`
- Runs `nix flake check` (validates module evaluation, overlay, etc.)

### `format-check`
- Installs Nix, runs `nix fmt -- --fail-on-change` to catch unformatted code

**Permissions:** `contents: read`

**Concurrency:**
```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

## 2. Enhanced Auto-update (`.github/workflows/check-upstream.yml`)

**Replaces** the current issue-only workflow.

**Triggers:** `schedule: cron '0 12 * * 1,4'` (Mon/Thu noon UTC) + `workflow_dispatch`

**Permissions:** `contents: write`, `pull-requests: write`, `issues: write` (fallback issue creation)

**Concurrency:**
```yaml
concurrency:
  group: auto-update
  cancel-in-progress: false
```

**Git config for push:**
```yaml
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
- run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
```

**Steps:**

1. Checkout repo (with push token and git config)
2. Install Nix
3. Get current version from `flake.nix`
4. Query GitLab API for latest upstream tag (tags have no `v` prefix, e.g. `4.0.1`)
5. If versions match, exit early
6. Check if a PR already exists for this version (skip if so)
7. Get new source hash using the dummy-hash trick (same code path as `fetchFromGitLab`):
   - Set src hash to `sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=` in `flake.nix`
   - Run `nix build .#coolercontrold 2>&1` and extract correct hash from error
8. Update `flake.nix` with correct src hash:
   ```bash
   sed -i "s/version = \"${OLD_VERSION}\"/version = \"${NEW_VERSION}\"/" flake.nix
   sed -i "s/rev = \"${OLD_VERSION}\"/rev = \"${NEW_VERSION}\"/" flake.nix
   sed -i "s|hash = \"sha256-[A-Za-z0-9+/=]*\"|hash = \"${NEW_SRC_HASH}\"|" flake.nix
   ```
9. Set cargoHash to dummy in `coolercontrold.nix`, build, extract correct hash from error
10. Update cargoHash in `coolercontrold.nix`
11. Set npmDepsHash to dummy in `coolercontrol-ui-data.nix`, build, extract correct hash from error
12. Update npmDepsHash in `coolercontrol-ui-data.nix`
13. Verify all 4 packages build:
    - `nix build .#coolercontrold`
    - `nix build .#coolercontrol-ui-data`
    - `nix build .#coolercontrol-gui`
    - `nix build .#coolerctl`
14. Also run `nix flake update` to ensure lock file is current
15. Create branch `auto-update/${NEW_VERSION}`, commit, push
16. Create PR with `auto-update` label via `gh pr create`

**Hash extraction pattern (hardened against ANSI escapes and Nix version differences):**
```bash
extract_hash() {
  local output="$1"
  echo "$output" | sed 's/\x1b\[[0-9;]*m//g' | grep -oP 'got:\s+\Ksha256-[A-Za-z0-9+/=]+' | head -1
}
```

**Error handling:**
- If GitLab API fails or returns unexpected format, exit with error (no issue/PR)
- If hash extraction fails after 2 retries, create a draft PR labeled `needs-manual-fix`
- If final build verification fails, create a draft PR labeled `needs-manual-fix`

## 3. Stale Cleanup (`.github/workflows/stale.yml`)

**Triggers:** `schedule: cron '0 6 * * *'` (daily 6am UTC)

**Uses:** `actions/stale@v9`

**Configuration:**
- `days-before-stale: 14`
- `days-before-close: 3`
- `stale-issue-label: stale`
- `stale-pr-label: stale`
- `exempt-issue-labels: pinned,security`
- `exempt-pr-labels: pinned,security,auto-update`
- `stale-issue-message: "This issue has been inactive for 14 days. It will be closed in 3 days unless there is new activity."`
- `stale-pr-message: "This PR has been inactive for 14 days. It will be closed in 3 days unless there is new activity."`

**Permissions:** `issues: write`, `pull-requests: write`

## 4. Flake Lock Update (`.github/workflows/update-lock.yml`)

**Triggers:** `schedule: cron '0 8 * * 0'` (Sundays 8am UTC) + `workflow_dispatch`

**Permissions:** `contents: write`, `pull-requests: write`

**Concurrency:**
```yaml
concurrency:
  group: auto-update
  cancel-in-progress: false
```

**Steps:**

1. Checkout repo (with push token and git config, same as auto-update)
2. Install Nix
3. Check for existing open PRs with `auto-update/flake-lock` prefix (skip if exists)
4. Run `nix flake update`
5. Check if `flake.lock` changed (`git diff --exit-code flake.lock`)
6. If changed:
   - Create branch `auto-update/flake-lock-YYYY-MM-DD`
   - Commit with message `chore: update flake.lock`
   - Push and create PR with `auto-update` label
   - PR body includes `nix flake metadata` output showing input revisions
7. If unchanged, exit cleanly

Note: shares `auto-update` concurrency group with check-upstream to prevent race conditions.

## Known Risks

- Auto-update runs upstream Nix expressions in CI. A compromised upstream could execute arbitrary code in the runner. This is inherent to any Nix auto-update system.
- Upstream tags have no `v` prefix (e.g. `4.0.1`). If upstream changes this convention, the version comparison will break. The workflow logs a warning if the tag format looks unexpected.

## Out of Scope

- Binary cache (Cachix) — separate spec
- Supply chain security (cargo audit, npm audit) — separate spec
- Systemd hardening — separate spec
- Branch protection rules (manual GitHub settings)
- Action version SHA pinning (can be added later)

## Files

- Create: `.github/workflows/ci.yml`
- Replace: `.github/workflows/check-upstream.yml`
- Create: `.github/workflows/stale.yml`
- Create: `.github/workflows/update-lock.yml`
