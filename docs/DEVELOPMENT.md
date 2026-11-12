# Development

```bash
git clone https://github.com/Daaboulex/coolercontrol-nix
cd coolercontrol-nix
nix develop
nix fmt
nix flake check --no-build
nix build .#coolercontrol-gui
nix build .#coolercontrol-ui-data
nix build .#coolercontrold
./result/bin/coolercontrold --help
```

| Command | What it does |
|---|---|
| `nix develop` | Enters the dev shell and installs the pre-commit hooks |
| `nix fmt` | Formats the flake, the module and the Home Manager module |
| `nix flake check --no-build` | Evaluation check |
| `nix build .#coolercontrol-gui` | Builds the full desktop app |
| `nix build .#coolercontrol-ui-data` | Builds the Vue web UI bundle |
| `nix build .#coolercontrold` | Builds the daemon only |

`nix build .#coolerctl` builds the CLI and runs its test suite.

## Layout

The packages, the overlay, both modules and the checks are wired together in
[`flake.nix`](../flake.nix).

| File | What it holds |
|---|---|
| [`coolercontrold.nix`](../coolercontrold.nix) | The daemon |
| [`coolercontrol-ui-data.nix`](../coolercontrol-ui-data.nix) | The web UI bundle |
| [`coolercontrol-gui.nix`](../coolercontrol-gui.nix) | The desktop app |
| [`coolerctl/`](../coolerctl/package.nix) | The CLI and its tests |
| [`module.nix`](../module.nix) | The NixOS module |
| [`hm-module.nix`](../hm-module.nix) | The Home Manager module |
| [`patches/`](../patches/qwebchannel-qrc-scheme.patch) | The desktop app's Qt WebEngine patch |

## Checks

- `export-config-is-valid-nix` imports the committed fixture of
  `coolerctl export-config`, so output a user cannot paste back fails the
  build. The CLI's own test suite fails if the generator and the fixture drift.
- `amdgpu-library-resolves` fails when nothing in the daemon's RUNPATH provides
  `libdrm_amdgpu.so.1`.
- `gpu-stress-libraries-resolve` does the same for `libvulkan.so.1` and
  `libEGL.so.1`.
- `qwebchannel-patch-still-needed` fails once upstream registers a URL scheme
  or stops loading `qwebchannel.js` from `qrc`, which is the signal to verify
  and drop the patch.
- `module-eval-nixos` evaluates the NixOS module with the overlay and
  `programs.coolercontrol.enable = true`.
- `module-eval-hm` evaluates the Home Manager module with
  `programs.coolercontrol.enable = true`. It needs no overlay.

The reasons behind the library and patch checks are in
[DESIGN.md](DESIGN.md).

## Upstream and updates

| | |
|---|---|
| Project | [coolercontrol/coolercontrol](https://gitlab.com/coolercontrol/coolercontrol) |
| License | GPL-3.0-or-later |
| Tracked | GitLab tags |

The tracked upstream version lives in [`flake.nix`](../flake.nix), next to the
source hash and the two dependency hashes. [`.github/update.json`](../.github/update.json)
names them (`hash`, `npmDepsHash`, `cargoHash`), and the packaging standard's
update workflow bumps them on each new GitLab tag.
