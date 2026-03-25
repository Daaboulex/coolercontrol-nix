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
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.guiPackage ] ++ lib.optional cfg.cli.enable cfg.cli.package;

    systemd = {
      packages = [ cfg.package ];
      services.coolercontrold = {
        wantedBy = [ "multi-user.target" ];
        serviceConfig = {
          StateDirectory = "coolercontrol";
          Environment = [
            "CC_CONFIG_DIR=/var/lib/coolercontrol"
          ];

          # Filesystem protection
          ProtectSystem = "strict";
          ReadWritePaths = [ "/var/lib/coolercontrol" ];
          PrivateTmp = true;
          ProtectHome = true;

          # Privilege restrictions
          NoNewPrivileges = true;
          ProtectKernelTunables = false; # needs sysfs/hwmon access
          ProtectKernelModules = false; # needs kmod for hardware detection
          ProtectControlGroups = true;

          # Network (daemon listens on localhost)
          RestrictAddressFamilies = [
            "AF_UNIX"
            "AF_INET"
            "AF_INET6"
          ];

          # Device access (hwmon, USB coolers, GPU)
          DevicePolicy = "auto";
        };
      };
    };
  };
}
