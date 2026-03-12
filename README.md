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

## Version tracking

This flake includes a GitHub Actions workflow that checks for new upstream releases twice per week (Monday/Thursday) and creates an issue when an update is available.

## Repository structure

```
coolercontrol-nix/
├── flake.nix                  # Flake definition (packages, overlay, module)
├── coolercontrold.nix         # Rust daemon package
├── coolercontrol-ui-data.nix  # Vue web UI build
├── coolercontrol-gui.nix      # Qt6 desktop app package
├── module.nix                 # NixOS module (systemd service + GUI)
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
