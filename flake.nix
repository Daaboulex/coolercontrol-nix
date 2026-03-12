{
  description = "CoolerControl — monitor and control your cooling devices on NixOS";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forEachSystem = nixpkgs.lib.genAttrs supportedSystems;
      pkgsFor = system: import nixpkgs { inherit system; };
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
            shared // { coolercontrol-ui-data = self.packages.${system}.coolercontrol-ui-data; }
          );
          coolercontrol-gui = pkgs.callPackage ./coolercontrol-gui.nix shared;
          default = self.packages.${system}.coolercontrold;
        }
      );

      overlays.default = final: prev: {
        coolercontrol = {
          coolercontrold = self.packages.${prev.stdenv.hostPlatform.system}.coolercontrold;
          coolercontrol-gui = self.packages.${prev.stdenv.hostPlatform.system}.coolercontrol-gui;
          coolercontrol-ui-data = self.packages.${prev.stdenv.hostPlatform.system}.coolercontrol-ui-data;
        };
      };

      nixosModules.default = import ./module.nix;
    };
}
