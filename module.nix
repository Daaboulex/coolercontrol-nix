{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.programs.coolercontrol;
in
{
  # nixpkgs ships its own programs/coolercontrol.nix declaring the same option
  # path. This module is a drop-in replacement (bleeding-edge package + extra
  # options), so disable the nixpkgs one to avoid a duplicate-declaration clash.
  disabledModules = [ "programs/coolercontrol.nix" ];

  options.programs.coolercontrol = {
    enable = lib.mkEnableOption "CoolerControl cooling device management";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.coolercontrol.coolercontrold;
      defaultText = lib.literalExpression "pkgs.coolercontrol.coolercontrold";
      description = "The coolercontrold package to use.";
    };

    guiPackage = lib.mkOption {
      type = lib.types.package;
      default = pkgs.coolercontrol.coolercontrol-gui;
      defaultText = lib.literalExpression "pkgs.coolercontrol.coolercontrol-gui";
      description = "The CoolerControl GUI package to use.";
    };

    cli = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = "Whether to install the coolerctl CLI tool.";
      };

      package = lib.mkOption {
        type = lib.types.package;
        default = pkgs.coolercontrol.coolerctl;
        defaultText = lib.literalExpression "pkgs.coolercontrol.coolerctl";
        description = "The coolerctl CLI package to use.";
      };
    };

    configFile = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      description = "A config.toml copied into the daemon's configuration directory once, on a machine where the daemon has not written its own yet. The daemon owns the file from then on; a change here reaches only a machine that has none.";
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.guiPackage ] ++ lib.optional cfg.cli.enable cfg.cli.package;

    systemd = {
      packages = [ cfg.package ];
      tmpfiles.rules = lib.mkIf (cfg.configFile != null) [
        "d /var/lib/coolercontrol - - - -"
        "C /var/lib/coolercontrol/config.toml 0644 root root - ${cfg.configFile}"
      ];
      services.coolercontrold = {
        wantedBy = [ "multi-user.target" ];
        serviceConfig = {
          StateDirectory = "coolercontrol";
        };
      };
    };
  };
}
