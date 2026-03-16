# CoolerControl CLI Refactor Phase A — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 6 targeted issues in the coolerctl CLI and integrate it into the NixOS module.

**Architecture:** Direct edits to 3 files: `cli/coolerctl.py` (Python fixes), `module.nix` (NixOS integration), `.gitignore` (cleanup). No new files, no restructuring.

**Tech Stack:** Python 3.10+ / Click, Nix module system

**Spec:** `docs/superpowers/specs/2026-03-16-coolerctl-refactor-a-design.md`

---

## Chunk 1: All Tasks

### Task 1: Fix file handle leak in `_load_token`

**Files:**
- Modify: `cli/coolerctl.py:65-67`

- [ ] **Step 1: Fix the leak**

Replace line 66:
```python
        return open(TOKEN_PATH).read().strip()
```
With:
```python
        with open(TOKEN_PATH) as f:
            return f.read().strip()
```

- [ ] **Step 2: Commit**

```bash
git add cli/coolerctl.py
git commit -m "fix(cli): close file handle in _load_token"
```

---

### Task 2: Add `--version` flag

**Files:**
- Modify: `cli/coolerctl.py:156` (the `@click.group()` decorator on `cli`)

- [ ] **Step 1: Add version_option decorator**

Add `@click.version_option(version="0.1.0", prog_name="coolerctl")` between the existing `@click.group()` and `@click.option("--base-url", ...)` decorators at line 156-158.

Result:
```python
@click.group()
@click.version_option(version="0.1.0", prog_name="coolerctl")
@click.option("--base-url", "-u", default=DEFAULT_BASE, envvar="COOLERCONTROL_URL",
              help="Daemon API base URL")
@click.option("--json", "-j", "json_output", is_flag=True, help="Force JSON output")
@click.pass_context
def cli(ctx, base_url: str, json_output: bool):
```

- [ ] **Step 2: Commit**

```bash
git add cli/coolerctl.py
git commit -m "feat(cli): add --version flag"
```

---

### Task 3: Add `--speed-profile` to `profiles create`

**Files:**
- Modify: `cli/coolerctl.py:767-787` (the `profiles_create` function)

- [ ] **Step 1: Add the option and parsing logic**

Add `--speed-profile` option to `profiles_create`. The full replacement of the function:

```python
@profiles.command("create")
@click.argument("name")
@click.option("--type", "-t", "p_type", default="Graph",
              help="Profile type: Graph, Fixed, Mix, Default")
@click.option("--speed-fixed", type=int, help="Fixed speed percentage")
@click.option("--speed-profile", "speed_profile_str",
              help="Fan curve as temp:duty pairs (e.g. '30:25,50:40,70:70,85:100')")
@click.option("--temp-source", help="Temperature source as device_uid:channel")
@click.option("--function", "function_uid", help="Function UID for this profile")
@click.pass_context
def profiles_create(ctx, name: str, p_type: str, speed_fixed: Optional[int],
                     speed_profile_str: Optional[str], temp_source: Optional[str],
                     function_uid: Optional[str]):
    """Create a new profile."""
    payload = {"name": name, "p_type": p_type}
    if speed_fixed is not None:
        payload["speed_fixed"] = speed_fixed
    if speed_profile_str:
        try:
            points = []
            for pair in speed_profile_str.split(","):
                t, d = pair.strip().split(":")
                temp_val = float(t)
                duty_val = int(d)
                if duty_val < 0 or duty_val > 100:
                    raise ValueError(f"duty must be 0-100, got {duty_val}")
                points.append([temp_val, duty_val])
            payload["speed_profile"] = points
        except ValueError as e:
            raise click.BadParameter(f"Invalid speed-profile format: {e}. Use 'temp:duty,temp:duty,...'")
    if temp_source:
        parts = temp_source.split(":")
        payload["temp_source"] = {"device_uid": parts[0], "temp_name": parts[1]}
    if function_uid:
        payload["function_uid"] = function_uid
    api("POST", "/profiles", ctx.obj["base"], json=payload)
    click.echo(f"Created profile: {name}")
```

- [ ] **Step 2: Commit**

```bash
git add cli/coolerctl.py
git commit -m "feat(cli): add --speed-profile option to profiles create"
```

---

