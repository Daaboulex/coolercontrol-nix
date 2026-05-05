"""Export daemon state as Nix configuration."""

import json
import re

import click

from .api import api, api_raw, ApiError


def _to_nix(data, indent="", key_field=None):
    """Convert Python data to Nix-ish representation."""

    def _safe_key(k):
        return re.sub(r"[^a-zA-Z0-9_-]", "-", str(k)) if not re.match(r"^[0-9]", str(k)) else f"_{k}"

    if data is None:
        return "null"
    elif isinstance(data, bool):
        return "true" if data else "false"
    elif isinstance(data, (int, float)):
        return str(data)
    elif isinstance(data, str):
        return json.dumps(data)
    elif isinstance(data, list):
        if not data:
            return "[]"
        if key_field and all(isinstance(x, dict) and key_field in x for x in data):
            lines = ["{"]
            for x in data:
                key = _safe_key(x[key_field])
                val = _to_nix(x, indent + "  ")
                lines.append(f"{indent}  {key} = {val};")
            lines.append(f"{indent}}}")
            return "\n".join(lines)
        else:
            if len(data) <= 3 and all(isinstance(x, (int, float, str, bool)) or x is None for x in data):
                return "[" + ", ".join(_to_nix(x) for x in data) + "]"

            lines = ["[\n"]
            for x in data:
                lines.append(f"{indent}  {_to_nix(x, indent + '  ')}\n")
            lines.append(f"{indent}]")
            return "".join(lines)
    elif isinstance(data, dict):
        if not data:
            return "{}"

        if len(data) <= 2 and all(isinstance(v, (int, float, str, bool)) or v is None for v in data.values()):
            return "{ " + "; ".join(f"{k} = {_to_nix(v)}" for k, v in data.items()) + "; }"

        lines = ["{\n"]
        for k, v in data.items():
            lines.append(f"{indent}  {k} = {_to_nix(v, indent + '  ')};\n")
        lines.append(f"{indent}}}")
        return "".join(lines)
    return str(data)


@click.command("export-config")
@click.pass_context
def export_config(ctx):
    """Export current daemon state as a Nix attrset for Home Manager.

    Outputs a 1:1 declarative configuration block that can be pasted
    directly into your coolercontrol.nix file.
    """
    import datetime

    def _safe_name(name):
        safe = re.sub(r"[^a-zA-Z0-9_-]", "-", name)
        if re.match(r"^[0-9]", safe):
            return f"_{safe}"
        return safe

    base = ctx.obj["base"]
    now = datetime.datetime.now().isoformat()

    click.echo(f"# CoolerControl configuration export")
    click.echo(f"# Generated: {now}")
    click.echo(f"# Source: {base}")
    click.echo("#")
    click.echo("# This is a documentation snapshot of the daemon's current state.")
    click.echo("# Paste relevant sections into your Home Manager coolercontrol config.")
    click.echo("\n{")

    # ── Devices (Hardware Reference) ──
    click.echo("  # ── Devices (Hardware Reference) ──")
    resp = api("GET", "/devices", base)
    devices = resp.get("devices", []) if isinstance(resp, dict) else resp or []
    click.echo(f"  # devices_info = {_to_nix(devices, '  ')};\n")

    # ── Per-Device Settings ──
    click.echo("  # ── Per-Device Settings ──")
    click.echo("  devices = {")
    for dev in devices:
        uid = dev.get("uid")
        name = dev.get("name", uid)
        safe_name = _safe_name(name)

        settings = api("GET", f"/devices/{uid}/settings", base) or {}

        legacy690 = False
        try:
            lresp = api("GET", f"/devices/{uid}/asetek690", base)
            if isinstance(lresp, dict):
                legacy690 = lresp.get("is_legacy690", False)
        except ApiError as e:
            if "405" not in str(e):
                raise e

        click.echo(f"    {safe_name} = {{")
        click.echo(f"      uid = \"{uid}\";")
        if legacy690:
            click.echo("      is_legacy690 = true;")
        click.echo(f"      channels = {_to_nix(settings, '      ')};")
        click.echo("    };")
    click.echo("  };\n")

    # ── Profiles ──
    click.echo("  # ── Profiles (fan curves) ──")
    resp = api("GET", "/profiles", base)
    profiles = resp.get("profiles", []) if isinstance(resp, dict) else resp or []
    for p in profiles:
        if p.get("speed_profile"):
            p["speed_profile"] = [{"temp": pt[0], "duty": pt[1]} for pt in p["speed_profile"]]
    click.echo(f"  profiles = {_to_nix(profiles, '  ', key_field='name')};\n")

    # ── Functions ──
    click.echo("  # ── Functions ──")
    resp = api("GET", "/functions", base)
    functions = resp.get("functions", []) if isinstance(resp, dict) else resp or []
    click.echo(f"  functions = {_to_nix(functions, '  ', key_field='name')};\n")

    # ── Modes ──
    click.echo("  # ── Modes ──")
    resp = api("GET", "/modes", base)
    modes = resp.get("modes", []) if isinstance(resp, dict) else resp or []
    click.echo(f"  modes = {_to_nix(modes, '  ', key_field='name')};\n")

    # ── Active Mode ──
    click.echo("  # ── Active Mode ──")
    active = api("GET", "/modes-active", base)
    if isinstance(active, list) and active:
        active = active[0]
    elif isinstance(active, dict):
        active = active.get("current_mode_uid")
    click.echo(f"  activeMode = {_to_nix(active, '  ')};\n")

    # ── Custom Sensors ──
    click.echo("  # ── Custom Sensors ──")
    resp = api("GET", "/custom-sensors", base)
    custom = resp.get("custom_sensors", []) if isinstance(resp, dict) else resp or []
    click.echo(f"  customSensors = {_to_nix(custom, '  ', key_field='id')};\n")

    # ── Plugins ──
    click.echo("  # ── Plugins ──")
    click.echo("  plugins = {")
    plugins_resp = api("GET", "/plugins", base)
    plugins_list = plugins_resp if isinstance(plugins_resp, list) else [plugins_resp] if plugins_resp else []
    for p in plugins_list:
        pid = p.get("id")
        name = p.get("name", pid)
        safe_name = _safe_name(name)
        try:
            p_config = api_raw("GET", f"/plugins/{pid}/config", base) or ""
            click.echo(f"    {safe_name} = {{")
            click.echo(f"      id = \"{pid}\";")
            click.echo("      config = ''")
            click.echo(p_config)
            click.echo("      '';")
            click.echo("    };")
        except ApiError as e:
            if "401" in str(e):
                continue
            raise e
    click.echo("  };\n")

    # ── Alerts ──
    click.echo("  # ── Alerts ──")
    resp = api("GET", "/alerts", base)
    alerts_data = resp.get("alerts", []) if isinstance(resp, dict) else resp or []
    click.echo(f"  alerts = {_to_nix(alerts_data, '  ')};\n")

    # ── Global Settings ──
    click.echo("  # ── Global Settings ──")
    settings = api("GET", "/settings", base) or {}
    click.echo(f"  settings = {_to_nix(settings, '  ')};\n")

    click.echo("}")
