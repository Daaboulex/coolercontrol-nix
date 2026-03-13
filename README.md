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

## Module Options

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
# flake.nix
inputs.coolercontrol.url = "github:daaboulex/coolercontrol-nix";

# home configuration
imports = [
  inputs.coolercontrol.homeManagerModules.default
];
```

### Example configuration

```nix
programs.coolercontrol = {
  enable = true;

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
  };

  functions.smooth = {
    uid = "ghi789";
    name = "Smooth Response";
    duty_minimum = 20;
    duty_maximum = 100;
    response_delay = 3;
    deviance = 2.0;
    only_downward = true;
    sample_window = 6;
  };

  modes.default = {
    uid = "jkl012";
    name = "Default Mode";
    device_settings = {
      "<device-uid>" = {
        "fan1" = { profile_uid = "abc123"; };
      };
    };
  };

  activeMode = "jkl012";

  settings = {
    apply_on_boot = true;
    handle_dynamic_temps = true;
    startup_delay = 2;
  };

  alerts = [
    { channel = "CPU"; threshold_celsius = 95; trigger = "above"; }
  ];
};
```

The module creates a systemd user service (`coolercontrol-apply.service`) that waits for the daemon to become reachable, then applies all declared configuration via the REST API.

## Exporting configuration

Use `export-config.sh` to snapshot the daemon's current state as a Nix attrset:

```bash
# Export from local daemon
./export-config.sh

# Export from a remote instance
./export-config.sh --url http://192.168.1.100:11987

# With authentication
./export-config.sh --token <bearer-token>
COOLERCONTROL_TOKEN=xxx ./export-config.sh
```

The output documents all devices, profiles, functions, modes, alerts, custom sensors, and global settings. Use it as a reference when writing your Home Manager configuration — copy UIDs and settings from the export.

## Home Manager options

| Option | Type | Default | Description |
|---|---|---|---|
| `programs.coolercontrol.enable` | bool | `false` | Enable declarative CoolerControl configuration |
| `programs.coolercontrol.url` | str | `"http://localhost:11987"` | Daemon URL |
| `programs.coolercontrol.profiles` | attrsOf submodule | `{}` | Fan curve profiles (uid, name, p_type, speed_fixed/speed_profile) |
| `programs.coolercontrol.functions` | attrsOf submodule | `{}` | Function definitions (uid, name, duty_minimum, duty_maximum, response_delay, deviance, only_downward, sample_window) |
| `programs.coolercontrol.modes` | attrsOf submodule | `{}` | Mode definitions (uid, name, device_settings) |
| `programs.coolercontrol.activeMode` | nullOr str | `null` | Mode UID to activate on login |
| `programs.coolercontrol.alerts` | listOf submodule | `[]` | Alert definitions (channel, threshold_celsius, trigger) |
| `programs.coolercontrol.settings` | nullOr submodule | `null` | Global daemon settings (apply_on_boot, thinkpad_full_speed, handle_dynamic_temps, startup_delay) |
| `programs.coolercontrol.extraCommands` | listOf str | `[]` | Additional shell commands to run after applying configuration |

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

## Credits

- [Guy Boldon (codifryed)](https://gitlab.com/codifryed) — CoolerControl developer
- [NixOS/nixpkgs coolercontrol package](https://github.com/NixOS/nixpkgs/tree/master/pkgs/applications/system/coolercontrol) — reference packaging by codifryed and OPNA2608

## License

CoolerControl is licensed under [GPL-3.0-or-later](https://www.gnu.org/licenses/gpl-3.0.html) by Guy Boldon.
The Nix packaging expressions in this repository are also licensed under GPL-3.0-or-later — see [LICENSE](LICENSE).
