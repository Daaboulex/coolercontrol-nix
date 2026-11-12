# Design

Why the packaging is built the way it is. The [README](../README.md) says how
to use it.

## The parts

This flake packages CoolerControl from source and provides a NixOS module with
systemd integration and full hardware access.

| Package | Technology | What it does |
|---|---|---|
| `coolercontrold` | Rust | System daemon: hardware detection, fan and pump control, web UI server |
| `coolercontrol-ui-data` | Vue 3 / Vite | Web UI embedded in the daemon (`https://localhost:11987`) |
| `coolercontrol-gui` | C++ / Qt6 WebEngine | Desktop app wrapping the web UI, started as `coolercontrol` |
| `coolerctl` | Python | CLI wrapping the daemon's REST API |

All four are flake packages, and the overlay puts all four under
`pkgs.coolercontrol`. `packages.default` is the daemon. The daemon embeds the
built web UI, so it takes `coolercontrol-ui-data` as a build input.

## Two NixOS module paths

nixpkgs ships a `programs.coolercontrol` module that reads its packages from
`pkgs.coolercontrol`. The overlay nests every package under that path so it
slots into that module. Using the nixpkgs module with this flake's overlay is
the recommended path.

This flake's own module, [`module.nix`](../module.nix), declares the same
option path. It is a drop-in replacement with extra options, so it disables the
nixpkgs module (`disabledModules = [ "programs/coolercontrol.nix" ]`) to avoid
a duplicate declaration. Its default `coolerctl` package exists only in the
overlay, so the overlay stays in place on this path too.

What this module does beyond enabling the daemon:

- It installs the desktop app, and `coolerctl` unless `cli.enable` is off.
- It makes `/var/lib/coolercontrol` the unit's `StateDirectory`.
- It puts `which` and `stress-ng` on the daemon's path.
- It can seed a `config.toml` once, through `configFile`.

## Configuration directory

The daemon stores config, TLS certs, plugins, modes, alerts and sessions at
`/var/lib/coolercontrol/`. The package sets that in the installed systemd unit,
which gains `Environment="CC_CONFIG_DIR=/var/lib/coolercontrol"`. The edit is a
`substituteInPlace --replace-fail`, so a unit without a `[Service]` section
fails the build.

With this flake's NixOS module, systemd manages the path as the unit's
`StateDirectory`.

## Seeding a configuration file

With this flake's NixOS module, a configuration file can be seeded once:

```nix
{
  programs.coolercontrol.configFile = ./config.toml;
}
```

It is copied into `/var/lib/coolercontrol/` on a machine where the daemon has
not written its own `config.toml` yet. The copy is a systemd-tmpfiles `C` rule. The daemon owns the file from then on, so
a change to the option reaches only a machine that has none.

## Why Home Manager goes through the REST API

The daemon runs as a NixOS system service. The Home Manager module configures
the user-facing state that the web UI would normally manage, so it applies
that state through the daemon's REST API at login instead of writing the
daemon's files. The detail is in [HOME-MANAGER.md](HOME-MANAGER.md).

## Build settings

The daemon builds from upstream's source with no source patches.

### PCI ID database

The package sets `HWDATA_PKGDATADIR` to hwdata's store path, which upstream's
`daemon/build.rs` bakes into the binary as the place to read `pci.ids`.

### Libraries the daemon opens at run time

The daemon opens `libdrm_amdgpu.so.1` at run time, and its GPU stress test
opens `libvulkan.so.1` and `libEGL.so.1`. Nothing links them, so `buildInputs`
alone leaves the daemon unable to find them: AMD detection degrades, an RDNA3/4
card is never identified, and the stress test finds no GPU. The package adds
libdrm, vulkan-loader and libglvnd to the binary's RUNPATH. The checks
`amdgpu-library-resolves` and `gpu-stress-libraries-resolve` fail when the
RUNPATH stops providing them.

NVIDIA's NVML is found through `addDriverRunpath`. liquidctl reaches the daemon
through the Python path of its wrapper.

### Desktop app on Qt WebEngine 6.140

Qt WebEngine 6.140 made `qrc` a local scheme, so the UI, served by the daemon
over https, can no longer load `qrc:///qtwebchannel/qwebchannel.js`. Without it
no call between the UI and the app works: settings such as Start in tray and
the zoom neither load nor save, and with Start in tray on the window is never
drawn.

On Qt WebEngine 6.140 or newer the app carries
[`patches/qwebchannel-qrc-scheme.patch`](../patches/qwebchannel-qrc-scheme.patch),
which registers `qrc` as a secure, CORS-enabled scheme, the part of Qt's
documented restore that this script load needs. On older Qt it builds
unpatched.

The check `qwebchannel-patch-still-needed` fails once upstream registers a
scheme or loads the script another way, which is the signal to verify and drop
the patch. What was measured is in [COMPATIBILITY.md](COMPATIBILITY.md).

## Credits

- [Guy Boldon (codifryed)](https://gitlab.com/codifryed), CoolerControl
  developer
- [NixOS/nixpkgs coolercontrol package](https://github.com/NixOS/nixpkgs/tree/master/pkgs/applications/system/coolercontrol),
  reference packaging
