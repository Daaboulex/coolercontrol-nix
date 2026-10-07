{
  description = "CoolerControl — monitor and control your cooling devices on NixOS";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    git-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    std = {
      url = "github:Daaboulex/nix-packaging-standard?ref=v2.40.1";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.git-hooks.follows = "git-hooks";
    };
  };

  outputs =
    inputs@{ flake-parts, self, ... }:
    let
      # Upstream version, source, and per-language dependency hashes.
      # scripts/update.sh bumps these in place on each new GitLab tag
      # (.github/update.json names them: hash, npmDepsHash, cargoHash).
      version = "5.0.1";
      mkSrc =
        p:
        p.fetchFromGitLab {
          owner = "coolercontrol";
          repo = "coolercontrol";
          rev = version;
          hash = "sha256-48hgLZ1tyojGJFsz9ZQKC03QMrUAFuH33Z/LOXYl/aI=";
        };
      npmDepsHash = "sha256-7yYI4tAoCeZvm4x5BGUN/bnDExKqxrM9VOD+tO1C6Hc=";
      cargoHash = "sha256-tbGNVyYrTRmxOqVM7mjNgwZXXcUY205mKuFjrptr+m4=";
    in
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];

      imports = [ inputs.std.flakeModules.base ];

      # The overlay nests every output under `pkgs.coolercontrol.*` so it slots
      # into nixpkgs' own `programs.coolercontrol` module (which reads that path).
      flake.overlays.default = final: _prev: {
        coolercontrol =
          let
            src = mkSrc final;
            coolercontrol-ui-data = final.callPackage ./coolercontrol-ui-data.nix {
              inherit version src npmDepsHash;
            };
          in
          {
            inherit coolercontrol-ui-data;
            coolercontrold = final.callPackage ./coolercontrold.nix {
              inherit
                version
                src
                cargoHash
                coolercontrol-ui-data
                ;
            };
            coolercontrol-gui = final.callPackage ./coolercontrol-gui.nix { inherit version src; };
            coolerctl = final.callPackage ./coolerctl/package.nix { };
          };
      };
      flake.nixosModules.default = import ./module.nix;
      flake.homeModules.default = import ./hm-module.nix;

      perSystem =
        {
          system,
          pkgs,
          self',
          ...
        }:
        let
          src = mkSrc pkgs;
        in
        {
          # A unified diff's context lines are byte-exact; a formatter that trims
          # them silently breaks the patch, so the fixers leave .patch alone.
          pre-commit.settings.hooks = {
            trim-trailing-whitespace.excludes = [ "\\.patch$" ];
            end-of-file-fixer.excludes = [ "\\.patch$" ];
            typos.excludes = [ "\\.patch$" ];
          };

          packages.coolercontrol-ui-data = pkgs.callPackage ./coolercontrol-ui-data.nix {
            inherit version src npmDepsHash;
          };
          # The daemon embeds the built web UI, so it consumes ui-data directly.
          packages.coolercontrold = pkgs.callPackage ./coolercontrold.nix {
            inherit version src cargoHash;
            inherit (self'.packages) coolercontrol-ui-data;
          };
          packages.coolercontrol-gui = pkgs.callPackage ./coolercontrol-gui.nix { inherit version src; };
          packages.coolerctl = pkgs.callPackage ./coolerctl/package.nix { };
          packages.default = self'.packages.coolercontrold;

          # `coolerctl export-config` must emit Nix a user can paste back.
          # Importing its committed fixture makes that a build-time property --
          # a bad quote fails to parse, an unescaped ${...} fails to evaluate --
          # and the CLI's own test suite fails if generator and fixture drift.
          checks.export-config-is-valid-nix =
            let
              exported = import ./coolerctl/export-config.golden;
            in
            pkgs.runCommand "export-config-is-valid-nix" { } ''
              test "${builtins.deepSeq exported "ok"}" = ok
              touch "$out"
            '';

          # patches/i2c-client-identity.patch is a divergence from upstream, so it
          # carries its own retirement. Upstream's identity file names i2c nowhere
          # today; the moment it does, upstream is handling this itself and the
          # patch is reviewed and dropped. The patch's own application is the other
          # half: it fails the build outright if the code it edits moves.
          # The daemon reaches libdrm through libdrm_amdgpu_sys, which dlopens
          # libdrm_amdgpu.so.1, so nothing links it and buildInputs alone leaves
          # it unresolvable: AMD detection degrades and an RDNA3/4 card is never
          # identified, with only a warning in the log to say so.
          checks.amdgpu-library-resolves =
            pkgs.runCommand "amdgpu-library-resolves"
              {
                nativeBuildInputs = [ pkgs.patchelf ];
                daemon = self'.packages.coolercontrold;
              }
              ''
                bin="$daemon/bin/.coolercontrold-wrapped"
                [ -f "$bin" ] || bin="$daemon/bin/coolercontrold"
                if [ ! -f "$bin" ]; then
                  echo "::error::no coolercontrold binary at $daemon/bin to inspect"
                  exit 1
                fi

                found=""
                for dir in $(patchelf --print-rpath "$bin" | tr ':' ' '); do
                  if [ -e "$dir/libdrm_amdgpu.so.1" ]; then
                    found="$dir"
                  fi
                done

                if [ -z "$found" ]; then
                  echo "::error::the daemon dlopens libdrm_amdgpu.so.1 and nothing in its RUNPATH provides it, so AMD detection degrades and an RDNA3/4 card is never identified"
                  exit 1
                fi

                touch "$out"
              '';

          checks.i2c-patch-still-needed = pkgs.runCommand "i2c-patch-still-needed" { inherit src; } ''
            file="$src/coolercontrold/daemon/src/repositories/hwmon/devices.rs"
            if grep -qi i2c "$file"; then
              echo "Upstream's device identity now names i2c:"
              grep -in i2c "$file" | head -5
              echo ""
              echo "The local divergence may be redundant. Verify that an i2c client's"
              echo "identity no longer carries the kernel-assigned bus number, then delete"
              echo "patches/i2c-client-identity.patch, its entry in coolercontrold.nix, and"
              echo "this check."
              exit 1
            fi
            touch "$out"
          '';
          checks.macsmc-patch-still-needed = pkgs.runCommand "macsmc-patch-still-needed" { inherit src; } ''
            file="$src/coolercontrold/daemon/src/repositories/hwmon/devices.rs"
            if grep -q '"macsmc_hwmon"' "$file"; then
              echo "Upstream now matches the kernel's macsmc_hwmon device name:"
              grep -n macsmc "$file" | head -5
              echo ""
              echo "The Apple Silicon fan fix may have landed. Verify that detection needs no"
              echo "fanN_manual, that 0% writes 0 to fanN_target, and that shutdown hands a"
              echo "macsmc_hwmon fan back to the firmware, then delete"
              echo "patches/macsmc-hwmon-fan-control.patch, its entry in coolercontrold.nix,"
              echo "and this check."
              exit 1
            fi
            touch "$out"
          '';
          checks.apple-silicon-cpu-patch-still-needed =
            pkgs.runCommand "apple-silicon-cpu-patch-still-needed" { inherit src; }
              ''
                dir="$src/coolercontrold/daemon/src/repositories/cpu"
                if grep -rq -e devicetree -e arm-platform "$dir"; then
                  echo "Upstream's CPU repository now reads the device tree:"
                  grep -rn -e devicetree -e arm-platform "$dir" | head -5
                  echo ""
                  echo "Apple Silicon may have its CPU device upstream. Verify that the daemon"
                  echo "starts on an Apple Silicon Mac with no CPU repository error and shows CPU"
                  echo "load and frequency, then delete patches/apple-silicon-cpu-device.patch,"
                  echo "its entry in coolercontrold.nix, and this check."
                  exit 1
                fi
                touch "$out"
              '';
          checks.module-eval-nixos = inputs.std.lib.nixosModuleCheck {
            inherit (inputs) nixpkgs;
            inherit system;
            overlays = [ self.overlays.default ];
            module = ./module.nix;
            config.programs.coolercontrol.enable = true;
          };
          # The HM module only shells out to curl at runtime — no overlay needed.
          checks.module-eval-hm = inputs.std.lib.homeModuleCheck {
            inherit (inputs) nixpkgs home-manager;
            inherit system;
            module = ./hm-module.nix;
            config.programs.coolercontrol.enable = true;
          };
        };
    };
}
