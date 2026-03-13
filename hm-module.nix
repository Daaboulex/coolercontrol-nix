# Home Manager module for declarative CoolerControl configuration.
#
# Applies profiles, functions, modes, alerts, and settings to the
# coolercontrold daemon via its REST API on login. The daemon itself
# runs as a NixOS system service — this module configures the user-
# facing state that the web UI would normally manage.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.programs.coolercontrol;

  profileSubmodule = lib.types.submodule {
    options = {
      uid = lib.mkOption {
        type = lib.types.str;
        description = "Profile UID (from daemon).";
      };
      name = lib.mkOption {
        type = lib.types.str;
        description = "Profile display name.";
      };
      p_type = lib.mkOption {
        type = lib.types.str;
        default = "Graph";
        description = "Profile type: Graph, Fixed, or Default.";
      };
      speed_fixed = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Fixed speed percentage (0-100). Mutually exclusive with speed_profile.";
      };
      speed_profile = lib.mkOption {
        type = lib.types.listOf (
          lib.types.submodule {
            options = {
              temp = lib.mkOption {
                type = lib.types.number;
                description = "Temperature point in degrees Celsius.";
              };
              duty = lib.mkOption {
                type = lib.types.int;
                description = "Fan duty percentage (0-100) at this temperature.";
              };
            };
          }
        );
        default = [ ];
        description = "Temperature-to-duty curve as list of {temp, duty} pairs.";
      };
      extra = lib.mkOption {
        type = lib.types.attrs;
        default = { };
        description = "Additional profile fields passed to the API as-is.";
      };
    };
  };

  functionSubmodule = lib.types.submodule {
    options = {
      uid = lib.mkOption {
        type = lib.types.str;
        description = "Function UID (from daemon).";
      };
      name = lib.mkOption {
        type = lib.types.str;
        description = "Function display name.";
      };
      duty_minimum = lib.mkOption {
        type = lib.types.int;
        default = 2;
        description = "Minimum duty cycle percentage.";
      };
      duty_maximum = lib.mkOption {
        type = lib.types.int;
        default = 100;
        description = "Maximum duty cycle percentage.";
      };
      response_delay = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Response delay in seconds before applying changes.";
      };
      deviance = lib.mkOption {
        type = lib.types.nullOr lib.types.float;
        default = null;
        description = "Temperature deviance threshold for triggering changes.";
      };
      only_downward = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Only apply deviance check when temperature drops.";
      };
      sample_window = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Sample window size for temperature averaging.";
      };
      extra = lib.mkOption {
        type = lib.types.attrs;
        default = { };
        description = "Additional function fields passed to the API as-is.";
      };
    };
  };

  modeSubmodule = lib.types.submodule {
    options = {
      uid = lib.mkOption {
        type = lib.types.str;
        description = "Mode UID (from daemon).";
      };
      name = lib.mkOption {
        type = lib.types.str;
        description = "Mode display name.";
      };
      device_settings = lib.mkOption {
        type = lib.types.attrs;
        default = { };
        description = ''
          Device-to-channel settings mapping. Structure:
          { "<device_uid>" = { "<channel>" = { profile_uid = "..."; }; }; }
        '';
      };
      extra = lib.mkOption {
        type = lib.types.attrs;
        default = { };
        description = "Additional mode fields passed to the API as-is.";
      };
    };
  };

  alertSubmodule = lib.types.submodule {
    options = {
      channel = lib.mkOption {
        type = lib.types.str;
        description = "Device channel name to monitor.";
      };
      threshold_celsius = lib.mkOption {
        type = lib.types.number;
        description = "Temperature threshold in degrees Celsius.";
      };
      trigger = lib.mkOption {
        type = lib.types.str;
        default = "above";
        description = "Trigger direction: above or below.";
      };
      extra = lib.mkOption {
        type = lib.types.attrs;
        default = { };
        description = "Additional alert fields passed to the API as-is.";
      };
    };
  };

  settingsSubmodule = lib.types.submodule {
    options = {
      apply_on_boot = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Apply device settings on daemon startup.";
      };
      no_init = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Skip device initialization on daemon startup.";
      };
      startup_delay = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Delay in seconds before applying settings after daemon start.";
      };
      thinkpad_full_speed = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Enable ThinkPad full-speed fan mode.";
      };
      handle_dynamic_temps = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Handle dynamically appearing temperature sources.";
      };
      liquidctl_integration = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Enable liquidctl integration for AIO/pump devices.";
      };
      hide_duplicate_devices = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Hide duplicate device entries in the UI.";
      };
      compress = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Enable compression for API responses.";
      };
      poll_rate = lib.mkOption {
        type = lib.types.nullOr lib.types.float;
        default = null;
        description = "Sensor polling rate in seconds.";
      };
      drivetemp_suspend = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Suspend drivetemp monitoring during system sleep.";
      };
      allow_unencrypted = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Allow unencrypted HTTP connections (not recommended).";
      };
    };
  };

  # Build JSON payload for a profile
  mkProfileJson =
    _name: p:
    let
      base = {
        inherit (p) uid name p_type;
      }
      // p.extra;
      withFixed = if p.speed_fixed != null then base // { inherit (p) speed_fixed; } else base;
      withProfile =
        if p.speed_profile != [ ] then
          withFixed
          // {
            speed_profile = map (pt: {
              inherit (pt) temp duty;
            }) p.speed_profile;
          }
        else
          withFixed;
    in
    builtins.toJSON withProfile;

  # Build JSON payload for a function
  mkFunctionJson =
    _name: f:
    let
      base = {
        inherit (f)
          uid
          name
          duty_minimum
          duty_maximum
          ;
      }
      // f.extra;
      addOpt =
        acc: k: v:
        if v != null then acc // { "${k}" = v; } else acc;
      withOpts = lib.foldl' (acc: pair: addOpt acc pair.k pair.v) base [
        {
          k = "response_delay";
          v = f.response_delay;
        }
        {
          k = "deviance";
          v = f.deviance;
        }
        {
          k = "only_downward";
          v = f.only_downward;
        }
        {
          k = "sample_window";
          v = f.sample_window;
        }
      ];
    in
    builtins.toJSON withOpts;

  # Build JSON payload for a mode
  mkModeJson =
    _name: m:
    builtins.toJSON (
      {
        inherit (m) uid name;
        all_device_settings = m.device_settings;
      }
      // m.extra
    );

  # Build JSON payload for an alert
  mkAlertJson =
    a:
    builtins.toJSON (
      {
        inherit (a) channel threshold_celsius trigger;
      }
      // a.extra
    );

  # Build settings PATCH payload (only non-null fields)
  mkSettingsJson =
    s:
    let
      addOpt =
        acc: k: v:
        if v != null then acc // { "${k}" = v; } else acc;
    in
    builtins.toJSON (
      lib.foldl' (acc: pair: addOpt acc pair.k pair.v) { } [
        {
          k = "apply_on_boot";
          v = s.apply_on_boot;
        }
        {
          k = "no_init";
          v = s.no_init;
        }
        {
          k = "startup_delay";
          v = s.startup_delay;
        }
        {
          k = "thinkpad_full_speed";
          v = s.thinkpad_full_speed;
        }
        {
          k = "handle_dynamic_temps";
          v = s.handle_dynamic_temps;
        }
        {
          k = "liquidctl_integration";
          v = s.liquidctl_integration;
        }
        {
          k = "hide_duplicate_devices";
          v = s.hide_duplicate_devices;
        }
        {
          k = "compress";
          v = s.compress;
        }
        {
          k = "poll_rate";
          v = s.poll_rate;
        }
        {
          k = "drivetemp_suspend";
          v = s.drivetemp_suspend;
        }
        {
          k = "allow_unencrypted";
          v = s.allow_unencrypted;
        }
      ]
    );

  curlCmd = "${pkgs.curl}/bin/curl";

  # Build the activation script
  applyScript = pkgs.writeShellScript "coolercontrol-apply" ''
    set -euo pipefail

    URL="${cfg.url}"
    TOKEN=""

    # Load token if available
    TOKEN_FILE="$HOME/.config/coolerctl/token"
    if [[ -n "''${COOLERCONTROL_TOKEN:-}" ]]; then
      TOKEN="$COOLERCONTROL_TOKEN"
    elif [[ -f "$TOKEN_FILE" ]]; then
      TOKEN=$(cat "$TOKEN_FILE")
    fi

    auth_args() {
      if [[ -n "$TOKEN" ]]; then
        echo "-H"
        echo "Authorization: Bearer $TOKEN"
      fi
    }

    api() {
      local method="$1" path="$2"
      shift 2
      ${curlCmd} -skf -X "$method" \
        -H "Content-Type: application/json" \
        $(auth_args) \
        "$@" \
        "''${URL}''${path}"
    }

    # Wait for daemon (up to 30s)
    echo "Waiting for CoolerControl daemon at $URL..."
    for i in $(seq 1 30); do
      if ${curlCmd} -skf -o /dev/null "''${URL}/handshake" 2>/dev/null; then
        echo "Daemon reachable after ''${i}s."
        break
      fi
      if [[ "$i" -eq 30 ]]; then
        echo "ERROR: CoolerControl daemon not reachable after 30s." >&2
        exit 1
      fi
      sleep 1
    done

    ${lib.concatStringsSep "\n" (
      lib.mapAttrsToList (name: p: ''
        echo "Applying profile: ${p.name} (${p.uid})"
        api PUT "/profiles/${p.uid}" -d '${mkProfileJson name p}'
      '') cfg.profiles
    )}

    ${lib.concatStringsSep "\n" (
      lib.mapAttrsToList (name: f: ''
        echo "Applying function: ${f.name} (${f.uid})"
        api PUT "/functions/${f.uid}" -d '${mkFunctionJson name f}'
      '') cfg.functions
    )}

    ${lib.concatStringsSep "\n" (
      lib.mapAttrsToList (name: m: ''
        echo "Applying mode: ${m.name} (${m.uid})"
        api PUT "/modes/${m.uid}" -d '${mkModeJson name m}'
      '') cfg.modes
    )}

    ${lib.optionalString (cfg.activeMode != null) ''
      echo "Activating mode: ${cfg.activeMode}"
      api PUT "/modes-active" -d '"${cfg.activeMode}"'
    ''}

    ${lib.concatStringsSep "\n" (
      map (a: ''
        echo "Creating alert for channel: ${a.channel}"
        api POST "/alerts" -d '${mkAlertJson a}'
      '') cfg.alerts
    )}

    ${lib.optionalString (cfg.settings != null) (
      let
        json = mkSettingsJson cfg.settings;
      in
      lib.optionalString (json != "{}") ''
        echo "Patching global settings"
        api PATCH "/settings" -d '${json}'
      ''
    )}

    ${lib.concatStringsSep "\n" (
      map (cmd: ''
        echo "Running extra command: ${cmd}"
        ${cmd}
      '') cfg.extraCommands
    )}

    echo "CoolerControl configuration applied."
  '';
