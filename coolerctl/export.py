"""Export daemon state as Nix configuration."""

import re

import click

from .api import api, api_raw, ApiError


_UNAVAILABLE = object()
_NIX_KEYWORDS = frozenset(
    ("assert", "else", "if", "in", "inherit", "let", "or", "rec", "then", "with")
)
_NIX_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_'-]*\Z")
_NIX_ESCAPES = {'"': '\\"', "\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def _nix_str(value):
    """Quote a value as a Nix string literal."""
    escaped = "".join(_NIX_ESCAPES.get(c, c) for c in str(value))
    return '"' + escaped.replace("${", "\\${") + '"'


def _nix_key(key):
    """Render a value as an attribute name, quoting whatever is not an identifier."""
    key = str(key)
    if _NIX_IDENT.match(key) and key not in _NIX_KEYWORDS:
        return key
    return _nix_str(key)


def _nix_indented(text, indent):
    """Render text as the body of a Nix '' indented string."""
    body = text.replace("''", "'''").replace("${", "''${")
    return "\n".join(f"{indent}{line}" for line in body.splitlines())


def _comment(text):
    """Collapse a value to one line so it cannot escape a '#' comment."""
    return " ".join(str(text).split())


def _unique_key(key, taken):
    """Suffix an attribute name already used in this set.

    Two identically named devices (a second `drivetemp`, a second GPU) would
    otherwise emit a duplicate attribute and the whole document would fail to
    evaluate. Every consumer of these keys reads the entry's own uid/id/name,
    so the key is a label and renaming it changes nothing that is applied.
    """
    candidate = str(key)
    n = 2
    while candidate in taken:
        candidate = f"{key}-{n}"
        n += 1
    taken.add(candidate)
    return candidate


def _to_nix(data, indent="", key_field=None):
    """Convert Python data to Nix representation."""
    if data is None:
        return "null"
    elif isinstance(data, bool):
        return "true" if data else "false"
    elif isinstance(data, (int, float)):
        return str(data)
    elif isinstance(data, str):
        return _nix_str(data)
    elif isinstance(data, list):
        if key_field and all(isinstance(x, dict) and key_field in x for x in data):
            if not data:
                return "{ }"
            taken = set()
            lines = ["{"]
            for x in data:
                key = _nix_key(_unique_key(x[key_field], taken))
                lines.append(f"{indent}  {key} = {_to_nix(x, indent + '  ')};")
            lines.append(f"{indent}}}")
            return "\n".join(lines)

        if not data:
            return "[ ]"
        if len(data) <= 3 and all(isinstance(x, (int, float, str, bool)) or x is None for x in data):
            return "[ " + " ".join(_to_nix(x) for x in data) + " ]"

        lines = ["[\n"]
        for x in data:
            lines.append(f"{indent}  {_to_nix(x, indent + '  ')}\n")
        lines.append(f"{indent}]")
        return "".join(lines)
    elif isinstance(data, dict):
        if not data:
            return "{ }"

        if len(data) <= 2 and all(
            isinstance(v, (int, float, str, bool)) or v is None for v in data.values()
        ):
            return "{ " + " ".join(f"{_nix_key(k)} = {_to_nix(v)};" for k, v in data.items()) + " }"

        lines = ["{\n"]
        for k, v in data.items():
            lines.append(f"{indent}  {_nix_key(k)} = {_to_nix(v, indent + '  ')};\n")
        lines.append(f"{indent}}}")
        return "".join(lines)
    return _nix_str(data)


@click.command("export-config")
@click.pass_context
def export_config(ctx):
    """Export current daemon state as a Nix attrset for Home Manager.

    Outputs a 1:1 declarative configuration block that can be pasted
    directly into your coolercontrol.nix file. A section the daemon
    refuses is emitted empty, marked in place, and reported on stderr
    with a non-zero exit — never left half-written.
    """
    import datetime

    base = ctx.obj["base"]
    now = datetime.datetime.now().isoformat()
    failures = []

    def get(path, note_indent="  "):
        try:
            return api("GET", path, base)
        except ApiError as e:
            failures.append(f"{path}: {_comment(e)}")
            click.echo(f"{note_indent}# {path} not exported: {_comment(e)}")
            return _UNAVAILABLE

    def get_list(path, key):
        resp = get(path)
        if resp is _UNAVAILABLE:
            return []
        if isinstance(resp, dict):
            return resp.get(key, [])
        return resp or []

    click.echo("# CoolerControl configuration export")
    click.echo(f"# Generated: {now}")
    click.echo(f"# Source: {base}")
    click.echo("#")
    click.echo("# This is a documentation snapshot of the daemon's current state.")
    click.echo("# Paste relevant sections into your Home Manager coolercontrol config.")
    click.echo("\n{")

    # ── Devices (Hardware Reference) ──
    click.echo("  # ── Devices (Hardware Reference) ──")
    devices = get_list("/devices", "devices")
    for line in f"devices_info = {_to_nix(devices, '  ')};".splitlines():
        click.echo(f"  # {line}")
    click.echo("")

    # ── Per-Device Settings ──
    click.echo("  # ── Per-Device Settings ──")
    click.echo("  devices = {")
    device_keys = set()
    for dev in devices:
        uid = dev.get("uid")
        name = _unique_key(dev.get("name", uid), device_keys)

        settings = get(f"/devices/{uid}/settings", "    ")
        if not isinstance(settings, dict):
            settings = {}

        legacy690 = False
        legacy_note = None
        try:
            lresp = api("GET", f"/devices/{uid}/asetek690", base)
            if isinstance(lresp, dict):
                legacy690 = lresp.get("is_legacy690", False)
        except ApiError as e:
            if "405" not in str(e):
                failures.append(f"/devices/{uid}/asetek690: {_comment(e)}")
                legacy_note = f"      # asetek690 probe failed: {_comment(e)}"

        click.echo(f"    {_nix_key(name)} = {{")
        if legacy_note:
            click.echo(legacy_note)
        click.echo(f"      uid = {_nix_str(uid)};")
        if legacy690:
            click.echo("      is_legacy690 = true;")
        click.echo(f"      channels = {_to_nix(settings, '      ')};")
        click.echo("    };")
    click.echo("  };\n")

    # ── Profiles ──
    click.echo("  # ── Profiles (fan curves) ──")
    profiles = [
        dict(p, speed_profile=[{"temp": pt[0], "duty": pt[1]} for pt in p["speed_profile"]])
        if p.get("speed_profile")
        else p
        for p in get_list("/profiles", "profiles")
    ]
    click.echo(f"  profiles = {_to_nix(profiles, '  ', key_field='name')};\n")

    # ── Functions ──
    click.echo("  # ── Functions ──")
    functions = get_list("/functions", "functions")
    click.echo(f"  functions = {_to_nix(functions, '  ', key_field='name')};\n")

    # ── Modes ──
    click.echo("  # ── Modes ──")
    modes = get_list("/modes", "modes")
    click.echo(f"  modes = {_to_nix(modes, '  ', key_field='name')};\n")

    # ── Active Mode ──
    click.echo("  # ── Active Mode ──")
    active = get("/modes-active")
    if active is _UNAVAILABLE:
        active = None
    elif isinstance(active, list) and active:
        active = active[0]
    elif isinstance(active, dict):
        active = active.get("current_mode_uid")
    click.echo(f"  activeMode = {_to_nix(active, '  ')};\n")

    # ── Custom Sensors ──
    click.echo("  # ── Custom Sensors ──")
    custom = get_list("/custom-sensors", "custom_sensors")
    click.echo(f"  customSensors = {_to_nix(custom, '  ', key_field='id')};\n")

    # ── Plugins ──
    click.echo("  # ── Plugins ──")
    plugins_resp = get("/plugins")
    if plugins_resp is _UNAVAILABLE or not plugins_resp:
        plugins_list = []
    elif isinstance(plugins_resp, list):
        plugins_list = plugins_resp
    else:
        plugins_list = [plugins_resp]
    click.echo("  plugins = {")
    plugin_keys = set()
    for p in plugins_list:
        pid = p.get("id")
        name = _unique_key(p.get("name", pid), plugin_keys)
        try:
            p_config = api_raw("GET", f"/plugins/{pid}/config", base) or ""
        except ApiError as e:
            failures.append(f"/plugins/{pid}/config: {_comment(e)}")
            click.echo(f"    # {_comment(name)} not exported: {_comment(e)}")
            continue
        click.echo(f"    {_nix_key(name)} = {{")
        click.echo(f"      id = {_nix_str(pid)};")
        click.echo("      config = ''")
        click.echo(_nix_indented(p_config, "        "))
        click.echo("      '';")
        click.echo("    };")
    click.echo("  };\n")

    # ── Alerts ──
    click.echo("  # ── Alerts ──")
    alerts_data = get_list("/alerts", "alerts")
    click.echo(f"  alerts = {_to_nix(alerts_data, '  ')};\n")

    # ── Global Settings ──
    click.echo("  # ── Global Settings ──")
    settings = get("/settings")
    if not isinstance(settings, dict):
        settings = {}
    click.echo(f"  settings = {_to_nix(settings, '  ')};\n")

    click.echo("}")

    if failures:
        for f in failures:
            click.echo(f"warning: {f}", err=True)
        ctx.exit(1)
