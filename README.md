# coolercontrol-nix

NixOS packaging for [CoolerControl](https://gitlab.com/coolercontrol/coolercontrol) — monitor and control your cooling devices (fans, pumps, AIOs) with a modern web UI and desktop app.

This flake packages CoolerControl **v4.1.0** from source (Rust daemon + Vue web UI + Qt6 desktop app) and provides a NixOS module with systemd integration and full hardware access.

> **Note**: This is a community packaging effort. CoolerControl is developed by [Guy Boldon](https://gitlab.com/codifryed).
> nixpkgs ships an older version — this flake tracks the latest upstream release.

## Quick Start

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

### 3. Enable CoolerControl

nixpkgs already ships a `programs.coolercontrol` NixOS module. With the overlay providing up-to-date packages, just enable it:

```nix
programs.coolercontrol.enable = true;
```

> **Alternative**: If you prefer to use this flake's NixOS module instead of nixpkgs', import `inputs.coolercontrol.nixosModules.default` and skip step 2.

### 4. (Optional) Add the Home Manager module

For declarative profiles, modes, functions, alerts, and settings:

```nix
home-manager.sharedModules = [
  inputs.coolercontrol.homeManagerModules.default
];
```

### 5. Rebuild

```bash
sudo nixos-rebuild switch
```

## Post-Install Setup

### First run

After rebuilding, the daemon starts automatically. Verify:

```bash
systemctl status coolercontrold
journalctl -u coolercontrold -f
```

The web UI is at `https://localhost:11987` (TLS with self-signed cert). Launch the desktop app with `coolercontrol`.

### Authentication

The daemon starts with a default password (`coolAdmin`). To set your own:

```bash
coolerctl auth set-password
# Current password: coolAdmin
# New password: <your password>
```

Then save a bearer token for CLI and Home Manager use:

```bash
coolerctl auth login
# Password: <your password>
# Token saved to ~/.config/coolerctl/token
```

The Home Manager apply service reads this token automatically. **You must run `coolerctl auth login` after every password change.**

### Configuration directory

The daemon stores config, TLS certs, plugins, modes, alerts, and sessions at `/var/lib/coolercontrol/` (set via `CC_CONFIG_DIR` in the systemd unit). This path is managed by systemd's `StateDirectory`.

> **Migrating from an older version**: If you previously ran CoolerControl without this flake, your config may be at `/etc/coolercontrol/`. Copy it over:
> ```bash
> sudo systemctl stop coolercontrold
> sudo cp -a /etc/coolercontrol/* /var/lib/coolercontrol/
> sudo systemctl start coolercontrold
> ```

## Components

| Component | Technology | Description |
|---|---|---|
| `coolercontrold` | Rust | System daemon — hardware detection, fan/pump control, web UI server |
| `coolercontrol-ui` | Vue 3 / Vite | Web UI embedded in the daemon (`https://localhost:11987`) |
| `coolercontrol` (GUI) | C++ / Qt6 WebEngine | Desktop app wrapping the web UI |
| `coolerctl` | Python | CLI wrapping the daemon's REST API |

## CLI usage

The `coolerctl` CLI wraps the daemon's REST API. It's installed automatically when `myModules.home.coolercontrol.enable = true`.

```bash
# Authentication
coolerctl auth login              # Save bearer token
coolerctl auth set-password       # Change daemon password
coolerctl auth status             # Check if token is configured

# Quick status
coolerctl status                  # System overview
coolerctl fans                    # Fan speeds
coolerctl temps                   # Temperatures

# Profiles & functions
coolerctl profiles list
coolerctl functions list
coolerctl modes list

# Export current config as Nix (for Home Manager)
coolerctl export-config
```

## Home Manager Module

Declaratively configure CoolerControl profiles, functions, modes, alerts, and settings. The daemon runs as a NixOS system service — this module applies state via the REST API on login.

### How it works

1. You declare profiles/functions/modes/settings in Nix
2. On login, a systemd user service (`coolercontrol-apply.service`) sends them to the daemon via REST API
3. The daemon persists changes to `/var/lib/coolercontrol/`

**Prerequisites**:
- The daemon must be running (`programs.coolercontrol.enable = true`)
- A bearer token must exist at `~/.config/coolerctl/token` (run `coolerctl auth login`)

### Debugging the apply service

```bash
# Check status
systemctl --user status coolercontrol-apply

# View logs (shows exact HTTP errors with status codes)
journalctl --user -u coolercontrol-apply -e

# Manually re-apply after fixing config
systemctl --user restart coolercontrol-apply
```

Common errors:
- **HTTP 401 "Invalid Credentials"**: Run `coolerctl auth login` to refresh the token
- **HTTP 400 "duty_minimum must be greater than 0"**: `duty_minimum` must be >= 1 in 4.1.0+
- **HTTP 422 "missing field X"**: A required field was not provided (check the example below)
- **"Daemon not reachable after 30s"**: The daemon isn't running — check `systemctl status coolercontrold`

### Example configuration

```nix
# home/hosts/<hostname>/coolercontrol/default.nix
{
  myModules.home.coolercontrol.settings = {
    enable = true;

    profiles = {
      default-profile = {
        uid = "0";
        name = "Default Profile";
        p_type = "Default";
        extra = {
          function_uid = "0";  # Required in 4.1.0+
        };
      };
      my-profile = {
        uid = "abc123";  # from coolerctl profiles list
        name = "Silent";
        p_type = "Graph";
        speed_profile = [
          { temp = 30; duty = 25; }
          { temp = 50; duty = 40; }
          { temp = 70; duty = 70; }
          { temp = 85; duty = 100; }
        ];
        extra = {
          function_uid = "def456";
        };
      };
    };

    functions = {
      default-function = {
        uid = "0";
        name = "Default Function";
        duty_minimum = 1;   # Must be >= 1 in 4.1.0+
        duty_maximum = 100;
      };
      my-function = {
        uid = "def456";
        name = "Smooth Response";
        duty_minimum = 2;
        duty_maximum = 100;
        response_delay = 3;
        deviance = 2.0;
        only_downward = false;
        sample_window = 6;
      };
    };

    modes = {
      default = {
        uid = "jkl012";
        name = "Default Mode";
        device_settings = {
          "<device-uid>" = {
            "fan1" = { profile_uid = "abc123"; };
          };
        };
      };
    };

    # Activate a mode on login
    activeMode = "jkl012";

    # Global daemon settings
    settings = {
      apply_on_boot = true;
      no_init = false;
      startup_delay = 2;
      thinkpad_full_speed = false;
      handle_dynamic_temps = false;
      liquidctl_integration = true;
      hide_duplicate_devices = true;
      compress = true;
      poll_rate = 1.0;
      drivetemp_suspend = true;
      allow_unencrypted = false;
    };
  };
}
```

### Exporting current config

Use `coolerctl export-config` to snapshot the daemon's current state as a Nix attrset. Copy the output directly into your Home Manager configuration.

### 4.1.0 API requirements

The 4.1.0 API is stricter than 4.0.x. Key differences:

| Field | Requirement |
|---|---|
| `function_uid` | Required on profiles (use `extra.function_uid`) |
| `duty_minimum` | Must be >= 1 (was allowed to be 0) |
| `member_profile_uids` | Required on profiles (defaults to `[]`) |
| `f_type` | Required on functions (defaults to `"Identity"`) |
| Bearer token | Required for write operations when password is set |

## Hardware Support

CoolerControl detects and controls devices through:

- **hwmon** — kernel hardware monitoring (CPU/GPU temps, fan speeds, PWM control)
- **liquidctl** — USB liquid coolers, fan controllers (Corsair, NZXT, EVGA, etc.)
- **libdrm** — AMD GPU temperature and fan control
- **NVML** — NVIDIA GPU monitoring (auto-loaded via `addDriverRunpath`)

### Kernel modules for motherboard fan control

Motherboard fan headers require the appropriate Super I/O kernel module:

```nix
# Nuvoton (most ASUS, MSI, Gigabyte boards)
boot.kernelModules = [ "nct6775" ];

# ITE (some Gigabyte, ASRock boards)
boot.kernelModules = [ "it87" ];
```

ASUS boards may also need:

```nix
boot.kernelParams = [ "acpi_enforce_resources=lax" ];
```

## NixOS-Specific Patches

### PCI ID database

The daemon's inline `pci_ids` module hardcodes Linux FHS paths for `pci.ids`. This flake patches the `@hwdata@` placeholder at build time with the Nix store path to `hwdata`.

### Configuration directory

The systemd unit sets `CC_CONFIG_DIR=/var/lib/coolercontrol` so the daemon works with `ProtectSystem=strict` (can't write to `/etc`). All config, plugins, TLS certs, and sessions are stored there.

## Version Tracking

GitHub Actions workflows automatically update to new upstream releases twice per week (Monday/Thursday). Successful updates are pushed directly to main; failures create a GitHub Issue with build logs and recovery steps.

## Repository Structure

```
coolercontrol-nix/
├── flake.nix                  # Flake definition (packages, overlay, modules)
├── coolercontrold.nix         # Rust daemon package
├── coolercontrol-ui-data.nix  # Vue web UI build
├── coolercontrol-gui.nix      # Qt6 desktop app package
├── module.nix                 # NixOS module (alternative to nixpkgs module)
├── hm-module.nix              # Home Manager module (declarative API config)
├── export-config.sh           # Export daemon state as Nix attrset
├── coolerctl/                 # coolerctl CLI (Python, wraps REST API)
├── scripts/update.sh          # Standardized auto-update script
├── .github/update.json        # Update configuration (upstream, hashes, verify)
├── README.md
├── LICENSE
└── .github/workflows/
    ├── ci.yml                 # PR/push: eval, format, build, verify
    ├── update.yml             # Scheduled: detect upstream, update hashes, push or issue
    └── maintenance.yml        # Weekly: flake.lock update, stale branch cleanup
```

## Credits

- [Guy Boldon (codifryed)](https://gitlab.com/codifryed) — CoolerControl developer
- [NixOS/nixpkgs coolercontrol package](https://github.com/NixOS/nixpkgs/tree/master/pkgs/applications/system/coolercontrol) — reference packaging

## License

CoolerControl is licensed under [GPL-3.0-or-later](https://www.gnu.org/licenses/gpl-3.0.html) by Guy Boldon.
The Nix packaging expressions in this repository are also licensed under GPL-3.0-or-later — see [LICENSE](LICENSE).
