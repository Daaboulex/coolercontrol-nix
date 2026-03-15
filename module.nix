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
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.guiPackage ];

    systemd = {
      packages = [ cfg.package ];
      services.coolercontrold = {
        wantedBy = [ "multi-user.target" ];
        preStart = ''
          mkdir -p /var/lib/coolercontrol/plugins
        '';
        serviceConfig = {
          StateDirectory = "coolercontrol";
          Environment = [
            "COOLERCONTROL_PLUGINS_PATH=/var/lib/coolercontrol/plugins"
          ];
        };
      };
    };
  };
}
