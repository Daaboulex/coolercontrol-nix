# CoolerControl CLI Phase B — Package Restructuring Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the 1,900-line `cli/coolerctl.py` monolith into a proper Python package at `coolerctl/` with ~17 modules.

**Architecture:** Extract each Click command group into its own module. Shared infrastructure in `api.py` and `output.py`. `__init__.py` wires everything together. Update Nix build files and tests.

**Tech Stack:** Python 3.10+ / Click / requests, Nix (buildPythonApplication)

**Spec:** `docs/superpowers/specs/2026-03-16-coolerctl-refactor-b-design.md`

---

### Task 1: Create package directory and infrastructure modules

**Files:**
- Create: `coolerctl/__init__.py`
- Create: `coolerctl/api.py`
- Create: `coolerctl/output.py`

- [ ] **Step 1: Create `coolerctl/api.py`**

Extract lines 10-143 (imports, constants, SESSION, urllib3 suppression, ApiError, _load_token, api, api_upload, api_raw):

Source ranges from `cli/coolerctl.py`:
- Lines 10-25: imports, DEFAULT_BASE, TOKEN_PATH, SESSION, urllib3
- Lines 59-60: ApiError class
- Lines 63-68: _load_token
- Lines 70-96: api()
- Lines 98-124: api_upload()
- Lines 127-142: api_raw()

- [ ] **Step 2: Create `coolerctl/output.py`**

Extract lines 27-57 (color constants, _use_color, _c, _temp_color) and lines 145-151 (fmt_json):

Source ranges:
- Lines 27-57: BOLD, DIM, RED, GREEN, YELLOW, BLUE, CYAN, RESET, _use_color, _c, _temp_color
- Lines 145-151: fmt_json

- [ ] **Step 3: Create stub `coolerctl/__init__.py`**

Just the root CLI group (lines 157-171) with `DEFAULT_BASE` import and `main()`. No command registrations yet.

---

### Task 2: Extract all command modules (parallel-safe, independent)

Each module follows the same pattern: define Click group/commands, import from `.api` and `.output`.

**Files to create (all under `coolerctl/`):**

- [ ] **Step 1: `daemon.py`** — lines 177-235 (handshake, health, shutdown, acknowledge) + lines 412-480 (status, _print_status_entry)
- [ ] **Step 2: `auth.py`** — lines 242-347 (auth group) + lines 354-404 (tokens group)
- [ ] **Step 3: `devices.py`** — lines 487-637 (devices group)
- [ ] **Step 4: `lcd.py`** — lines 644-718 (lcd group)
- [ ] **Step 5: `profiles.py`** — lines 726-852 (profiles group)
- [ ] **Step 6: `functions.py`** — lines 859-981 (functions group)
- [ ] **Step 7: `modes.py`** — lines 988-1133 (modes group)
- [ ] **Step 8: `alerts.py`** — lines 1140-1243 (alerts group)
- [ ] **Step 9: `sensors.py`** — lines 1251-1345 (custom-sensors group)
- [ ] **Step 10: `settings.py`** — lines 1353-1429 (settings group)
- [ ] **Step 11: `plugins.py`** — lines 1436-1521 (plugins group)
- [ ] **Step 12: `streaming.py`** — lines 1569-1626 (_stream_sse, watch-status, watch-logs, watch-alerts, watch-modes) + lines 1633-1650 (logs)
- [ ] **Step 13: `shortcuts.py`** — lines 1528-1538 (thinkpad-fan-control) + lines 1546-1562 (detect) + lines 1657-1698 (fan, temps, fans)
- [ ] **Step 14: `export.py`** — lines 1705-1930 (_to_nix, _safe_name, export_config)

---

### Task 3: Wire all commands into `__init__.py`

**Files:**
- Modify: `coolerctl/__init__.py`

- [ ] **Step 1: Add all imports and registrations**

