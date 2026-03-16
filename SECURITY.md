# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest on `main` | Yes |
| Older commits | No |

## Reporting a Vulnerability

If you discover a security vulnerability in this Nix packaging:

1. **Do NOT open a public issue.**
2. Email the maintainer or open a [private security advisory](https://github.com/Daaboulex/coolercontrol-nix/security/advisories/new) on GitHub.
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact

You should receive a response within 7 days.

## Security Measures

### Package Integrity
- All upstream sources are fetched with SRI hashes (`sha256-...`)
- `cargoHash` and `npmDepsHash` pin dependency trees
- Flake lock pins nixpkgs to a specific commit

### Systemd Hardening
The `coolercontrold` service runs with:
- `ProtectSystem=strict` — read-only filesystem except state directory
- `PrivateTmp=true` — isolated temp directory
- `ProtectHome=true` — no access to user home directories
- `NoNewPrivileges=true` — cannot escalate privileges
- `ProtectControlGroups=true` — read-only cgroups
- `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6` — no exotic sockets

Hardware access (hwmon, USB, kernel modules) is permitted as required by the daemon.

### Token Handling
- Bearer tokens stored at `~/.config/coolerctl/token` with `0600` permissions
- Home Manager module passes tokens via curl `--config` file, not CLI args
- Environment variable `COOLERCONTROL_TOKEN` supported as alternative

### CI/CD
- Auto-update workflow runs upstream Nix expressions in CI runners (inherent risk of auto-update systems)
- GitHub Actions use minimal permissions per workflow
- Auto-update PRs require CI verification before merge

### Known Limitations
- Daemon runs as root (required for hardware access)
- Self-signed TLS certificates used by default (curl uses `-k` to skip verification)
- No GPG signature verification of upstream releases