in
{
  options.programs.coolercontrol = {
    enable = lib.mkEnableOption "declarative CoolerControl daemon configuration";

    url = lib.mkOption {
      type = lib.types.str;
      default = "https://localhost:11987";
      description = "CoolerControl daemon URL.";
    };

    profiles = lib.mkOption {
      type = lib.types.lazyAttrsOf profileSubmodule;
      default = { };
      description = "Fan curve profiles to apply. Keys are arbitrary names, UIDs come from the daemon.";
    };

    functions = lib.mkOption {
      type = lib.types.lazyAttrsOf functionSubmodule;
      default = { };
      description = "Function definitions to apply. Keys are arbitrary names, UIDs come from the daemon.";
    };

    modes = lib.mkOption {
      type = lib.types.lazyAttrsOf modeSubmodule;
      default = { };
      description = "Mode definitions to apply. Keys are arbitrary names, UIDs come from the daemon.";
    };

    activeMode = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "Mode UID to activate on login.";
    };

    alerts = lib.mkOption {
      type = lib.types.listOf alertSubmodule;
      default = [ ];
      description = "Alert definitions to create.";
    };

    settings = lib.mkOption {
      type = lib.types.nullOr settingsSubmodule;
      default = null;
      description = "Global daemon settings to patch.";
    };

    extraCommands = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = "Additional shell commands to run after applying configuration.";
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.user.services.coolercontrol-apply = {
      Unit = {
        Description = "Apply declarative CoolerControl configuration";
        After = [ "graphical-session.target" ];
      };
      Service = {
        Type = "oneshot";
        ExecStart = applyScript;
        RemainAfterExit = true;
      };
      Install = {
        WantedBy = [ "graphical-session.target" ];
      };
    };
  };
}