```python
from .daemon import handshake, health, shutdown, acknowledge, status
from .auth import auth, tokens
from .devices import devices
from .lcd import lcd
from .profiles import profiles
from .functions import functions
from .modes import modes
from .alerts import alerts
from .sensors import custom_sensors
from .settings import settings
from .plugins import plugins
from .streaming import watch_status, watch_logs, watch_alerts, watch_modes, show_logs
from .shortcuts import quick_fan, quick_temps, quick_fans, thinkpad_fan_control, detect
from .export import export_config

# Register groups
cli.add_command(auth)
cli.add_command(tokens)
cli.add_command(devices)
cli.add_command(lcd)
cli.add_command(profiles)
cli.add_command(functions)
cli.add_command(modes)
cli.add_command(alerts)
cli.add_command(custom_sensors)
cli.add_command(settings)
cli.add_command(plugins)

# Register top-level commands
cli.add_command(handshake)
cli.add_command(health)
cli.add_command(shutdown)
cli.add_command(acknowledge)
cli.add_command(status)
cli.add_command(watch_status)
cli.add_command(watch_logs)
cli.add_command(watch_alerts)
cli.add_command(watch_modes)
cli.add_command(show_logs)
cli.add_command(quick_fan)
cli.add_command(quick_temps)
cli.add_command(quick_fans)
cli.add_command(thinkpad_fan_control)
cli.add_command(detect)
cli.add_command(export_config)
```

---

### Task 4: Update build files

**Files:**
- Create: `coolerctl/setup.py` (new version)
- Create: `coolerctl/package.nix` (updated)
- Modify: `flake.nix:37`

- [ ] **Step 1: Write `coolerctl/setup.py`**

```python
from setuptools import setup

setup(
    name="coolerctl",
    version="0.1.0",
    # setup.py lives inside the package dir; Nix copies it as build root,
    # so "." correctly points to the package source files.
    packages=["coolerctl"],
    package_dir={"coolerctl": "."},
    install_requires=[
        "click>=8.0",
        "requests>=2.28",
    ],
    entry_points={
        "console_scripts": [
            "coolerctl=coolerctl:main",
        ],
    },
    python_requires=">=3.10",
    description="CLI for CoolerControl daemon REST API",
    license="GPL-3.0",
)
```

- [ ] **Step 2: Write `coolerctl/package.nix`**

Same as current `cli/package.nix` but with updated test path and src.

- [ ] **Step 3: Update `flake.nix` line 37**

Change `./cli/package.nix` to `./coolerctl/package.nix`.

---

### Task 5: Update tests

**Files:**
- Create: `coolerctl/test_coolerctl.py` (updated from `cli/test_coolerctl.py`)

- [ ] **Step 1: Update imports and mock targets**

```python
from coolerctl import cli
from coolerctl.api import _load_token, ApiError

# Mock target mapping:
# "coolerctl.TOKEN_PATH"  → "coolerctl.api.TOKEN_PATH"
# "coolerctl.api" (profiles) → "coolerctl.profiles.api"
# "coolerctl.api" (settings) → "coolerctl.settings.api"
# "coolerctl.SESSION" → "coolerctl.api.SESSION"
# "coolerctl.api" (health) → "coolerctl.daemon.api"
# "coolerctl.api" (handshake) → "coolerctl.daemon.api"
```

---

### Task 6: Delete old `cli/` directory and verify

- [ ] **Step 1: Delete `cli/` directory**

```bash
rm -rf cli/
```

- [ ] **Step 2: Build and verify all 19 tests pass**

```bash
nix build .#coolerctl -o result-cli 2>&1
nix log $(nix path-info --derivation .#coolerctl) 2>&1 | grep -E "(PASSED|FAILED|passed|failed)"
```

- [ ] **Step 3: Verify CLI works**

```bash
./result-cli/bin/coolerctl --version
./result-cli/bin/coolerctl --help
```

- [ ] **Step 4: Clean up and commit**

```bash
rm -f result-cli
git add -A
git commit -m "refactor(cli): restructure into coolerctl/ package with 17 modules"
```
