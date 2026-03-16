# Security Hardening Design

## Summary

Add systemd service hardening to the NixOS module and fix token exposure in the Home Manager module's curl calls.

## 1. Systemd Hardening (`module.nix`)

Add the following to `serviceConfig` for `coolercontrold.service`:

```nix
# Filesystem protection
ProtectSystem = "strict";
ReadWritePaths = [ "/var/lib/coolercontrol" ];
PrivateTmp = true;
ProtectHome = true;

# Privilege restrictions
NoNewPrivileges = true;
ProtectKernelTunables = false;  # needs sysfs/hwmon access
ProtectKernelModules = false;   # needs kmod for hardware detection
ProtectControlGroups = true;

# Network restrictions (daemon listens on localhost)
RestrictAddressFamilies = [ "AF_UNIX" "AF_INET" "AF_INET6" ];

# Device access (required for hwmon, USB coolers, GPU)
DevicePolicy = "auto";
```

**Not restricted** (daemon needs these for hardware access):
- `ProtectKernelTunables` — needs `/sys/class/hwmon`
- `ProtectKernelModules` — uses `kmod` to load sensor modules
- `DevicePolicy` — needs USB device access for liquidctl
- `CapabilityBoundingSet` — not restricted because daemon runs as root for hardware access

## 2. HM Module Token Fix (`hm-module.nix`)

**Current problem:** `auth_args()` function returns `-H "Authorization: Bearer $TOKEN"` which becomes visible in `/proc/*/cmdline` when curl is executed.

**Fix:** Write a curl config file to a temp file, use `--config` to read it:

```bash
# Write curl auth config to temp file (PrivateTmp protects it)
AUTH_FILE=$(mktemp)
trap 'rm -f "$AUTH_FILE"' EXIT
if [[ -n "$TOKEN" ]]; then
  echo '-H "Authorization: Bearer '"$TOKEN"'"' > "$AUTH_FILE"
  chmod 600 "$AUTH_FILE"
fi

api() {
  local method="$1" path="$2"
  shift 2
  curl -skf -X "$method" \
    -H "Content-Type: application/json" \
    --config "$AUTH_FILE" \
    "$@" \
    "${URL}${path}"
}
```

The token is never passed as a CLI argument — it's read from a file that only the user can access.

## Files

- Modify: `module.nix` (add serviceConfig hardening)
- Modify: `hm-module.nix` (replace `auth_args` with config file pattern)
