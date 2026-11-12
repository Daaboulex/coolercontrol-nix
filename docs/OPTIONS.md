# Options

Every option the modules of this flake declare. This file is generated from the module sources: change a description there, then run `nix run .#std-write-option-reference`.

## Home Manager module

Declared in [hm-module.nix](../hm-module.nix).

### `programs.coolercontrol.enable`

Whether to enable declarative CoolerControl daemon configuration.

Type: `boolean`. Default: `false`.

### `programs.coolercontrol.activeMode`

Mode UID to activate on login.

Type: `null or string`. Default: `null`.

### `programs.coolercontrol.alerts`

Alert definitions to create.

Type: `list of (submodule)`. Default: `[ ]`.

### `programs.coolercontrol.alerts.*.channel`

Device channel name to monitor.

Type: `string`.

### `programs.coolercontrol.alerts.*.extra`

Additional alert fields passed to the API as-is.

Type: `attribute set`. Default: `{ }`.

### `programs.coolercontrol.alerts.*.threshold_celsius`

Temperature threshold in degrees Celsius.

Type: `signed integer or floating point number`.

### `programs.coolercontrol.alerts.*.trigger`

Trigger direction: above or below.

Type: `string`. Default: `"above"`.

### `programs.coolercontrol.customSensors`

Custom sensor definitions to create. Keys are arbitrary names, IDs come from the daemon.

Type: `lazy attribute set of (submodule)`. Default: `{ }`.

### `programs.coolercontrol.customSensors.<name>.cs_type`

Custom sensor type (e.g., Mix, File).

Type: `string`. Default: `"Mix"`.

### `programs.coolercontrol.customSensors.<name>.extra`

Additional custom sensor fields passed to the API as-is.

Type: `attribute set`. Default: `{ }`.

### `programs.coolercontrol.customSensors.<name>.id`

Custom sensor ID.

Type: `string`.

### `programs.coolercontrol.customSensors.<name>.mix_function`

Mix function (e.g., Max, Average). Only used if cs_type is Mix.

Type: `null or string`. Default: `"Max"`.

### `programs.coolercontrol.customSensors.<name>.sources`

List of temperature sources for Mix sensors.

Type: `list of (submodule)`. Default: `[ ]`.

### `programs.coolercontrol.customSensors.<name>.sources.*.temp_source`

The temperature sensor this source reads.

Type: `submodule`.

### `programs.coolercontrol.customSensors.<name>.sources.*.temp_source.device_uid`

Device UID.

Type: `string`.

### `programs.coolercontrol.customSensors.<name>.sources.*.temp_source.temp_name`

Temperature source name.

Type: `string`.

### `programs.coolercontrol.customSensors.<name>.sources.*.weight`

Weight of this source.

Type: `signed integer or floating point number`. Default: `1`.

### `programs.coolercontrol.devices`

Per-device settings and channel mappings. Keys are arbitrary names, UIDs come from the daemon.

Type: `lazy attribute set of (submodule)`. Default: `{ }`.

### `programs.coolercontrol.devices.<name>.channels`

Per-channel settings for this device.

Type: `lazy attribute set of (submodule)`. Default: `{ }`.

### `programs.coolercontrol.devices.<name>.channels.<name>.lcd`

LCD configuration for this channel.

Type: `null or (attribute set)`. Default: `null`.

### `programs.coolercontrol.devices.<name>.channels.<name>.lighting`

Lighting configuration for this channel.

Type: `null or (attribute set)`. Default: `null`.

### `programs.coolercontrol.devices.<name>.channels.<name>.profile_uid`

Profile UID to assign to this channel.

Type: `null or string`. Default: `null`.

### `programs.coolercontrol.devices.<name>.channels.<name>.speed_fixed`

Fixed speed percentage for manual mode.

Type: `null or signed integer`. Default: `null`.

### `programs.coolercontrol.devices.<name>.is_legacy690`

