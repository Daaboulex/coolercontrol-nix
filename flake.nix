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
      url = "github:Daaboulex/nix-packaging-standard/release";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.git-hooks.follows = "git-hooks";
    };
  };

  outputs =
    inputs@{ flake-parts, self, ... }:
    let
      # Upstream version, source, and per-language dependency hashes.
      # The standard's package-update workflow bumps these on each new GitLab tag
      # (.github/update.json names them: hash, npmDepsHash, cargoHash).
      version = "5.1.2";
      mkSrc =
        p:
        p.fetchFromGitLab {
          owner = "coolercontrol";
          repo = "coolercontrol";
          rev = version;
          hash = "sha256-Av0By/DxdBh0n0Og9fho3X8yizpSu2Joe39iM2GyxPg=";
        };
      npmDepsHash = "sha256-hVbvYrPcqvoOGB6QTNISGbFYErLCo2MIKy+AwJLpbcc=";
      cargoHash = "sha256-2RJ1ZDQJ+j0sUhGaqEisiA3H3wEiz9l4CEYxzO6ktLg=";
    in
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];

      imports = [
        inputs.std.flakeModules.base
        {
          perSystem.std.option-reference = {
            "NixOS module" = ./module.nix;
            "Home Manager module" = ./hm-module.nix;
          };
        }
      ];

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

          # The daemon reaches libdrm through libdrm_amdgpu_sys, which dlopens
          # libdrm_amdgpu.so.1, so nothing links it and buildInputs alone leaves
          # it unresolvable: AMD detection degrades and an RDNA3/4 card is never
          # identified, with only a warning in the log to say so.
          checks.gpu-stress-libraries-resolve =
            pkgs.runCommand "gpu-stress-libraries-resolve"
              {
                nativeBuildInputs = [ pkgs.patchelf ];
                daemon = self'.packages.coolercontrold;
              }
              ''
                bin="$daemon/bin/.coolercontrold-wrapped"
                [ -f "$bin" ] || bin="$daemon/bin/coolercontrold"
                rpath=$(patchelf --print-rpath "$bin")
                for lib in libvulkan.so.1 libEGL.so.1; do
                  found=""
                  for dir in ''${rpath//:/ }; do
                    [ -e "$dir/$lib" ] && found="$dir"
                  done
                  if [ -z "$found" ]; then
                    echo "::error::the GPU stress test dlopens $lib and nothing in the daemon's RUNPATH provides it, so it finds no GPU when run as a service"
                    exit 1
                  fi
                done
                touch "$out"
              '';
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

          checks.qwebchannel-patch-still-needed =
            pkgs.runCommand "qwebchannel-patch-still-needed" { inherit src; }
              ''
                store="$src/coolercontrol-ui/src/stores/DeviceStore.ts"
                stale=""
                if grep -rn QWebEngineUrlScheme "$src/coolercontrol"; then
                  echo "Upstream's desktop app now registers a URL scheme."
                  stale=1
                fi
                if ! grep -q 'qrc:///qtwebchannel/qwebchannel.js' "$store"; then
                  echo "DeviceStore.ts no longer loads qwebchannel.js from qrc."
                  stale=1
                fi
                if [ -n "$stale" ]; then
                  echo ""
                  echo "The Qt WebEngine 6.140 qrc fix may have landed. Verify that with Start in"
                  echo "tray on the app logs \"Initialized closed to system tray.\" and no \"Not"
                  echo "allowed to load local resource\", then delete"
                  echo "patches/qwebchannel-qrc-scheme.patch, its entry in coolercontrol-gui.nix,"
                  echo "and this check."
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
