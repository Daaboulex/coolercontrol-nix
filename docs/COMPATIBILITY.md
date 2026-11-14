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

## Migrating from an older version

If you previously ran CoolerControl without this flake, your config may be at
`/etc/coolercontrol/`. Copy it over:

```bash
sudo systemctl stop coolercontrold
sudo cp -a /etc/coolercontrol/* /var/lib/coolercontrol/
sudo systemctl start coolercontrold
```
