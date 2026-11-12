# Home Manager module

Declaratively configure CoolerControl profiles, functions, modes, alerts and
settings. The daemon runs as a NixOS system service, and this module applies
state through its REST API at login.

## Setup

```nix
{
  home-manager.sharedModules = [ inputs.coolercontrol.homeModules.default ];
}
```

## How it works

1. You declare profiles, functions, modes and settings in Nix.
2. At login, a systemd user service (`coolercontrol-apply.service`) sends them
   to the daemon through the REST API. It is started with
   `graphical-session.target`.
3. The daemon persists the changes to `/var/lib/coolercontrol/`.

Prerequisites:

- The daemon must be running (`programs.coolercontrol.enable = true` in the
  NixOS configuration).
- A bearer token must exist at `~/.config/coolerctl/token`. Run
  `coolerctl auth login` to save one, and again after every password change.

The service reads the token on its own. It uses the `COOLERCONTROL_TOKEN`
environment variable instead when that is set. It waits up to 30 seconds for
the daemon at `programs.coolercontrol.url`, which defaults to
`https://localhost:11987`.

## Example configuration

This goes in `home.nix` or any Home Manager module.

```nix
{
  programs.coolercontrol = {
    enable = true;

    profiles = {
      default-profile = {
        uid = "0";
        name = "Default Profile";
        p_type = "Default";
        extra = {
          function_uid = "0";
        };
      };
      my-profile = {
        uid = "abc123";
        name = "Silent";
        p_type = "Graph";
        speed_profile = [
          { temp = 30; duty = 25; }
          { temp = 50; duty = 40; }
          { temp = 70; duty = 70; }
          { temp = 85; duty = 100; }
        ];
        extra = {
          function_uid = "def456";
        };
      };
    };

    functions = {
      default-function = {
        uid = "0";
        name = "Default Function";
        duty_minimum = 1;
        duty_maximum = 100;
      };
      my-function = {
        uid = "def456";
        name = "Smooth Response";
        duty_minimum = 2;
        duty_maximum = 100;
        response_delay = 3;
        deviance = 2.0;
        only_downward = false;
        sample_window = 6;
      };
    };

    modes = {
      default = {
        uid = "jkl012";
        name = "Default Mode";
        device_settings = {
          "<device-uid>" = {
            "fan1" = { profile_uid = "abc123"; };
          };
        };
      };
    };

    activeMode = "jkl012";

    settings = {
      apply_on_boot = true;
      no_init = false;
      startup_delay = 2;
      thinkpad_full_speed = false;
      handle_dynamic_temps = false;
      liquidctl_integration = true;
      hide_duplicate_devices = true;
      compress = true;
      poll_rate = 1.0;
      drivetemp_suspend = true;
      allow_unencrypted = false;
    };
  };
}
```

Notes on the example:

- The attribute names (`my-profile`, `my-function`, `default`) are arbitrary.
  The UIDs come from the daemon. `coolerctl profiles list` shows a profile's.
- `activeMode` is the UID of the mode to activate at login.
- `settings` holds the global daemon settings. Only the ones you set are sent.

The module also declares `devices`, `customSensors`, `plugins`, `alerts`,
`extraCommands` and `url`. Their fields are in
[`hm-module.nix`](../hm-module.nix).

## Exporting current config

Use `coolerctl export-config` to snapshot the daemon's current state as a Nix
attrset. Copy the output directly into your Home Manager configuration.

## API requirements

The daemon's API requires:

| Field | Requirement |
|---|---|
| `function_uid` | Required on profiles. Set it with `extra.function_uid`. The module sends `"0"` when unset |
| `duty_minimum` | Must be >= 1 |
| `member_profile_uids` | Required on Mix and Overlay profiles. The module sends `[]` when unset |
| `f_type` | Required on functions. The module sends `"Identity"` when unset |
| Bearer token | Required for write operations when a password is set |

## Debugging the apply service

Check its status:

```bash
systemctl --user status coolercontrol-apply
```

View the logs, which show the exact HTTP errors with status codes:

```bash
journalctl --user -u coolercontrol-apply -e
```

Apply again by hand after fixing the configuration:

```bash
systemctl --user restart coolercontrol-apply
```

Common errors:

- HTTP 401 "Invalid Credentials". Run `coolerctl auth login` to refresh the
  token.
- HTTP 400 "duty_minimum must be greater than 0". `duty_minimum` must be >= 1.
- HTTP 422 "missing field X". A required field was not provided. Check the
  example above.
- "CoolerControl daemon not reachable after 30s". The daemon is not running.
  Check `systemctl status coolercontrold`.