Whether to enable AseTek 690 legacy mode.

Type: `null or boolean`. Default: `null`.

### `programs.coolercontrol.devices.<name>.thinkpad_fan_control`

Whether to enable ThinkPad fan control for this device.

Type: `null or boolean`. Default: `null`.

### `programs.coolercontrol.devices.<name>.uid`

Device UID.

Type: `string`.

### `programs.coolercontrol.extraCommands`

Additional shell commands to run after applying configuration.

Type: `list of string`. Default: `[ ]`.

### `programs.coolercontrol.functions`

Function definitions to apply. Keys are arbitrary names, UIDs come from the daemon.

Type: `lazy attribute set of (submodule)`. Default: `{ }`.

### `programs.coolercontrol.functions.<name>.deviance`

Temperature deviance threshold for triggering changes.

Type: `null or floating point number`. Default: `null`.

### `programs.coolercontrol.functions.<name>.duty_maximum`

Maximum duty cycle percentage.

Type: `signed integer`. Default: `100`.

### `programs.coolercontrol.functions.<name>.duty_minimum`

Minimum duty cycle percentage.

Type: `signed integer`. Default: `2`.

### `programs.coolercontrol.functions.<name>.extra`

Additional function fields passed to the API as-is.

Type: `attribute set`. Default: `{ }`.

### `programs.coolercontrol.functions.<name>.name`

Function display name.

Type: `string`.

### `programs.coolercontrol.functions.<name>.only_downward`

Only apply deviance check when temperature drops.

Type: `null or boolean`. Default: `null`.

### `programs.coolercontrol.functions.<name>.response_delay`

Response delay in seconds before applying changes.

Type: `null or signed integer`. Default: `null`.

### `programs.coolercontrol.functions.<name>.sample_window`

Sample window size for temperature averaging.

Type: `null or signed integer`. Default: `null`.

### `programs.coolercontrol.functions.<name>.uid`

Function UID (from daemon).

Type: `string`.

### `programs.coolercontrol.modes`

Mode definitions to apply. Keys are arbitrary names, UIDs come from the daemon.

Type: `lazy attribute set of (submodule)`. Default: `{ }`.

### `programs.coolercontrol.modes.<name>.device_settings`

Device-to-channel settings mapping. Structure:
{ "<device_uid>" = { "<channel>" = { profile_uid = "..."; }; }; }

Type: `attribute set`. Default: `{ }`.

### `programs.coolercontrol.modes.<name>.extra`

Additional mode fields passed to the API as-is.

Type: `attribute set`. Default: `{ }`.

### `programs.coolercontrol.modes.<name>.name`

Mode display name.

Type: `string`.

### `programs.coolercontrol.modes.<name>.uid`

Mode UID (from daemon).

Type: `string`.

### `programs.coolercontrol.plugins`

Plugin configurations. Keys are arbitrary names, IDs come from the daemon.

Type: `lazy attribute set of (submodule)`. Default: `{ }`.

### `programs.coolercontrol.plugins.<name>.config`

Raw plugin configuration (usually text/plain).

Type: `null or string`. Default: `null`.

### `programs.coolercontrol.plugins.<name>.enabled`

Whether the plugin is enabled.

Type: `boolean`. Default: `true`.

### `programs.coolercontrol.plugins.<name>.id`

Plugin ID.

Type: `string`.

### `programs.coolercontrol.profiles`

Fan curve profiles to apply. Keys are arbitrary names, UIDs come from the daemon.

Type: `lazy attribute set of (submodule)`. Default: `{ }`.

### `programs.coolercontrol.profiles.<name>.extra`

Additional profile fields passed to the API as-is.

Type: `attribute set`. Default: `{ }`.

### `programs.coolercontrol.profiles.<name>.name`

Profile display name.

Type: `string`.

### `programs.coolercontrol.profiles.<name>.p_type`

