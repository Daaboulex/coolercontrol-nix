# CoolerControl CLI Refactor — Phase B (Package Restructuring)

## Summary

Restructure the 1,900-line `cli/coolerctl.py` monolith into a proper Python package at `coolerctl/`, split by command group. Pure code move — no behavior changes.

## Package Structure

```
coolerctl/
├── __init__.py        # Root CLI group, --version, --base-url, --json, registers all subcommands
├── api.py             # SESSION, api(), api_upload(), api_raw(), ApiError, _load_token()
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
__init__.py --> all command modules (imports groups to register)
all command modules --> api.py (HTTP calls)
all command modules --> output.py (formatting)
export.py --> api.py + output.py (uses api_raw too)
streaming.py --> api.py (uses SESSION directly for SSE)
```

## Nix Changes

- `flake.nix`: Change `./cli/package.nix` to `./coolerctl/package.nix`
- `setup.py`: `py_modules=["coolerctl"]` → `packages=["coolerctl"]` with `package_dir={"coolerctl": "."}`, entry point stays `coolerctl:main`
- `package.nix`: `src = ./.` unchanged (relative to new dir), `format = "setuptools"` unchanged

## Testing

Existing 19 tests updated with imports from the package:
- `from coolerctl import cli, _load_token, api, ApiError` → `from coolerctl import cli, main` and `from coolerctl.api import api, ApiError, _load_token`
- Mock patches updated: `coolerctl.api` → `coolerctl.api.api`, etc.
- No new tests — pure restructuring with no behavior changes

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
