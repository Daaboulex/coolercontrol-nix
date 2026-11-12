# Compatibility

What CoolerControl reaches, what your machine may need, and what was measured.

## Platforms

The flake declares its packages for `x86_64-linux` and `aarch64-linux`.

## Hardware support

CoolerControl detects and controls devices through:

- hwmon: kernel hardware monitoring (CPU and GPU temperatures, fan speeds, PWM
  control)
- liquidctl: USB liquid coolers and fan controllers (Corsair, NZXT, EVGA and
  others)
- libdrm: AMD GPU temperature and fan control
- NVML: NVIDIA GPU monitoring, loaded through `addDriverRunpath`

## Kernel modules for motherboard fan control

Motherboard fan headers require the appropriate Super I/O kernel module.

Nuvoton, on most ASUS, MSI and Gigabyte boards:

```nix
{
  boot.kernelModules = [ "nct6775" ];
}
```

ITE, on some Gigabyte and ASRock boards:

```nix
{
  boot.kernelModules = [ "it87" ];
}
```

ASUS boards may also need:

```nix
{
  boot.kernelParams = [ "acpi_enforce_resources=lax" ];
}
```

## Desktop app on Qt WebEngine 6.140

The fix described in [DESIGN.md](DESIGN.md) was measured on a J316c MacBook Pro
(M1 Max) and a Ryzen 9 9950X3D, Qt 6.12.0 with Qt WebEngine 6.140.0-rc.

Unpatched, the app logs
`Not allowed to load local resource: qrc:///qtwebchannel/qwebchannel.js`, and
neither `Initialized closed to system tray.` nor `Initialized open window.` is
ever logged. Patched, the script loads and the matching line is logged about a
second after the UI.

The Qt change behind it is qtwebengine `8e460f8089b9`, "Make 'qrc' a local
scheme", QTBUG-148477. The full account is the header of
[`patches/qwebchannel-qrc-scheme.patch`](../patches/qwebchannel-qrc-scheme.patch).

## Migrating from an older version

If you previously ran CoolerControl without this flake, your config may be at
`/etc/coolercontrol/`. Copy it over:

```bash
sudo systemctl stop coolercontrold
sudo cp -a /etc/coolercontrol/* /var/lib/coolercontrol/
sudo systemctl start coolercontrold
```