Profile type: Graph, Fixed, or Default.

Type: `string`. Default: `"Graph"`.

### `programs.coolercontrol.profiles.<name>.speed_fixed`

Fixed speed percentage (0-100). Mutually exclusive with speed_profile.

Type: `null or signed integer`. Default: `null`.

### `programs.coolercontrol.profiles.<name>.speed_profile`

Temperature-to-duty curve as list of {temp, duty} pairs.

Type: `list of (submodule)`. Default: `[ ]`.

### `programs.coolercontrol.profiles.<name>.speed_profile.*.duty`

Fan duty percentage (0-100) at this temperature.

Type: `signed integer`.

### `programs.coolercontrol.profiles.<name>.speed_profile.*.temp`

Temperature point in degrees Celsius.

Type: `signed integer or floating point number`.

### `programs.coolercontrol.profiles.<name>.uid`

Profile UID (from daemon).

Type: `string`.

### `programs.coolercontrol.settings`

Global daemon settings to patch.

Type: `null or (submodule)`. Default: `null`.

### `programs.coolercontrol.settings.allow_unencrypted`

Allow unencrypted HTTP connections (not recommended).

Type: `null or boolean`. Default: `null`.

### `programs.coolercontrol.settings.apply_on_boot`

Apply device settings on daemon startup.

Type: `null or boolean`. Default: `null`.

### `programs.coolercontrol.settings.compress`

Enable compression for API responses.

Type: `null or boolean`. Default: `null`.

### `programs.coolercontrol.settings.drivetemp_suspend`

Suspend drivetemp monitoring during system sleep.

Type: `null or boolean`. Default: `null`.

### `programs.coolercontrol.settings.handle_dynamic_temps`

Handle dynamically appearing temperature sources.

Type: `null or boolean`. Default: `null`.

### `programs.coolercontrol.settings.hide_duplicate_devices`

Hide duplicate device entries in the UI.

Type: `null or boolean`. Default: `null`.

### `programs.coolercontrol.settings.liquidctl_integration`

Enable liquidctl integration for AIO/pump devices.

Type: `null or boolean`. Default: `null`.

### `programs.coolercontrol.settings.no_init`

Skip device initialization on daemon startup.

Type: `null or boolean`. Default: `null`.

### `programs.coolercontrol.settings.poll_rate`

Sensor polling rate in seconds.

Type: `null or floating point number`. Default: `null`.

### `programs.coolercontrol.settings.startup_delay`

Delay in seconds before applying settings after daemon start.

Type: `null or signed integer`. Default: `null`.

### `programs.coolercontrol.settings.thinkpad_full_speed`

Enable ThinkPad full-speed fan mode.

Type: `null or boolean`. Default: `null`.

### `programs.coolercontrol.url`

CoolerControl daemon URL.

Type: `string`. Default: `"https://localhost:11987"`.

## NixOS module

Declared in [module.nix](../module.nix).

### `programs.coolercontrol.enable`

Whether to enable CoolerControl cooling device management.

Type: `boolean`. Default: `false`.

### `programs.coolercontrol.package`

The coolercontrold package to use.

Type: `package`. Default: `pkgs.coolercontrol.coolercontrold`.

### `programs.coolercontrol.cli.enable`

Whether to install the coolerctl CLI tool.

Type: `boolean`. Default: `true`.

### `programs.coolercontrol.cli.package`

The coolerctl CLI package to use.

Type: `package`. Default: `pkgs.coolercontrol.coolerctl`.

### `programs.coolercontrol.configFile`

A config.toml copied into the daemon's configuration directory once, on a machine where the daemon has not written its own yet. The daemon owns the file from then on; a change here reaches only a machine that has none.

Type: `null or absolute path`. Default: `null`.

### `programs.coolercontrol.guiPackage`

The CoolerControl GUI package to use.

Type: `package`. Default: `pkgs.coolercontrol.coolercontrol-gui`.
