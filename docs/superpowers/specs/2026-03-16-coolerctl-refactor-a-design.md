# CoolerControl CLI Refactor — Phase A (Targeted Fixes)

## Summary

Fix 6 identified issues in the coolerctl CLI and integrate it into the NixOS module as a proper option. No restructuring or unnecessary refactoring.

## Changes

### 1. Fix file handle leak in `_load_token` (cli/coolerctl.py:66)

**Current:** `open(TOKEN_PATH).read().strip()` — never closes the file descriptor.

**Fix:** Use `with` statement:
```python
with open(TOKEN_PATH) as f:
    return f.read().strip()
```

### 2. Add CLI to NixOS module (module.nix)

Add `programs.coolercontrol.cli.enable` option (default `true` when coolercontrol is enabled). When enabled, adds `coolerctl` to `environment.systemPackages`.

```nix
cli.enable = lib.mkOption {
  type = lib.types.bool;
  default = true;
  description = "Whether to install the coolerctl CLI tool.";
};

cli.package = lib.mkOption {
  type = lib.types.package;
  default = pkgs.coolercontrol.coolerctl;
  defaultText = lib.literalExpression "pkgs.coolercontrol.coolerctl";
  description = "The coolerctl CLI package to use.";
};
```

Note: Requires the overlay to be applied (same assumption as existing `package` and `guiPackage` options). The new options are inside the existing `lib.mkIf cfg.enable` block.

In `config`:
```nix
environment.systemPackages =
  [ cfg.guiPackage ]
  ++ lib.optional cfg.cli.enable cfg.cli.package;
```

### 3. Add `result-daemon` to `.gitignore`

Add `result-*` pattern to catch any `nix build -o result-*` symlinks.

### 4. Add `--speed-profile` to `profiles create` (cli/coolerctl.py:775)

Add a `--speed-profile` option accepting comma-separated `temp:duty` pairs:

```
coolerctl profiles create "Gaming" --type Graph --speed-profile "30:25,50:40,70:70,85:100"
```

Parsed into `[[30,25],[50,40],[70,70],[85,100]]` for the API payload key `speed_profile`.

Validation: temp must be numeric, duty must be integer 0-100. Raises `click.BadParameter` on malformed input. Mutually exclusive with `--speed-fixed` (Click will allow both but `--speed-profile` takes precedence for Graph type; `--speed-fixed` is for Fixed type).

### 5. Expose common settings as CLI flags (cli/coolerctl.py:1367)

Add the most-used settings as explicit flags to `settings update`:
- `--apply-on-boot` / `--no-apply-on-boot`
- `--poll-rate FLOAT`
- `--startup-delay INT` (already exists)
- `--handle-dynamic-temps` / `--no-handle-dynamic-temps`
- `--liquidctl-integration` / `--no-liquidctl-integration`

Less common settings remain available via `--from-json`.

JSON key mapping:
- `--apply-on-boot` / `--no-apply-on-boot` -> `{"apply_on_boot": bool}`
- `--poll-rate FLOAT` -> `{"poll_rate": float}`
- `--startup-delay INT` -> `{"startup_delay": int}` (existing)
- `--handle-dynamic-temps` / `--no-handle-dynamic-temps` -> `{"handle_dynamic_temps": bool}`
- `--liquidctl-integration` / `--no-liquidctl-integration` -> `{"liquidctl_integration": bool}`

### 6. Add `--version` flag (cli/coolerctl.py:156)

Add `@click.version_option(version="0.1.0", prog_name="coolerctl")` to the root group.

## Notes

- All 6 changes are independent and can be implemented in any order.
- `export-config` already handles speed_profile conversion correctly (line 1829) — no changes needed.
- hm-module.nix shares TOKEN_PATH (`~/.config/coolerctl/token`) with the CLI — unified token management deferred to Phase B.

## Out of Scope

- Python package restructuring (Phase B)
- Shell completion generation
- Comprehensive test suite
- Any changes to `hm-module.nix`

## Testing

- `nix build .#coolerctl` — verify package builds
- `result/bin/coolerctl --version` — verify version flag
- `result/bin/coolerctl --help` — verify all commands present
- `result/bin/coolerctl profiles create --help` — verify speed-profile option
- `result/bin/coolerctl settings update --help` — verify new flags
