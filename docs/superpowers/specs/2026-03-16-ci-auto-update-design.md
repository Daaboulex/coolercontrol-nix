# CI + Auto-update Automation Design

## Summary

Add CI build verification on PRs, enhance upstream version checking to create auto-PRs with correct hashes, add stale issue cleanup, and automate flake.lock updates.

## 1. CI Build & Test (`.github/workflows/ci.yml`)

**Triggers:** `pull_request` targeting `main`

**Jobs:**

### `build-packages`
- Uses: `ubuntu-latest`
- Installs Nix via `DeterminateSystems/nix-installer-action@v16`
- Enables cache via `DeterminateSystems/magic-nix-cache-action@v8`
- Builds all 4 packages in sequence:
  - `nix build .#coolercontrold`
  - `nix build .#coolercontrol-gui`
  - `nix build .#coolercontrol-ui-data`
  - `nix build .#coolerctl` (runs 19 pytest tests via checkPhase)

### `flake-check`
- Runs `nix flake check` (validates module evaluation, overlay, etc.)

### `format-check`
- Installs Nix, runs `nix fmt -- --fail-on-change` to catch unformatted code

**Permissions:** `contents: read`

## 2. Enhanced Auto-update (`.github/workflows/check-upstream.yml`)

**Replaces** the current issue-only workflow.

**Triggers:** `schedule: cron '0 12 * * 1,4'` (Mon/Thu noon UTC) + `workflow_dispatch`

**Permissions:** `contents: write`, `pull-requests: write`

**Steps:**

1. Checkout repo
2. Install Nix
3. Get current version from `flake.nix`
4. Query GitLab API for latest upstream tag
5. If versions match, exit early
6. Check if a PR already exists for this version (skip if so)
7. Prefetch new source:
   ```bash
   NEW_HASH=$(nix-prefetch-url --unpack --type sha256 \
     "https://gitlab.com/coolercontrol/coolercontrol/-/archive/${NEW_VERSION}/coolercontrol-${NEW_VERSION}.tar.gz" \
     2>/dev/null | xargs nix hash convert --hash-algo sha256 --to sri)
   ```
8. Update `flake.nix`: replace version string and src hash using `sed`
9. Build coolercontrold with deliberately wrong cargoHash (`sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=`), capture correct hash from error output
10. Update cargoHash in `coolercontrold.nix`
11. Build coolercontrol-ui-data with wrong npmDepsHash, capture correct hash from error output
12. Update npmDepsHash in `coolercontrol-ui-data.nix`
13. Run full `nix build .#coolercontrold` and `nix build .#coolerctl` to verify
14. Create branch `auto-update/${NEW_VERSION}`, commit, push
15. Create PR via `gh pr create` with title and body including:
    - Version change (old -> new)
    - Link to upstream release notes
    - Updated hashes
    - Note that CI will verify the build

**Hash extraction pattern:**
```bash
nix build .#coolercontrold 2>&1 | grep -oP 'got:\s+\Ksha256-[A-Za-z0-9+/=]+'
```

**Error handling:**
- If prefetch fails, create an issue instead of a PR (upstream may have changed release format)
- If hash extraction fails after 2 retries, create a draft PR with a note about manual hash fixup
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
- `exempt-pr-labels: pinned,security`
- `stale-issue-message: "This issue has been inactive for 14 days. It will be closed in 3 days unless there is new activity."`
- `stale-pr-message: "This PR has been inactive for 14 days. It will be closed in 3 days unless there is new activity."`

**Permissions:** `issues: write`, `pull-requests: write`

## 4. Flake Lock Update (`.github/workflows/update-lock.yml`)

**Triggers:** `schedule: cron '0 8 * * 0'` (Sundays 8am UTC) + `workflow_dispatch`

**Permissions:** `contents: write`, `pull-requests: write`

**Steps:**

1. Checkout repo
2. Install Nix
3. Run `nix flake update`
4. Check if `flake.lock` changed (`git diff --exit-code flake.lock`)
5. If changed:
   - Create branch `auto-update/flake-lock-YYYY-MM-DD`
   - Commit with message `chore: update flake.lock`
   - Push and create PR
   - PR body includes diff summary of nixpkgs revision change
6. If unchanged, exit cleanly

**Deduplication:** Check for existing open PRs with `auto-update/flake-lock` prefix before creating.

## Out of Scope

- Binary cache (Cachix) — separate spec
- Supply chain security (cargo audit, npm audit) — separate spec
- Systemd hardening — separate spec
- Branch protection rules (manual GitHub settings)

## Files

- Create: `.github/workflows/ci.yml`
- Replace: `.github/workflows/check-upstream.yml`
- Create: `.github/workflows/stale.yml`
- Create: `.github/workflows/update-lock.yml`
