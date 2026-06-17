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
      url = "github:Daaboulex/nix-packaging-standard?ref=v2.7.0";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.git-hooks.follows = "git-hooks";
    };
  };

  outputs =
    inputs@{ flake-parts, self, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];

      imports = [ inputs.std.flakeModules.base ];

      # The overlay nests every output under `pkgs.coolercontrol.*` so it slots
      # into nixpkgs' own `programs.coolercontrol` module (which reads that path).
      flake.overlays.default = _final: prev: {
        coolercontrol = {
          inherit (self.packages.${prev.stdenv.hostPlatform.system})
            coolercontrold
            coolercontrol-gui
            coolercontrol-ui-data
            coolerctl
            ;
        };
      };
      flake.nixosModules.default = import ./module.nix;
      flake.homeManagerModules.default = import ./hm-module.nix;

      perSystem =
        {
          system,
          pkgs,
          self',
          ...
        }:
        let
          # Upstream version, source, and per-language dependency hashes.
          # scripts/update.sh bumps these in place on each new GitLab tag
          # (.github/update.json names them: hash, npmDepsHash, cargoHash).
          version = "4.3.1";
          src = pkgs.fetchFromGitLab {
            owner = "coolercontrol";
            repo = "coolercontrol";
            rev = version;
            hash = "sha256-nFlaiQtc4r3FBmdhErUAucG3SQ1GWQX9ClnZXGVWjbc=";
          };
          npmDepsHash = "sha256-zolbx5ROiFzNhPGcOnJjEiY3W2IXI24wLKPj3wRSLXU=";
          cargoHash = "sha256-DE1m/odw90epyR8U9H1pxyJXariIHLXwk+mVYi8cu5A=";
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
