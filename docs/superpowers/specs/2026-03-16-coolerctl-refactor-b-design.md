# CoolerControl CLI Refactor — Phase B (Package Restructuring)

## Summary

Restructure the 1,900-line `cli/coolerctl.py` monolith into a proper Python package at `coolerctl/`, split by command group. Pure code move — no behavior changes.

## Package Structure

```
coolerctl/
├── __init__.py        # Root CLI group, --version, --base-url, --json, registers all subcommands
├── api.py             # SESSION, DEFAULT_BASE, TOKEN_PATH, api(), api_upload(), api_raw(), ApiError, _load_token(), urllib3 warning suppression
├── output.py          # Colors, _c(), _use_color(), _temp_color(), fmt_json()
├── auth.py            # auth group + tokens group
├── devices.py         # devices group (list, settings, set-manual, set-profile, reset, pwm, lighting, lcd, asetek690)
├── lcd.py             # lcd group (list-images, upload-image, update-settings, shutdown-image)
├── profiles.py        # profiles group (list, create, update, delete, order)
├── functions.py       # functions group (list, create, update, delete, order)
├── modes.py           # modes group (list, show, active, activate, create, update, delete, duplicate, order)
├── alerts.py          # alerts group (list, create, update, delete)
├── sensors.py         # custom-sensors group (list, show, create, update, delete, order)
├── settings.py        # settings group (show, update, devices, update-device, ui, update-ui)
├── plugins.py         # plugins group (list, config, update-config, ui-check, ui-file, lib)
├── daemon.py          # Top-level: handshake, health, shutdown, acknowledge, status (+_print_status_entry)
├── streaming.py       # _stream_sse(), watch-status, watch-logs, watch-alerts, watch-modes, logs
├── shortcuts.py       # Top-level: fan, temps, fans, thinkpad-fan-control, detect
├── export.py          # _to_nix(), export-config command
├── setup.py           # find_packages(), entry_point coolerctl:main
├── package.nix        # Updated Nix derivation
└── test_coolerctl.py  # Existing 19 tests with updated imports
```

## Wiring Pattern

Each command module defines its Click group/commands. `__init__.py` imports and registers them:

```python
# coolerctl/__init__.py
import click
from .auth import auth, tokens
from .profiles import profiles
# ... all other groups

@click.group()
@click.version_option(version="0.1.0", prog_name="coolerctl")
@click.option("--base-url", "-u", ...)
@click.option("--json", "-j", ...)
@click.pass_context
def cli(ctx, base_url, json_output):
    ctx.ensure_object(dict)
    ctx.obj["base"] = base_url
    ctx.obj["json"] = json_output

cli.add_command(auth)
cli.add_command(tokens)
cli.add_command(profiles)
# ... etc

def main():
    cli()
```

Each command module imports only from `api` and `output`:

```python
# coolerctl/profiles.py
from .api import api, ApiError
from .output import fmt_json, _c, BOLD
```

No cross-dependencies between command modules.

## Dependencies Between Modules

```
__init__.py --> api.py (imports DEFAULT_BASE for --base-url default)
__init__.py --> all command modules (imports groups/commands to register)
all command modules --> api.py (HTTP calls)
all command modules --> output.py (formatting)
export.py --> api.py (uses api(), api_raw())
streaming.py --> api.py (uses SESSION, _load_token directly for SSE)
```

Note: `export.py` does not depend on `output.py` — `_to_nix` is a self-contained serializer.

## Nix Changes

- `flake.nix`: Change `./cli/package.nix` to `./coolerctl/package.nix`
- `setup.py`: `py_modules=["coolerctl"]` → `packages=["coolerctl"]` with `package_dir={"coolerctl": "."}` (setup.py lives inside the package dir; Nix copies it as build root, so `.` is correct), entry point stays `coolerctl:main`
- `package.nix`: `src = ./.` unchanged (relative to new dir), `format = "setuptools"` unchanged

## Testing

Existing 19 tests updated. Key: `unittest.mock.patch` must target where the name is **looked up**, not where it is defined.

Import updates:
- `from coolerctl import cli` stays (cli is in `__init__.py`)
- `from coolerctl.api import _load_token, ApiError`

Mock patch target mapping:

| Test Class | Old Target | New Target |
|---|---|---|
| TestLoadToken | `coolerctl.TOKEN_PATH` | `coolerctl.api.TOKEN_PATH` |
| TestSpeedProfile | `coolerctl.api` | `coolerctl.profiles.api` |
| TestSettingsFlags | `coolerctl.api` | `coolerctl.settings.api` |
| TestApiErrorHandling (SESSION) | `coolerctl.SESSION` | `coolerctl.api.SESSION` |
| TestApiErrorHandling (handshake) | `coolerctl.SESSION` | `coolerctl.api.SESSION` |
| TestRootOptions (health) | `coolerctl.api` | `coolerctl.daemon.api` |
| TestRootOptions (handshake) | `coolerctl.api` | `coolerctl.daemon.api` |

No new tests — pure restructuring with no behavior changes.

## Migration

1. Create `coolerctl/` directory with all new modules
2. Move test file to `coolerctl/test_coolerctl.py`
3. Update `setup.py` and `package.nix` in new location
4. Update `flake.nix` to reference new path
5. Delete old `cli/` directory entirely
6. Verify: `nix build .#coolerctl` passes all 19 tests

## Out of Scope

- No new features or API changes
- No new tests beyond import path updates
- No changes to `module.nix` or `hm-module.nix` (reference overlay, not file paths)
- No version bump (still 0.1.0)