### Task 4: Expose common settings flags

**Files:**
- Modify: `cli/coolerctl.py:1366-1385` (the `settings_update` function)

- [ ] **Step 1: Replace settings_update with expanded version**

```python
@settings.command("update")
@click.option("--startup-delay", type=int, help="Startup delay in seconds")
@click.option("--apply-on-boot/--no-apply-on-boot", default=None,
              help="Re-apply settings on daemon startup")
@click.option("--poll-rate", type=float, help="Sensor polling interval (0.5-5.0 seconds)")
@click.option("--handle-dynamic-temps/--no-handle-dynamic-temps", default=None,
              help="Handle hotplug temperature sources")
@click.option("--liquidctl-integration/--no-liquidctl-integration", default=None,
              help="Enable liquidctl for AIO coolers")
@click.option("--from-json", "json_file", type=click.Path(exists=True),
              help="Update from a JSON file")
@click.pass_context
def settings_update(ctx, startup_delay: Optional[int], apply_on_boot: Optional[bool],
                     poll_rate: Optional[float], handle_dynamic_temps: Optional[bool],
                     liquidctl_integration: Optional[bool], json_file: Optional[str]):
    """Update daemon settings."""
    if json_file:
        with open(json_file) as f:
            payload = json.load(f)
        api("PATCH", "/settings", ctx.obj["base"], json=payload)
        click.echo("Settings updated from file")
        return
    payload = {}
    if startup_delay is not None:
        payload["startup_delay"] = startup_delay
    if apply_on_boot is not None:
        payload["apply_on_boot"] = apply_on_boot
    if poll_rate is not None:
        payload["poll_rate"] = poll_rate
    if handle_dynamic_temps is not None:
        payload["handle_dynamic_temps"] = handle_dynamic_temps
    if liquidctl_integration is not None:
        payload["liquidctl_integration"] = liquidctl_integration
    if not payload:
        raise click.UsageError("No settings to update (use flags or --from-json)")
    api("PATCH", "/settings", ctx.obj["base"], json=payload)
    click.echo("Settings updated")
```

- [ ] **Step 2: Commit**

```bash
git add cli/coolerctl.py
git commit -m "feat(cli): expose common daemon settings as CLI flags"
```

---

### Task 5: Add CLI to NixOS module

**Files:**
- Modify: `module.nix:12-27` (options block) and `module.nix:31` (config block)

- [ ] **Step 1: Add cli options**

In the `options.programs.coolercontrol` block, after the `guiPackage` option (after line 27), add:

```nix
    cli = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = "Whether to install the coolerctl CLI tool.";
      };

      package = lib.mkOption {
        type = lib.types.package;
        default = pkgs.coolercontrol.coolerctl;
        defaultText = lib.literalExpression "pkgs.coolercontrol.coolerctl";
        description = "The coolerctl CLI package to use.";
      };
    };
```

- [ ] **Step 2: Update systemPackages**

Change line 31 from:
```nix
    environment.systemPackages = [ cfg.guiPackage ];
```
To:
```nix
    environment.systemPackages =
      [ cfg.guiPackage ]
      ++ lib.optional cfg.cli.enable cfg.cli.package;
```

- [ ] **Step 3: Commit**

```bash
git add module.nix
git commit -m "feat(module): add cli.enable option to install coolerctl"
```

---

### Task 6: Clean up `.gitignore`

**Files:**
- Modify: `.gitignore:1`

- [ ] **Step 1: Add result-* pattern**

Change line 1 from:
```
result
```
To:
```
result
result-*
```

- [ ] **Step 2: Remove the result-daemon symlink**

```bash
rm result-daemon
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add result-* to gitignore and remove result-daemon"
```

---

## Verification

After all tasks:

- [ ] `nix build .#coolerctl` — package builds
- [ ] `result/bin/coolerctl --version` — prints `coolerctl, version 0.1.0`
- [ ] `result/bin/coolerctl --help` — all commands present
- [ ] `result/bin/coolerctl profiles create --help` — shows `--speed-profile`
- [ ] `result/bin/coolerctl settings update --help` — shows new flags
- [ ] `nix eval .#nixosModules.default --apply 'x: "ok"'` — module loads
- [ ] `git status` — no untracked `result-*` files
