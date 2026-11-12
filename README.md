# CoolerControl for NixOS

[CoolerControl](https://gitlab.com/coolercontrol/coolercontrol) monitors and
controls your cooling devices (fans, pumps, AIOs) with a web UI and a desktop
app. This flake builds it from source for NixOS: the Rust daemon, the Vue web
UI and the Qt6 desktop app. It is for anyone who wants up-to-date CoolerControl
packages on NixOS, with fan curves declared in Home Manager if you like.

The flake targets `x86_64-linux` and `aarch64-linux`. The desktop app's fix for
Qt WebEngine 6.140 was measured on an Apple M1 Max and a Ryzen 9 9950X3D. Which
coolers and boards work is not recorded here.

## What you get

- `overlays.default` puts the packages under `pkgs.coolercontrol`, where the
  `programs.coolercontrol` module that nixpkgs ships reads them.
- `nixosModules.default` replaces the nixpkgs module and adds a few options.
- `homeModules.default` applies declared fan curves and settings at login.
- `coolerctl` is a command line tool for the daemon's REST API.

## Install

Add the flake:

```nix
{
  inputs.coolercontrol = {
    url = "github:Daaboulex/coolercontrol-nix";
    inputs.nixpkgs.follows = "nixpkgs";
  };
}
```

Then stack the overlay and switch CoolerControl on. nixpkgs already ships a
`programs.coolercontrol` module, and the overlay gives it up-to-date packages.

```nix
{
  nixpkgs.overlays = [ inputs.coolercontrol.overlays.default ];
  programs.coolercontrol.enable = true;
}
```

Rebuild with `sudo nixos-rebuild switch`. The daemon starts on its own.

To use this flake's module instead, also import
`inputs.coolercontrol.nixosModules.default`. Keep the overlay: the module's
default `coolerctl` package exists only there.

## First run

```bash
systemctl status coolercontrold
journalctl -u coolercontrold -f
```

The web UI is at `https://localhost:11987`, over TLS with a self-signed
certificate. Start the desktop app with `coolercontrol`.

The daemon starts with a default password, `coolAdmin`. Set your own, then save
a bearer token for `coolerctl` and the Home Manager module:

```bash
coolerctl auth set-password
coolerctl auth login
```

The token is saved to `~/.config/coolerctl/token`. Run `coolerctl auth login`
again after every password change.

## Command line

This flake's module installs `coolerctl`. With the nixpkgs module, add
`pkgs.coolercontrol.coolerctl` to `environment.systemPackages` or `home.packages`.

| Command | What it shows |
|---|---|
| `coolerctl status` | System overview |
| `coolerctl fans`, `coolerctl temps` | Fan speeds, temperatures |
| `coolerctl profiles list` | Profiles, and likewise `functions list` and `modes list` |
| `coolerctl auth status` | Whether a token is configured |
| `coolerctl export-config` | The current configuration as Nix, for Home Manager |

## Fan curves in Home Manager

```nix
{
  home-manager.sharedModules = [ inputs.coolercontrol.homeModules.default ];
}
```

A user service, `coolercontrol-apply.service`, sends what you declare to the
daemon at login. It needs the daemon running and the saved token. A full
example is in [docs/HOME-MANAGER.md](docs/HOME-MANAGER.md).

## Options you are likely to set

| Option | Module | What it is for |
|---|---|---|
| `configFile` | this flake's NixOS module | A `config.toml` copied into `/var/lib/coolercontrol/` once |
| `cli.enable` | this flake's NixOS module | Install `coolerctl`, on by default |
| `profiles`, `functions`, `modes` | Home Manager | The fan curves, functions and modes to apply |
| `activeMode` | Home Manager | The mode to activate at login |
| `settings` | Home Manager | Global daemon settings |

All sit under `programs.coolercontrol`. Every option, with its type and
default: [docs/OPTIONS.md](docs/OPTIONS.md).

## Known limits

- `configFile` only seeds a machine whose daemon has no `config.toml` yet.
- The Home Manager module needs a saved token, renewed after a password change.
- `duty_minimum` on a function must be at least 1.
- Motherboard fan headers need a Super I/O kernel module. Which one is in
  [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## When something does not work

```bash
systemctl --user status coolercontrol-apply
journalctl --user -u coolercontrol-apply -e
systemctl --user restart coolercontrol-apply
```

The log shows the exact HTTP error. A 401 means the token is stale, so run
`coolerctl auth login`. "CoolerControl daemon not reachable after 30s" means
the daemon is not running, so check `systemctl status coolercontrold`. The
other errors are listed in [docs/HOME-MANAGER.md](docs/HOME-MANAGER.md).

## More

- [docs/HOME-MANAGER.md](docs/HOME-MANAGER.md): a full example, the API's rules
- [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md): hardware, kernel modules, migration
- [docs/DESIGN.md](docs/DESIGN.md): the two module paths, build settings, credits
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): building, the checks, updates

## License

[`LICENSE`](LICENSE) holds the GNU General Public License version 3, and the `meta.license` of each of the four packages (`coolercontrold`, `coolercontrol-ui-data`, `coolercontrol-gui`, `coolerctl`) declares `gpl3Plus`, which is GPL-3.0-or-later. Upstream CoolerControl is [GPL-3.0-or-later](https://gitlab.com/coolercontrol/coolercontrol/-/blob/main/LICENSE) by Guy Boldon.
