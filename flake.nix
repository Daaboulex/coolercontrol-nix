{
  description = "CoolerControl — monitor and control your cooling devices on NixOS";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    git-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      git-hooks,
    }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forEachSystem = nixpkgs.lib.genAttrs supportedSystems;
      pkgsFor = system: import nixpkgs { localSystem.system = system; };
    in
    {
      packages = forEachSystem (
        system:
        let
          pkgs = pkgsFor system;
          shared = {
            version = "4.0.1";
            src = pkgs.fetchFromGitLab {
              owner = "coolercontrol";
              repo = "coolercontrol";
              rev = "4.0.1";
              hash = "sha256-X8KEZARksSwmFEKnGnwZk9aQ0ND6fOsSelCIWPkEjN8=";
            };
          };
        in
        {
          coolercontrol-ui-data = pkgs.callPackage ./coolercontrol-ui-data.nix shared;
          coolercontrold = pkgs.callPackage ./coolercontrold.nix (
            shared // { inherit (self.packages.${system}) coolercontrol-ui-data; }
          );
          coolercontrol-gui = pkgs.callPackage ./coolercontrol-gui.nix shared;
          coolerctl = pkgs.callPackage ./coolerctl/package.nix { };
          default = self.packages.${system}.coolercontrold;
        }
      );

      overlays.default = _final: prev: {
        coolercontrol = {
          inherit (self.packages.${prev.stdenv.hostPlatform.system}) coolercontrold;
          inherit (self.packages.${prev.stdenv.hostPlatform.system}) coolercontrol-gui;
          inherit (self.packages.${prev.stdenv.hostPlatform.system}) coolercontrol-ui-data;
          inherit (self.packages.${prev.stdenv.hostPlatform.system}) coolerctl;
        };
      };

      nixosModules.default = import ./module.nix;

      homeManagerModules.default = import ./hm-module.nix;

      formatter = forEachSystem (system: (pkgsFor system).nixfmt-rfc-style);

      checks = forEachSystem (system: {
        pre-commit-check = git-hooks.lib.${system}.run {
          src = self;
          hooks = {
            nixfmt-rfc-style.enable = true;
          };
        };
      });

      devShells = forEachSystem (
        system:
        let
          pkgs = pkgsFor system;
        in
        {
          default = pkgs.mkShell {
            inherit (self.checks.${system}.pre-commit-check) shellHook;
            buildInputs = self.checks.${system}.pre-commit-check.enabledPackages;
            packages = [ pkgs.nil ];
          };
        }
      );
    };
}
