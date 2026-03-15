# coolercontrol-nix

NixOS packaging for [CoolerControl](https://gitlab.com/coolercontrol/coolercontrol) — monitor and control your cooling devices (fans, pumps, AIOs) with a modern web UI and desktop app.

This flake packages CoolerControl **v4.0.1** from source (Rust daemon + Vue web UI + Qt6 desktop app) and provides a NixOS module with systemd integration and full hardware access.

> **Note**: This is a community packaging effort. CoolerControl is developed by [Guy Boldon](https://gitlab.com/codifryed).
> nixpkgs ships an older version (3.1.1) — this flake tracks the latest upstream release.

## Components

| Component | Technology | Description |
|---|---|---|
| `coolercontrold` | Rust | System daemon — hardware detection, fan/pump control, web UI server, liquidctl integration |
| `coolercontrol-ui` | Vue 3 / Vite | Web UI embedded in the daemon (served at `https://localhost:11987`) |
| `coolercontrol` (GUI) | C++ / Qt6 WebEngine | Desktop app wrapping the web UI with system tray integration |

## Usage

### 1. Add flake input

```nix
# flake.nix
inputs.coolercontrol = {
  url = "github:daaboulex/coolercontrol-nix";
  inputs.nixpkgs.follows = "nixpkgs";
};
```

### 2. Stack the overlay

```nix
nixpkgs.overlays = [
  inputs.coolercontrol.overlays.default
];
```

### 3. Import the NixOS module

```nix
imports = [
  inputs.coolercontrol.nixosModules.default
];
```

### 4. Enable CoolerControl

```nix
programs.coolercontrol.enable = true;
```

## NixOS module options

| Option | Type | Default | Description |
|---|---|---|---|
| `programs.coolercontrol.enable` | bool | `false` | Enable CoolerControl daemon and GUI |
| `programs.coolercontrol.package` | package | `pkgs.coolercontrol.coolercontrold` | The coolercontrold package to use |
| `programs.coolercontrol.guiPackage` | package | `pkgs.coolercontrol.coolercontrol-gui` | The CoolerControl GUI package to use |

## What gets installed

- **System service**: `coolercontrold.service` — runs the daemon as root with access to hwmon, NVIDIA (NVML), AMD (libdrm), and liquidctl devices
- **Desktop app**: `coolercontrol` binary with `.desktop` file and icons — launch from your application menu
- **Web UI**: Available at `https://localhost:11987` (TLS enabled by default in v4.0+)
- **GPU driver access**: `addDriverRunpath` ensures the daemon can detect NVIDIA/AMD GPUs at runtime
- **PCI device names**: `hwdata` is patched into the vendored `pciid-parser` crate at build time so the daemon can resolve PCI IDs to human-readable device names on NixOS

## Hardware support

CoolerControl detects and controls devices through:

- **hwmon** — kernel hardware monitoring (CPU/GPU temps, fan speeds, PWM control)
- **liquidctl** — USB liquid coolers, fan controllers (Corsair, NZXT, EVGA, etc.)
- **libdrm** — AMD GPU temperature and fan control
- **NVML** — NVIDIA GPU monitoring (auto-loaded via `addDriverRunpath`)

### Kernel modules for motherboard fan control

CoolerControl can only see fans exposed by loaded hwmon drivers. GPU fans (amdgpu/nvidia) are auto-detected, but **motherboard fan headers require the appropriate Super I/O kernel module** to be loaded. Without it, CoolerControl will only show GPU fans.

Most motherboards use a Nuvoton or ITE Super I/O chip. Add the correct module to your NixOS config:

```nix
# Nuvoton (most ASUS, MSI, Gigabyte boards — NCT6775/6776/6779/6791/6796/6798/6799)
boot.kernelModules = [ "nct6775" ];

# ITE (some Gigabyte, ASRock boards — IT8688E, IT8689E, etc.)
boot.kernelModules = [ "it87" ];
```

You may also need this kernel parameter for ASUS boards (allows the driver to access ACPI-claimed I/O ports):

```nix
boot.kernelParams = [ "acpi_enforce_resources=lax" ];
```

To identify your chip, run `sudo modprobe nct6775 && sensors` or `sudo modprobe it87 && sensors` and check which one exposes fan readings. See the [CoolerControl hardware support docs](https://docs.coolercontrol.org/hardware-support.html) for details.

## Verification

After rebuilding:

```bash
# Check the service is running
systemctl status coolercontrold

# View daemon logs
journalctl -u coolercontrold -f

# Open the web UI
xdg-open https://localhost:11987

# Launch the desktop app
coolercontrol
```

## CLI usage

The `coolerctl` CLI wraps the daemon's REST API for scripting and automation:

```bash
# List detected devices and their channels
coolerctl devices list

# Show current temperatures
coolerctl temps

# Show fan speeds
coolerctl fans

# Watch live status stream
coolerctl watch-status

# List profiles (fan curves)
coolerctl profiles list

# Create a profile with a fixed speed
coolerctl profiles create --name "Silent" --speed-fixed 30

# Create a profile with a temperature curve
coolerctl profiles create --name "Custom" \
  --speed-profile '[{"temp": 30, "duty": 20}, {"temp": 60, "duty": 50}, {"temp": 80, "duty": 100}]'

# List and activate modes
coolerctl modes list
coolerctl modes activate <mode-uid>

# List functions
coolerctl functions list

# Manage alerts
coolerctl alerts list
coolerctl alerts create --channel "CPU" --threshold 90

# Show global settings
coolerctl settings show

# Authenticate (if daemon has a password set)
coolerctl auth login
```

## Home Manager module

Declaratively configure CoolerControl profiles, functions, modes, alerts, and settings through Home Manager. The daemon runs as a NixOS system service — this module applies user-facing state via the REST API on login.

### Import

```nix
# In your flake, add to Home Manager sharedModules:
home-manager.sharedModules = [
  inputs.coolercontrol.homeManagerModules.default
];
```

### Example configuration

```nix
programs.coolercontrol = {
  enable = true;

  # Connect to daemon (HTTPS with self-signed cert by default)
  url = "https://localhost:11987";

  # Fan curve profiles
  profiles.silent = {
    uid = "abc123";  # from coolerctl profiles list
    name = "Silent";
    p_type = "Fixed";
    speed_fixed = 30;
  };

  profiles.gaming = {
    uid = "def456";
    name = "Gaming";
    p_type = "Graph";
    speed_profile = [
      { temp = 30; duty = 25; }
      { temp = 50; duty = 40; }
      { temp = 70; duty = 70; }
      { temp = 85; duty = 100; }
    ];
    extra.function_uid = "ghi789";
  };

  # Response functions — control how profiles react to temperature changes
  functions.smooth = {
    uid = "ghi789";
    name = "Smooth Response";
    duty_minimum = 20;
    duty_maximum = 100;
    response_delay = 3;     # seconds before reacting
    deviance = 2;            # °C hysteresis
    only_downward = false;   # allow speed increases
    sample_window = 6;       # average temps over N seconds
  };

  # Modes — assign profiles to specific device channels
  modes.default = {
    uid = "jkl012";
    name = "Default Mode";
    device_settings = {
      "<device-uid>" = {
        "fan1" = { profile_uid = "abc123"; };
      };
    };
  };

  # Activate a mode on login
  activeMode = "jkl012";

  # Temperature alerts
  alerts = [
    { channel = "CPU"; threshold_celsius = 95; trigger = "above"; }
  ];

  # Global daemon settings (all 11 fields)
  settings = {
    apply_on_boot = true;          # re-apply profiles on boot
    no_init = false;               # skip device init (debugging only)
    startup_delay = 2;             # seconds to wait before applying
    thinkpad_full_speed = false;   # ThinkPad fan override
    handle_dynamic_temps = false;  # handle hotplug temp sources
    liquidctl_integration = true;  # enable liquidctl for AIOs
    hide_duplicate_devices = true; # hide duplicate device entries
    compress = true;               # compress API responses
    poll_rate = 1.0;               # sensor poll interval (0.5-5.0s)
    drivetemp_suspend = true;      # skip drivetemp when drive sleeping
    allow_unencrypted = false;     # require HTTPS
  };

  # Additional commands after config is applied
  extraCommands = [ ];
};
```

The module creates a systemd user service (`coolercontrol-apply.service`) that waits for the daemon to become reachable, then applies all declared configuration via the REST API.

## Exporting configuration

The `coolerctl` CLI can snapshot the daemon's current state as a Nix attrset for direct use in Home Manager:

```bash
# Recommended: Using the built-in CLI command
coolerctl export-config

# Or use the standalone script
./export-config.sh

# With password authentication
coolerctl --base-url https://localhost:11987 export-config  # CLI will use saved token
./export-config.sh --password <password>
```

The output documents all devices, profiles, functions, modes, alerts, custom sensors, and global settings. It is designed to be 1:1 compatible with the Home Manager module — you can copy and paste the output directly into your configuration.

## Home Manager options reference

### Top-level options

| Option | Type | Default | Description |
|---|---|---|---|
| `enable` | bool | `false` | Enable declarative CoolerControl configuration |
| `url` | str | `"https://localhost:11987"` | Daemon HTTPS endpoint |
| `profiles` | attrsOf submodule | `{}` | Fan curve profiles |
| `functions` | attrsOf submodule | `{}` | Response function definitions |
| `modes` | attrsOf submodule | `{}` | Device-channel-profile assignments |
| `activeMode` | nullOr str | `null` | Mode UID to activate on login |
| `alerts` | listOf submodule | `[]` | Temperature threshold alerts |
| `settings` | nullOr submodule | `null` | Global daemon settings |
| `extraCommands` | listOf str | `[]` | Additional commands after applying config |

### Profile submodule

| Option | Type | Default | Description |
|---|---|---|---|
| `uid` | str | — | Daemon-assigned UUID |
| `name` | str | — | Display name |
| `p_type` | str | — | Profile type: `"Default"`, `"Fixed"`, `"Graph"`, `"Mix"` |
| `speed_fixed` | int | `0` | Fixed duty percentage (for `"Fixed"` type) |
| `speed_profile` | listOf {temp, duty} | `[]` | Temperature curve points (for `"Graph"` type) |
| `extra` | attrs | `{}` | Additional fields (e.g. `function_uid`) |

### Function submodule

| Option | Type | Default | Description |
|---|---|---|---|
| `uid` | str | — | Daemon-assigned UUID |
| `name` | str | — | Display name |
| `duty_minimum` | int | `0` | Minimum fan duty % |
| `duty_maximum` | int | `100` | Maximum fan duty % |
| `response_delay` | int | `0` | Seconds before responding to temp change |
| `deviance` | int | `0` | Temperature hysteresis in °C |
| `only_downward` | bool | `false` | Only allow downward speed changes |
| `sample_window` | int | `0` | Temperature averaging window in seconds |
| `extra` | attrs | `{}` | Additional fields |

### Mode submodule

| Option | Type | Default | Description |
|---|---|---|---|
| `uid` | str | — | Daemon-assigned UUID |
| `name` | str | — | Display name |
| `device_settings` | attrsOf (attrsOf attrs) | `{}` | Device UID → channel → profile assignment |
| `extra` | attrs | `{}` | Additional fields |

### Alert submodule

| Option | Type | Default | Description |
|---|---|---|---|
| `channel` | str | — | Temperature source channel name |
| `threshold_celsius` | int | — | Trigger temperature in °C |
| `trigger` | str | `"above"` | Trigger direction: `"above"` or `"below"` |
| `extra` | attrs | `{}` | Additional fields |

### Settings submodule

| Option | Type | Default | Description |
|---|---|---|---|
| `apply_on_boot` | bool | `true` | Re-apply profiles/modes on system boot |
| `no_init` | bool | `false` | Skip device initialisation on daemon start |
| `startup_delay` | int | `2` | Seconds to wait after boot before applying |
| `thinkpad_full_speed` | bool | `false` | Allow fans to exceed firmware limits (ThinkPad only) |
| `handle_dynamic_temps` | bool | `false` | Handle dynamically appearing temp sources |
| `liquidctl_integration` | bool | `true` | Enable liquidctl for AIO coolers |
| `hide_duplicate_devices` | bool | `true` | Hide duplicate device entries |
| `compress` | bool | `true` | Compress API responses |
| `poll_rate` | float | `1.0` | Sensor polling interval in seconds (0.5-5.0) |
| `drivetemp_suspend` | bool | `true` | Suspend drivetemp monitoring during disk sleep |
| `allow_unencrypted` | bool | `false` | Allow unencrypted HTTP connections |

## NixOS-specific patches

### PCI ID database

The upstream `pciid-parser` Rust crate hardcodes Linux FHS paths (`/usr/share/hwdata/pci.ids`) which don't exist on NixOS. This flake patches the vendored crate at build time to substitute the `@hwdata@` placeholder with the Nix store path to `hwdata`, enabling proper PCI device name resolution.

## Version tracking

This flake includes a GitHub Actions workflow that checks for new upstream releases twice per week (Monday/Thursday) and creates an issue when an update is available.

## Repository structure

```
coolercontrol-nix/
├── flake.nix                  # Flake definition (packages, overlay, modules)
├── coolercontrold.nix         # Rust daemon package
├── coolercontrol-ui-data.nix  # Vue web UI build
├── coolercontrol-gui.nix      # Qt6 desktop app package
├── module.nix                 # NixOS module (systemd service + GUI)
├── hm-module.nix              # Home Manager module (declarative API config)
├── export-config.sh           # Export daemon state as Nix attrset
├── cli/                       # coolerctl CLI (Python, wraps REST API)
├── README.md
├── LICENSE
└── .github/
    └── workflows/
        └── check-upstream.yml # Automated upstream release tracking
```

## CLI Utility

A Python-based CLI `coolerctl` is provided for interacting with the daemon from the command line.

```bash
# Login to get a token
coolerctl auth login

# Export current daemon state to Nix (Home Manager)
coolerctl export-config

# Quick status
coolerctl status
coolerctl fans
coolerctl temps
```

## Known Issues

- **Plugins**: The Plugins tab in the GUI may be empty. This is because the daemon's plugin loading mechanism currently expects plugins in standard FHS locations (like `/usr/lib/coolercontrol`), which are not present on NixOS. A future update will patch the daemon to support Nix-native plugin paths.
- **PCI Device Names**: Resolved via a patch to `pciid-parser` that points to the Nix store `hwdata` path.

## Credits

- [Guy Boldon (codifryed)](https://gitlab.com/codifryed) — CoolerControl developer
- [NixOS/nixpkgs coolercontrol package](https://github.com/NixOS/nixpkgs/tree/master/pkgs/applications/system/coolercontrol) — reference packaging by codifryed and OPNA2608

## License

CoolerControl is licensed under [GPL-3.0-or-later](https://www.gnu.org/licenses/gpl-3.0.html) by Guy Boldon.
The Nix packaging expressions in this repository are also licensed under GPL-3.0-or-later — see [LICENSE](LICENSE).
