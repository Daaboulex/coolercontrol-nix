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
  description = "The coolerctl CLI package to use.";
};
```

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

Parsed into `[[30,25],[50,40],[70,70],[85,100]]` for the API.

### 5. Expose common settings as CLI flags (cli/coolerctl.py:1367)

Add the most-used settings as explicit flags to `settings update`:
- `--apply-on-boot` / `--no-apply-on-boot`
- `--poll-rate FLOAT`
- `--startup-delay INT` (already exists)
- `--handle-dynamic-temps` / `--no-handle-dynamic-temps`
- `--liquidctl-integration` / `--no-liquidctl-integration`

Less common settings remain available via `--from-json`.

### 6. Add `--version` flag (cli/coolerctl.py:156)

Add `@click.version_option(version="0.1.0", prog_name="coolerctl")` to the root group.

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
