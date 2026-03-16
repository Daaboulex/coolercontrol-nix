#!/usr/bin/env python3
"""coolerctl — CLI for CoolerControl daemon REST API.

Wraps the coolercontrold HTTP API for scripting, automation,
StreamController integration, and LLM-driven fan curve tuning.

Covers all 79 endpoints from the CoolerControl OpenAPI v4.0.0 spec.
"""

import json
import os
import sys
from typing import Optional

import click
import requests

DEFAULT_BASE = "https://localhost:11987"
TOKEN_PATH = os.path.expanduser("~/.config/coolerctl/token")
SESSION = requests.Session()
SESSION.verify = False  # CoolerControl uses self-signed certs by default

# Disable urllib3 warnings for unverified HTTPS
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Colors for terminal output ──

BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
RESET = "\033[0m"


def _use_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(color: str, text: str) -> str:
    if _use_color():
        return f"{color}{text}{RESET}"
    return str(text)


def _temp_color(temp: float) -> str:
    """Color-code a temperature value."""
    if temp > 80:
        return _c(RED, f"{temp:6.1f}")
    elif temp > 60:
        return _c(YELLOW, f"{temp:6.1f}")
    else:
        return _c(GREEN, f"{temp:6.1f}")


class ApiError(click.ClickException):
    """API call failed."""


def _load_token() -> str | None:
    """Load saved bearer token from disk."""
    if os.path.isfile(TOKEN_PATH):
        with open(TOKEN_PATH) as f:
            return f.read().strip()
    return os.environ.get("COOLERCONTROL_TOKEN")


def api(method: str, path: str, base: str = DEFAULT_BASE, **kwargs) -> dict | list | None:
    """Make an API call to coolercontrold."""
    url = f"{base}{path}"
    token = _load_token()
    if token:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
    try:
        resp = SESSION.request(method, url, timeout=kwargs.pop("timeout", 10), **kwargs)
    except requests.ConnectionError:
        raise ApiError(f"Cannot connect to coolercontrold at {base}. Is the daemon running?")
    if resp.status_code == 200:
        try:
            return resp.json()
        except ValueError:
            return None
    elif resp.status_code == 204:
        return None
    else:
        detail = ""
        try:
            detail = resp.json().get("error", resp.text)
        except (ValueError, AttributeError):
            detail = resp.text
        raise ApiError(f"API error {resp.status_code}: {detail}")


def api_upload(method: str, path: str, file_path: str, base: str = DEFAULT_BASE) -> dict | None:
    """Upload a file via multipart form to coolercontrold."""
    url = f"{base}{path}"
    token = _load_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if not os.path.isfile(file_path):
        raise ApiError(f"File not found: {file_path}")
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        try:
            resp = SESSION.request(method, url, files=files, headers=headers, timeout=30)
        except requests.ConnectionError:
            raise ApiError(f"Cannot connect to coolercontrold at {base}. Is the daemon running?")
    if resp.status_code in (200, 204):
        try:
            return resp.json()
        except ValueError:
            return None
    else:
        detail = ""
        try:
            detail = resp.json().get("error", resp.text)
        except (ValueError, AttributeError):
            detail = resp.text
        raise ApiError(f"API error {resp.status_code}: {detail}")


def api_raw(method: str, path: str, base: str = DEFAULT_BASE, **kwargs) -> str:
    """Make an API call returning raw text."""
    url = f"{base}{path}"
    token = _load_token()
    if token:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
    try:
        resp = SESSION.request(method, url, timeout=kwargs.pop("timeout", 10), **kwargs)
    except requests.ConnectionError:
        raise ApiError(f"Cannot connect to coolercontrold at {base}. Is the daemon running?")
    if resp.status_code in (200, 204):
        return resp.text
    else:
        raise ApiError(f"API error {resp.status_code}: {resp.text}")


def fmt_json(data, compact: bool = False):
    """Print JSON output."""
    if compact:
        click.echo(json.dumps(data, separators=(",", ":")))
    else:
        click.echo(json.dumps(data, indent=2))


# ── Root ──


@click.group()
@click.version_option(version="0.1.0", prog_name="coolerctl")
@click.option("--base-url", "-u", default=DEFAULT_BASE, envvar="COOLERCONTROL_URL",
              help="Daemon API base URL")
@click.option("--json", "-j", "json_output", is_flag=True, help="Force JSON output")
@click.pass_context
def cli(ctx, base_url: str, json_output: bool):
    """coolerctl — CoolerControl CLI.

    Control fans, pumps, lighting, LCD screens, profiles, and modes
    from the command line. Talks to the coolercontrold REST API.
    """
    ctx.ensure_object(dict)
    ctx.obj["base"] = base_url
    ctx.obj["json"] = json_output


# ══════════════════════════════════════════════════════════════════
#  Health / Handshake / Shutdown
# ══════════════════════════════════════════════════════════════════


@cli.command()
@click.pass_context
def handshake(ctx):
    """Verify daemon connection (no auth required)."""
    try:
        result = api("GET", "/handshake", ctx.obj["base"])
        if result and result.get("shake"):
            click.echo("OK — coolercontrold is running")
        else:
            click.echo("WARN — coolercontrold responded but handshake failed", err=True)
            sys.exit(1)
    except ApiError:
        click.echo("FAIL — coolercontrold is not reachable", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def health(ctx):
    """Show daemon health status (version, uptime, memory)."""
    data = api("GET", "/health", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    if not data:
        click.echo("No health data returned")
        return
    details = data.get("details", {})
    click.echo(f"Status:    {_c(GREEN, data.get('status', 'unknown'))}")
    click.echo(f"Version:   {details.get('version', 'unknown')}")
    click.echo(f"PID:       {details.get('pid', '?')}")
    uptime = details.get("uptime", "?")
    click.echo(f"Uptime:    {uptime}s")
    click.echo(f"Memory:    {details.get('memory_mb', '?')} MB")
    liq = details.get("liquidctl_connected")
    click.echo(f"Liquidctl: {'connected' if liq else 'not connected'}")
    errs = details.get("errors", [])
    warns = details.get("warnings", [])
    if errs:
        click.echo(f"Errors:    {_c(RED, str(len(errs)))}")
    if warns:
        click.echo(f"Warnings:  {_c(YELLOW, str(len(warns)))}")


@cli.command()
@click.pass_context
def shutdown(ctx):
    """Shutdown the CoolerControl daemon."""
    api("POST", "/shutdown", ctx.obj["base"])
    click.echo("Daemon shutdown requested")


@cli.command()
@click.pass_context
def acknowledge(ctx):
    """Acknowledge daemon log issues."""
    api("POST", "/acknowledge", ctx.obj["base"])
    click.echo("Log issues acknowledged")


# ══════════════════════════════════════════════════════════════════
#  Auth
# ══════════════════════════════════════════════════════════════════


@cli.group()
def auth():
    """Manage authentication."""


@auth.command("login")
@click.option("--password", "-p", prompt=True, hide_input=True, help="Admin password")
@click.pass_context
def auth_login(ctx, password: str):
    """Login and save a bearer token for future CLI use."""
    base = ctx.obj["base"]
    import base64
    auth_bytes = f"CCAdmin:{password}".encode("utf-8")
    auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")
    headers = {"Authorization": f"Basic {auth_b64}"}
    
    # Try POST /login with basic auth
    resp = SESSION.post(f"{base}/login", headers=headers, timeout=10)
    if resp.status_code != 200:
        # Fallback to JSON payload if basic auth fails
        resp = SESSION.post(f"{base}/login", json={"current_password": password}, timeout=10)
        
    if resp.status_code != 200:
        raise ApiError(f"Login failed (HTTP {resp.status_code}) — check your password")
    
    # Create a bearer token
    resp = SESSION.post(f"{base}/tokens", timeout=10,
                        json={"label": "coolerctl"})
    if resp.status_code != 200:
        raise ApiError(f"Failed to create token: {resp.text}")
    token_data = resp.json()
    token = token_data.get("token", "")
    if not token:
        raise ApiError("No token in response")
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(token)
    os.chmod(TOKEN_PATH, 0o600)
    click.echo(f"Logged in — token saved to {TOKEN_PATH}")


@auth.command("logout")
@click.pass_context
def auth_logout_api(ctx):
    """Logout from the daemon (invalidates session)."""
    api("POST", "/logout", ctx.obj["base"])
    if os.path.isfile(TOKEN_PATH):
        os.remove(TOKEN_PATH)
    click.echo("Logged out")


@auth.command("verify")
@click.pass_context
def auth_verify(ctx):
    """Verify current session authentication."""
    try:
        api("POST", "/verify-session", ctx.obj["base"])
        click.echo("Session is valid")
    except ApiError as e:
        click.echo(f"Session invalid: {e}", err=True)
        sys.exit(1)


@auth.command("set-password")
@click.option("--current-password", "-c", prompt="Current password", hide_input=True,
              help="Current admin password")
@click.option("--new-password", "-p", prompt="New password", hide_input=True,
              confirmation_prompt=True, help="New admin password")
@click.pass_context
def auth_set_password(ctx, current_password: str, new_password: str):
    """Set the daemon admin password."""
    api("POST", "/set-passwd", ctx.obj["base"],
        json={"current_password": current_password, "new_password": new_password})
    click.echo("Password set")


@auth.command("token")
@click.argument("token_value")
def auth_set_token(token_value: str):
    """Set a bearer token directly (from CoolerControl UI)."""
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(token_value)
    os.chmod(TOKEN_PATH, 0o600)
    click.echo(f"Token saved to {TOKEN_PATH}")


@auth.command("status")
def auth_status():
    """Check if a token is configured."""
    token = _load_token()
    if token:
        click.echo(f"Token configured ({len(token)} chars)")
    else:
        click.echo("No token configured")


@auth.command("clear")
def auth_clear():
    """Remove saved token."""
    if os.path.isfile(TOKEN_PATH):
        os.remove(TOKEN_PATH)
        click.echo("Token removed")
    else:
        click.echo("No token to remove")


# ══════════════════════════════════════════════════════════════════
#  Tokens
# ══════════════════════════════════════════════════════════════════


@cli.group()
def tokens():
    """Manage API access tokens."""


@tokens.command("list")
@click.pass_context
def tokens_list(ctx):
    """List all access tokens."""
    data = api("GET", "/tokens", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    if not data:
        click.echo("No tokens found")
        return
    for t in data if isinstance(data, list) else [data]:
        tid = t.get("id", t.get("token_id", "?"))
        label = t.get("label", t.get("name", "?"))
        created = t.get("created_at", "")
        expires = t.get("expires_at", "never")
        click.echo(f"  {tid:40s} {label:20s} created={created}  expires={expires}")


@tokens.command("create")
@click.option("--label", "-l", default="coolerctl", help="Token label/name")
@click.option("--expires", help="Expiration timestamp (ISO 8601)")
@click.pass_context
def tokens_create(ctx, label: str, expires: Optional[str]):
    """Create a new access token."""
    payload = {"label": label}
    if expires:
        payload["expires_at"] = expires
    data = api("POST", "/tokens", ctx.obj["base"], json=payload)
    if ctx.obj["json"]:
        fmt_json(data)
        return
    if data and data.get("token"):
        click.echo(f"Token created: {data['token']}")
        click.echo("Save this token — it will not be shown again.")
    else:
        fmt_json(data)


@tokens.command("delete")
@click.argument("token_id")
@click.pass_context
def tokens_delete(ctx, token_id: str):
    """Delete an access token."""
    api("DELETE", f"/tokens/{token_id}", ctx.obj["base"])
    click.echo(f"Deleted token: {token_id}")


# ══════════════════════════════════════════════════════════════════
#  Status
# ══════════════════════════════════════════════════════════════════


@cli.command()
@click.option("--device", "-d", "device_uid", help="Show status for a specific device")
@click.option("--channel", "-c", help="Show status for a specific channel (requires --device)")
@click.pass_context
def status(ctx, device_uid: Optional[str], channel: Optional[str]):
    """Show current status of all devices (temps, fans, loads).

    Use --device to filter by device, --device + --channel for a single channel.
    """
    base = ctx.obj["base"]
    if device_uid and channel:
        data = api("GET", f"/status/{device_uid}/channels/{channel}", base)
        if ctx.obj["json"]:
            fmt_json(data)
            return
        # Channel status history
        fmt_json(data)
        return
    elif device_uid:
        data = api("GET", f"/status/{device_uid}", base)
    else:
        data = api("POST", "/status", base)

    if ctx.obj["json"]:
        fmt_json(data)
        return

    devices = data if isinstance(data, list) else [data] if data else []
    for device in devices:
        uid = device.get("d_uid", device.get("uid", "?"))
        name = device.get("d_name", uid)
        d_type = device.get("d_type", "")
        click.echo(f"\n{'=' * 60}")
        click.echo(f"Device: {_c(BOLD, name)} ({d_type}) [{uid[:20]}]")
        click.echo(f"{'=' * 60}")
        # Handle both status_history (GET) and status (POST) response shapes
        status_entries = device.get("status", device.get("status_history", []))
        if isinstance(status_entries, list) and status_entries:
            # Use latest entry if it's a history
            entry = status_entries[-1] if isinstance(status_entries[-1], dict) else status_entries
            _print_status_entry(entry)
        elif isinstance(status_entries, dict):
            _print_status_entry(status_entries)


def _print_status_entry(entry):
    """Print a single status entry with temps and channels."""
    temps = entry.get("temps", [])
    channels = entry.get("channels", [])
    if temps:
        click.echo("  Temperatures:")
        for t in temps:
            temp_val = t.get("temp", 0)
            click.echo(f"    {t['name']:30s} {_temp_color(temp_val)}C")
    if channels:
        click.echo("  Channels:")
        for ch in channels:
            parts = []
            if ch.get("duty") is not None:
                parts.append(f"{ch['duty']:5.1f}%")
            if ch.get("rpm") is not None:
                parts.append(f"{ch['rpm']:5d} RPM")
            if ch.get("freq") is not None:
                parts.append(f"{ch['freq']} Hz")
            if ch.get("watts") is not None:
                parts.append(f"{ch['watts']:.1f}W")
            info = "  ".join(parts) if parts else "no data"
            click.echo(f"    {ch['name']:30s} {info}")


# ══════════════════════════════════════════════════════════════════
#  Devices
# ══════════════════════════════════════════════════════════════════


@cli.group()
def devices():
    """List and manage cooling devices."""


@devices.command("list")
@click.pass_context
def devices_list(ctx):
    """List all detected devices."""
    data = api("GET", "/devices", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    devs = data if isinstance(data, list) else data.get("devices", []) if data else []
    for dev in devs:
        uid = dev.get("uid", "?")
        name = dev.get("name", uid)
        d_type = dev.get("d_type", "")
        info_data = dev.get("info", {})
        model = info_data.get("model", dev.get("model", ""))
        click.echo(f"  {_c(BOLD, name)}")
        click.echo(f"    UID:    {uid}")
        click.echo(f"    Type:   {d_type}")
        if model:
            click.echo(f"    Model:  {model}")
        channels = info_data.get("channels", {})
        if channels:
            fan_ch = [k for k, v in channels.items() if v.get("speed_options")]
            temp_ch = [k for k, v in channels.items()
                       if not v.get("speed_options") and not v.get("lcd_info") and not v.get("lighting_modes")]
            lcd_ch = [k for k, v in channels.items() if v.get("lcd_info")]
            light_ch = [k for k, v in channels.items() if v.get("lighting_modes")]
            if fan_ch:
                click.echo(f"    Fan channels:      {len(fan_ch)} ({', '.join(fan_ch[:5])})")
            if temp_ch:
                click.echo(f"    Temp sensors:      {len(temp_ch)} ({', '.join(temp_ch[:5])})")
            if lcd_ch:
                click.echo(f"    LCD screens:       {len(lcd_ch)} ({', '.join(lcd_ch)})")
            if light_ch:
                click.echo(f"    Lighting channels: {len(light_ch)} ({', '.join(light_ch)})")
        click.echo()


@devices.command("settings")
@click.argument("device_uid")
@click.pass_context
def devices_settings(ctx, device_uid: str):
    """Show settings for a device."""
    data = api("GET", f"/devices/{device_uid}/settings", ctx.obj["base"])
    fmt_json(data)


@devices.command("set-manual")
@click.argument("device_uid")
@click.argument("channel")
@click.argument("duty", type=int)
@click.pass_context
def devices_set_manual(ctx, device_uid: str, channel: str, duty: int):
    """Set a channel to manual duty cycle (0-100%)."""
    if duty < 0 or duty > 100:
        raise click.BadParameter("Duty must be 0-100")
    api("PUT", f"/devices/{device_uid}/settings/{channel}/manual",
        ctx.obj["base"], json={"speed_fixed": duty})
    click.echo(f"Set {channel} -> {duty}% (manual)")


@devices.command("set-profile")
@click.argument("device_uid")
@click.argument("channel")
@click.argument("profile_uid")
@click.pass_context
def devices_set_profile(ctx, device_uid: str, channel: str, profile_uid: str):
    """Assign a profile to a device channel."""
    api("PUT", f"/devices/{device_uid}/settings/{channel}/profile",
        ctx.obj["base"], json={"profile_uid": profile_uid})
    click.echo(f"Set {channel} -> profile {profile_uid}")


@devices.command("reset-channel")
@click.argument("device_uid")
@click.argument("channel")
@click.pass_context
def devices_reset(ctx, device_uid: str, channel: str):
    """Reset a channel to default."""
    api("PUT", f"/devices/{device_uid}/settings/{channel}/reset", ctx.obj["base"])
    click.echo(f"Reset {channel}")


@devices.command("set-pwm")
@click.argument("device_uid")
@click.argument("channel")
@click.argument("pwm_mode", type=int)
@click.pass_context
def devices_set_pwm(ctx, device_uid: str, channel: str, pwm_mode: int):
    """Set PWM mode for a channel (DEPRECATED)."""
    api("PUT", f"/devices/{device_uid}/settings/{channel}/pwm",
        ctx.obj["base"], json={"pwm_mode": pwm_mode})
    click.echo(f"Set {channel} PWM mode -> {pwm_mode}")


@devices.command("set-lighting")
@click.argument("device_uid")
@click.argument("channel")
@click.option("--mode", "-m", required=True, help="Lighting mode name")
@click.option("--color", "-c", multiple=True, help="RGB color as R,G,B (can repeat)")
@click.option("--speed", "-s", help="Animation speed")
@click.pass_context
def devices_set_lighting(ctx, device_uid: str, channel: str, mode: str,
                          color: tuple, speed: Optional[str]):
    """Set channel lighting mode and colors."""
    colors = []
    for c in color:
        parts = [int(x.strip()) for x in c.split(",")]
        if len(parts) != 3:
            raise click.BadParameter(f"Color must be R,G,B: got {c}")
        colors.append(parts)
    payload = {"mode": mode, "colors": colors}
    if speed:
        payload["speed"] = speed
    api("PUT", f"/devices/{device_uid}/settings/{channel}/lighting",
        ctx.obj["base"], json=payload)
    click.echo(f"Set {channel} lighting -> {mode}")


@devices.command("set-lcd")
@click.argument("device_uid")
@click.argument("channel")
@click.option("--mode", "-m", required=True, help="LCD mode (none, static, carousel, liquid-temp)")
@click.option("--brightness", "-b", type=int, help="LCD brightness 0-100")
@click.pass_context
def devices_set_lcd(ctx, device_uid: str, channel: str, mode: str,
                     brightness: Optional[int]):
    """Set channel LCD mode."""
    payload = {"mode": mode, "colors": []}
    if brightness is not None:
        payload["brightness"] = brightness
    api("PUT", f"/devices/{device_uid}/settings/{channel}/lcd",
        ctx.obj["base"], json=payload)
    click.echo(f"Set {channel} LCD -> {mode}")


@devices.command("asetek690")
@click.argument("device_uid")
@click.option("--legacy/--no-legacy", default=False, help="Set legacy AseTek 690 mode")
@click.pass_context
def devices_asetek690(ctx, device_uid: str, legacy: bool):
    """Set AseTek 690 legacy mode for a device."""
    api("PATCH", f"/devices/{device_uid}/asetek690",
        ctx.obj["base"], json={"is_legacy690": legacy})
    click.echo(f"AseTek 690 legacy mode {'enabled' if legacy else 'disabled'} for {device_uid}")


# ══════════════════════════════════════════════════════════════════
#  LCD Image Management
# ══════════════════════════════════════════════════════════════════


@cli.group()
def lcd():
    """Manage LCD screen images."""


@lcd.command("list-images")
@click.argument("device_uid")
@click.argument("channel")
@click.pass_context
def lcd_list_images(ctx, device_uid: str, channel: str):
    """List LCD images for a device channel."""
    data = api("GET", f"/devices/{device_uid}/settings/{channel}/lcd/images", ctx.obj["base"])
    fmt_json(data)


@lcd.command("upload-image")
@click.argument("device_uid")
@click.argument("channel")
@click.argument("image_path", type=click.Path(exists=True))
@click.pass_context
def lcd_upload_image(ctx, device_uid: str, channel: str, image_path: str):
    """Upload an image to an LCD screen (processes for optimal display)."""
    result = api_upload("POST", f"/devices/{device_uid}/settings/{channel}/lcd/images",
                        image_path, ctx.obj["base"])
    click.echo(f"Uploaded image to {channel} on {device_uid}")
    if result:
        fmt_json(result)


@lcd.command("update-settings")
@click.argument("device_uid")
@click.argument("channel")
@click.option("--mode", "-m", help="LCD mode")
@click.option("--brightness", "-b", type=int, help="Brightness 0-100")
@click.option("--orientation", type=int, help="Screen orientation in degrees")
@click.pass_context
def lcd_update_settings(ctx, device_uid: str, channel: str, mode: Optional[str],
                         brightness: Optional[int], orientation: Optional[int]):
    """Update LCD image display settings."""
    payload = {}
    if mode:
        payload["mode"] = mode
    if brightness is not None:
        payload["brightness"] = brightness
    if orientation is not None:
        payload["orientation"] = orientation
    if not payload:
        raise click.UsageError("No settings to update (use --mode, --brightness, or --orientation)")
    api("PUT", f"/devices/{device_uid}/settings/{channel}/lcd/images",
        ctx.obj["base"], json=payload)
    click.echo(f"Updated LCD settings for {channel} on {device_uid}")


@lcd.command("set-shutdown-image")
@click.argument("device_uid")
@click.argument("channel")
@click.argument("image_path", type=click.Path(exists=True))
@click.pass_context
def lcd_set_shutdown_image(ctx, device_uid: str, channel: str, image_path: str):
    """Set the image displayed when the daemon shuts down."""
    result = api_upload("PUT", f"/devices/{device_uid}/settings/{channel}/lcd/shutdown-image",
                        image_path, ctx.obj["base"])
    click.echo(f"Set shutdown image for {channel} on {device_uid}")
    if result:
        fmt_json(result)


@lcd.command("clear-shutdown-image")
@click.argument("device_uid")
@click.argument("channel")
@click.pass_context
def lcd_clear_shutdown_image(ctx, device_uid: str, channel: str):
    """Clear the LCD shutdown image."""
    api("DELETE", f"/devices/{device_uid}/settings/{channel}/lcd/shutdown-image", ctx.obj["base"])
    click.echo(f"Cleared shutdown image for {channel} on {device_uid}")


# ══════════════════════════════════════════════════════════════════
#  Profiles
# ══════════════════════════════════════════════════════════════════


@cli.group()
def profiles():
    """Manage fan curve profiles."""


@profiles.command("list")
@click.pass_context
def profiles_list(ctx):
    """List all profiles."""
    data = api("GET", "/profiles", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    items = data if isinstance(data, list) else data.get("profiles", []) if data else []
    for p in items:
        uid = p.get("uid", "?")
        name = p.get("name", uid)
        p_type = p.get("p_type", "")
        fixed = p.get("speed_fixed")
        curve = p.get("speed_profile")
        type_str = p_type
        if p_type == "Fixed" and fixed is not None:
            type_str = f"Fixed {fixed}%"
        elif p_type == "Graph" and curve:
            points = ", ".join([f"{t}C->{d}%" for t, d in curve])
            type_str = f"Graph [{points}]"
        elif p_type == "Mix":
            members = p.get("member_profile_uids", [])
            type_str = f"Mix ({len(members)} members)"
        click.echo(f"  {_c(BOLD, name)}")
        click.echo(f"    UID:  {uid}")
        click.echo(f"    Type: {type_str}")
        ts = p.get("temp_source")
        if ts:
            click.echo(f"    Temp: {ts.get('temp_name', '?')} @ {ts.get('device_uid', '?')[:16]}")
        func = p.get("function_uid", "")
        if func:
            click.echo(f"    Func: {func}")
        click.echo()


@profiles.command("create")
@click.argument("name")
@click.option("--type", "-t", "p_type", default="Graph",
              help="Profile type: Graph, Fixed, Mix, Default")
@click.option("--speed-fixed", type=int, help="Fixed speed percentage")
@click.option("--speed-profile", "speed_profile_str",
              help="Fan curve as temp:duty pairs (e.g. '30:25,50:40,70:70,85:100')")
@click.option("--temp-source", help="Temperature source as device_uid:channel")
@click.option("--function", "function_uid", help="Function UID for this profile")
@click.pass_context
def profiles_create(ctx, name: str, p_type: str, speed_fixed: Optional[int],
                     speed_profile_str: Optional[str], temp_source: Optional[str],
                     function_uid: Optional[str]):
    """Create a new profile."""
    payload = {"name": name, "p_type": p_type}
    if speed_fixed is not None:
        payload["speed_fixed"] = speed_fixed
    if speed_profile_str:
        try:
            points = []
            for pair in speed_profile_str.split(","):
                t, d = pair.strip().split(":")
                temp_val = float(t)
                duty_val = int(d)
                if duty_val < 0 or duty_val > 100:
                    raise ValueError(f"duty must be 0-100, got {duty_val}")
                points.append([temp_val, duty_val])
            payload["speed_profile"] = points
        except ValueError as e:
            raise click.BadParameter(
                f"Invalid speed-profile format: {e}. Use 'temp:duty,temp:duty,...'")
    if temp_source:
        parts = temp_source.split(":")
        payload["temp_source"] = {"device_uid": parts[0], "temp_name": parts[1]}
    if function_uid:
        payload["function_uid"] = function_uid
    api("POST", "/profiles", ctx.obj["base"], json=payload)
    click.echo(f"Created profile: {name}")


@profiles.command("update")
@click.argument("profile_uid")
@click.option("--name", help="New name")
@click.option("--speed-fixed", type=int, help="New fixed speed")
@click.option("--from-json", "json_file", type=click.Path(exists=True),
              help="Update from a JSON file (overrides other options)")
@click.pass_context
def profiles_update(ctx, profile_uid: str, name: Optional[str],
                     speed_fixed: Optional[int], json_file: Optional[str]):
    """Update an existing profile."""
    if json_file:
        with open(json_file) as f:
            payload = json.load(f)
        api("PUT", "/profiles", ctx.obj["base"], json=payload)
        click.echo(f"Updated profile from {json_file}")
        return
    all_profiles = api("GET", "/profiles", ctx.obj["base"])
    items = all_profiles if isinstance(all_profiles, list) else all_profiles.get("profiles", [])
    current = next((p for p in items if p.get("uid") == profile_uid), None)
    if not current:
        raise ApiError(f"Profile {profile_uid} not found")
    if name:
        current["name"] = name
    if speed_fixed is not None:
        current["speed_fixed"] = speed_fixed
    api("PUT", "/profiles", ctx.obj["base"], json=current)
    click.echo(f"Updated profile: {profile_uid}")


@profiles.command("delete")
@click.argument("profile_uid")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def profiles_delete(ctx, profile_uid: str, yes: bool):
    """Delete a profile."""
    if not yes:
        click.confirm(f"Delete profile {profile_uid}?", abort=True)
    api("DELETE", f"/profiles/{profile_uid}", ctx.obj["base"])
    click.echo(f"Deleted profile: {profile_uid}")


@profiles.command("order")
@click.argument("uids", nargs=-1, required=True)
@click.pass_context
def profiles_order(ctx, uids: tuple):
    """Set profile display order. Pass UIDs in desired order."""
    # Fetch all profiles, reorder, and POST
    all_profiles = api("GET", "/profiles", ctx.obj["base"])
    items = all_profiles if isinstance(all_profiles, list) else all_profiles.get("profiles", [])
    ordered = []
    for uid in uids:
        found = next((p for p in items if p.get("uid") == uid), None)
        if not found:
            raise ApiError(f"Profile {uid} not found")
        ordered.append(found)
    # Add any not explicitly listed
    listed_uids = set(uids)
    for p in items:
        if p.get("uid") not in listed_uids:
            ordered.append(p)
    api("POST", "/profiles/order", ctx.obj["base"], json={"profiles": ordered})
    click.echo(f"Profile order updated ({len(uids)} positioned)")


# ══════════════════════════════════════════════════════════════════
#  Functions
# ══════════════════════════════════════════════════════════════════


@cli.group()
def functions():
    """Manage fan curve functions (response curves)."""


@functions.command("list")
@click.pass_context
def functions_list(ctx):
    """List all functions."""
    data = api("GET", "/functions", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    items = data if isinstance(data, list) else data.get("functions", []) if data else []
    for f in items:
        uid = f.get("uid", "?")
        name = f.get("name", uid)
        f_type = f.get("f_type", "")
        duty_min = f.get("duty_minimum", "?")
        duty_max = f.get("duty_maximum", "?")
        click.echo(f"  {_c(BOLD, name)} ({f_type})")
        click.echo(f"    UID:       {uid}")
        click.echo(f"    Step size: {duty_min}-{duty_max}%")
        resp_delay = f.get("response_delay")
        if resp_delay is not None:
            click.echo(f"    Response:  {resp_delay}s delay")
        click.echo()


@functions.command("create")
@click.argument("name")
@click.option("--type", "-t", "f_type", default="Identity",
              help="Function type: Identity, Standard, ExponentialMovingAvg")
@click.option("--duty-min", type=int, default=2, help="Minimum duty step size")
@click.option("--duty-max", type=int, default=5, help="Maximum duty step size")
@click.option("--response-delay", type=int, help="Response delay in seconds")
@click.option("--deviance", type=float, help="Temperature deviance threshold")
@click.pass_context
def functions_create(ctx, name: str, f_type: str, duty_min: int, duty_max: int,
                      response_delay: Optional[int], deviance: Optional[float]):
    """Create a new function."""
    payload = {
        "name": name,
        "f_type": f_type,
        "duty_minimum": duty_min,
        "duty_maximum": duty_max,
        "step_size_min_decreasing": 0,
        "step_size_max_decreasing": 0,
        "threshold_hopping": False,
    }
    if response_delay is not None:
        payload["response_delay"] = response_delay
    if deviance is not None:
        payload["deviance"] = deviance
    api("POST", "/functions", ctx.obj["base"], json=payload)
    click.echo(f"Created function: {name}")


@functions.command("update")
@click.argument("function_uid")
@click.option("--name", help="New name")
@click.option("--duty-min", type=int, help="New minimum duty step size")
@click.option("--duty-max", type=int, help="New maximum duty step size")
@click.option("--from-json", "json_file", type=click.Path(exists=True),
              help="Update from a JSON file")
@click.pass_context
def functions_update(ctx, function_uid: str, name: Optional[str],
                      duty_min: Optional[int], duty_max: Optional[int],
                      json_file: Optional[str]):
    """Update an existing function."""
    if json_file:
        with open(json_file) as f:
            payload = json.load(f)
        api("PUT", "/functions", ctx.obj["base"], json=payload)
        click.echo(f"Updated function from {json_file}")
        return
    all_funcs = api("GET", "/functions", ctx.obj["base"])
    items = all_funcs if isinstance(all_funcs, list) else all_funcs.get("functions", [])
    current = next((fn for fn in items if fn.get("uid") == function_uid), None)
    if not current:
        raise ApiError(f"Function {function_uid} not found")
    if name:
        current["name"] = name
    if duty_min is not None:
        current["duty_minimum"] = duty_min
    if duty_max is not None:
        current["duty_maximum"] = duty_max
    api("PUT", "/functions", ctx.obj["base"], json=current)
    click.echo(f"Updated function: {function_uid}")


@functions.command("delete")
@click.argument("function_uid")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def functions_delete(ctx, function_uid: str, yes: bool):
    """Delete a function."""
    if not yes:
        click.confirm(f"Delete function {function_uid}?", abort=True)
    api("DELETE", f"/functions/{function_uid}", ctx.obj["base"])
    click.echo(f"Deleted function: {function_uid}")


@functions.command("order")
@click.argument("uids", nargs=-1, required=True)
@click.pass_context
def functions_order(ctx, uids: tuple):
    """Set function display order. Pass UIDs in desired order."""
    all_funcs = api("GET", "/functions", ctx.obj["base"])
    items = all_funcs if isinstance(all_funcs, list) else all_funcs.get("functions", [])
    ordered = []
    for uid in uids:
        found = next((fn for fn in items if fn.get("uid") == uid), None)
        if not found:
            raise ApiError(f"Function {uid} not found")
        ordered.append(found)
    listed_uids = set(uids)
    for fn in items:
        if fn.get("uid") not in listed_uids:
            ordered.append(fn)
    api("POST", "/functions/order", ctx.obj["base"], json={"functions": ordered})
    click.echo(f"Function order updated ({len(uids)} positioned)")


# ══════════════════════════════════════════════════════════════════
#  Modes
# ══════════════════════════════════════════════════════════════════


@cli.group()
def modes():
    """Manage modes (combinations of profiles applied together)."""


@modes.command("list")
@click.pass_context
def modes_list(ctx):
    """List all modes."""
    data = api("GET", "/modes", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    items = data if isinstance(data, list) else data.get("modes", []) if data else []
    for m in items:
        uid = m.get("uid", "?")
        name = m.get("name", uid)
        settings = m.get("device_settings", [])
        click.echo(f"  {_c(BOLD, name)}")
        click.echo(f"    UID:      {uid}")
        n_settings = len(settings) if isinstance(settings, (list, dict)) else 0
        click.echo(f"    Devices:  {n_settings}")
        click.echo()


@modes.command("show")
@click.argument("mode_uid")
@click.pass_context
def modes_show(ctx, mode_uid: str):
    """Show details of a specific mode."""
    data = api("GET", f"/modes/{mode_uid}", ctx.obj["base"])
    fmt_json(data)


@modes.command("active")
@click.pass_context
def modes_active(ctx):
    """Show currently active modes."""
    data = api("GET", "/modes-active", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    if not data:
        click.echo("No active modes")
        return
    active = data if isinstance(data, list) else [data]
    for uid in active:
        click.echo(f"  Active: {uid}")


@modes.command("activate")
@click.argument("mode_uid")
@click.pass_context
def modes_activate(ctx, mode_uid: str):
    """Activate a mode."""
    api("POST", f"/modes-active/{mode_uid}", ctx.obj["base"])
    click.echo(f"Activated mode: {mode_uid}")


@modes.command("create")
@click.argument("name")
@click.pass_context
def modes_create(ctx, name: str):
    """Create a new mode."""
    api("POST", "/modes", ctx.obj["base"], json={"name": name, "device_settings": {}})
    click.echo(f"Created mode: {name}")


@modes.command("update")
@click.argument("mode_uid")
@click.option("--name", help="New name")
@click.option("--from-json", "json_file", type=click.Path(exists=True),
              help="Update from a JSON file")
@click.pass_context
def modes_update(ctx, mode_uid: str, name: Optional[str], json_file: Optional[str]):
    """Update an existing mode."""
    if json_file:
        with open(json_file) as f:
            payload = json.load(f)
        api("PUT", "/modes", ctx.obj["base"], json=payload)
        click.echo(f"Updated mode from {json_file}")
        return
    all_modes = api("GET", "/modes", ctx.obj["base"])
    items = all_modes if isinstance(all_modes, list) else all_modes.get("modes", [])
    current = next((m for m in items if m.get("uid") == mode_uid), None)
    if not current:
        raise ApiError(f"Mode {mode_uid} not found")
    if name:
        current["name"] = name
    api("PUT", "/modes", ctx.obj["base"], json=current)
    click.echo(f"Updated mode: {mode_uid}")


@modes.command("delete")
@click.argument("mode_uid")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def modes_delete(ctx, mode_uid: str, yes: bool):
    """Delete a mode."""
    if not yes:
        click.confirm(f"Delete mode {mode_uid}?", abort=True)
    api("DELETE", f"/modes/{mode_uid}", ctx.obj["base"])
    click.echo(f"Deleted mode: {mode_uid}")


@modes.command("duplicate")
@click.argument("mode_uid")
@click.pass_context
def modes_duplicate(ctx, mode_uid: str):
    """Duplicate a mode."""
    api("POST", f"/modes/{mode_uid}/duplicate", ctx.obj["base"])
    click.echo(f"Duplicated mode: {mode_uid}")


@modes.command("set-settings")
@click.argument("mode_uid")
@click.argument("json_file", type=click.Path(exists=True))
@click.pass_context
def modes_set_settings(ctx, mode_uid: str, json_file: str):
    """Update device settings for a mode from a JSON file."""
    with open(json_file) as f:
        payload = json.load(f)
    api("PUT", f"/modes/{mode_uid}/settings", ctx.obj["base"], json=payload)
    click.echo(f"Updated device settings for mode: {mode_uid}")


@modes.command("order")
@click.argument("uids", nargs=-1, required=True)
@click.pass_context
def modes_order(ctx, uids: tuple):
    """Set mode display order. Pass UIDs in desired order."""
    all_modes = api("GET", "/modes", ctx.obj["base"])
    items = all_modes if isinstance(all_modes, list) else all_modes.get("modes", [])
    ordered = []
    for uid in uids:
        found = next((m for m in items if m.get("uid") == uid), None)
        if not found:
            raise ApiError(f"Mode {uid} not found")
        ordered.append(found)
    listed_uids = set(uids)
    for m in items:
        if m.get("uid") not in listed_uids:
            ordered.append(m)
    api("POST", "/modes/order", ctx.obj["base"], json={"modes": ordered})
    click.echo(f"Mode order updated ({len(uids)} positioned)")


# ══════════════════════════════════════════════════════════════════
#  Alerts
# ══════════════════════════════════════════════════════════════════


@cli.group()
def alerts():
    """Manage temperature/sensor alerts."""


@alerts.command("list")
@click.pass_context
def alerts_list(ctx):
    """List all alerts."""
    data = api("GET", "/alerts", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    items = data if isinstance(data, list) else data.get("alerts", []) if data else []
    if not items:
        click.echo("No alerts configured")
        return
    for a in items:
        uid = a.get("uid", "?")
        name = a.get("name", uid)
        state = a.get("state", "?")
        min_v = a.get("min", "?")
        max_v = a.get("max", "?")
        shutdown = a.get("shutdown_on_activation", False)
        state_color = RED if state == "Active" else GREEN
        click.echo(f"  {_c(state_color, name)} (uid: {uid})")
        click.echo(f"    Range: {min_v} - {max_v}  |  State: {state}")
        src = a.get("channel_source", {})
        if src:
            click.echo(f"    Source: {src.get('channel_name', '?')} @ {src.get('device_uid', '?')[:16]}")
        if shutdown:
            click.echo(f"    {_c(RED, '!! Shutdown on activation')}")
        click.echo()


@alerts.command("create")
@click.argument("name")
@click.option("--min", "min_val", type=float, required=True, help="Min threshold")
@click.option("--max", "max_val", type=float, required=True, help="Max threshold")
@click.option("--device", required=True, help="Device UID")
@click.option("--channel", required=True, help="Channel name")
@click.option("--notify/--no-notify", default=True, help="Desktop notification")
@click.option("--shutdown/--no-shutdown", "shutdown_on_activation", default=False,
              help="Shutdown system on activation")
@click.pass_context
def alerts_create(ctx, name: str, min_val: float, max_val: float,
                   device: str, channel: str, notify: bool, shutdown_on_activation: bool):
    """Create a new alert."""
    payload = {
        "name": name,
        "min": min_val,
        "max": max_val,
        "channel_source": {"device_uid": device, "channel_name": channel},
        "desktop_notify": notify,
        "desktop_notify_audio": False,
        "desktop_notify_recovery": True,
        "shutdown_on_activation": shutdown_on_activation,
    }
    api("POST", "/alerts", ctx.obj["base"], json=payload)
    click.echo(f"Created alert: {name}")


@alerts.command("update")
@click.argument("alert_uid")
@click.option("--name", help="New name")
@click.option("--min", "min_val", type=float, help="New min threshold")
@click.option("--max", "max_val", type=float, help="New max threshold")
@click.option("--from-json", "json_file", type=click.Path(exists=True),
              help="Update from a JSON file")
@click.pass_context
def alerts_update(ctx, alert_uid: str, name: Optional[str], min_val: Optional[float],
                   max_val: Optional[float], json_file: Optional[str]):
    """Update an existing alert."""
    if json_file:
        with open(json_file) as f:
            payload = json.load(f)
        api("PUT", "/alerts", ctx.obj["base"], json=payload)
        click.echo(f"Updated alert from {json_file}")
        return
    all_alerts = api("GET", "/alerts", ctx.obj["base"])
    items = all_alerts if isinstance(all_alerts, list) else all_alerts.get("alerts", [])
    current = next((a for a in items if a.get("uid") == alert_uid), None)
    if not current:
        raise ApiError(f"Alert {alert_uid} not found")
    if name:
        current["name"] = name
    if min_val is not None:
        current["min"] = min_val
    if max_val is not None:
        current["max"] = max_val
    api("PUT", "/alerts", ctx.obj["base"], json=current)
    click.echo(f"Updated alert: {alert_uid}")


@alerts.command("delete")
@click.argument("alert_uid")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def alerts_delete(ctx, alert_uid: str, yes: bool):
    """Delete an alert."""
    if not yes:
        click.confirm(f"Delete alert {alert_uid}?", abort=True)
    api("DELETE", f"/alerts/{alert_uid}", ctx.obj["base"])
    click.echo(f"Deleted alert: {alert_uid}")


# ══════════════════════════════════════════════════════════════════
#  Custom Sensors
# ══════════════════════════════════════════════════════════════════


@cli.group("custom-sensors")
def custom_sensors():
    """Manage custom (virtual) sensors."""


@custom_sensors.command("list")
@click.pass_context
def custom_sensors_list(ctx):
    """List all custom sensors."""
    data = api("GET", "/custom-sensors", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    items = data if isinstance(data, list) else data.get("custom_sensors", []) if data else []
    if not items:
        click.echo("No custom sensors configured")
        return
    for s in items:
        uid = s.get("id", "?")
        cs_type = s.get("cs_type", "?")
        mix_fn = s.get("mix_function", "?")
        sources = s.get("sources", [])
        file_path = s.get("file_path")
        click.echo(f"  {_c(BOLD, uid)} ({cs_type})")
        click.echo(f"    Mix function: {mix_fn}")
        if file_path:
            click.echo(f"    File: {file_path}")
        if sources:
            click.echo(f"    Sources: {len(sources)}")
            for src in sources[:5]:
                ts = src.get("temp_source", {})
                w = src.get("weight", 1.0)
                click.echo(f"      - {ts.get('temp_name', '?')} @ {ts.get('device_uid', '?')[:16]} (weight: {w})")
        click.echo()


@custom_sensors.command("show")
@click.argument("sensor_id")
@click.pass_context
def custom_sensors_show(ctx, sensor_id: str):
    """Show details of a specific custom sensor."""
    data = api("GET", f"/custom-sensors/{sensor_id}", ctx.obj["base"])
    fmt_json(data)


@custom_sensors.command("create")
@click.argument("cs_type", type=click.Choice(["Mix", "Max", "Min", "Average", "WeightedAvg", "Delta"]))
@click.option("--source", "-s", multiple=True, required=True,
              help="Source as device_uid:channel_name (can repeat)")
@click.pass_context
def custom_sensors_create(ctx, cs_type: str, source: tuple):
    """Create a custom sensor from multiple source channels."""
    sources = []
    for s in source:
        parts = s.split(":")
        if len(parts) != 2:
            raise click.BadParameter(f"Source must be device_uid:channel_name, got: {s}")
        sources.append({"device_uid": parts[0], "temp_name": parts[1]})
    api("POST", "/custom-sensors", ctx.obj["base"],
        json={"cs_type": cs_type, "sources": sources})
    click.echo(f"Created custom sensor ({cs_type})")


@custom_sensors.command("update")
@click.argument("json_file", type=click.Path(exists=True))
@click.pass_context
def custom_sensors_update(ctx, json_file: str):
    """Update a custom sensor from a JSON file."""
    with open(json_file) as f:
        payload = json.load(f)
    api("PUT", "/custom-sensors", ctx.obj["base"], json=payload)
    click.echo("Custom sensor updated")


@custom_sensors.command("delete")
@click.argument("sensor_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def custom_sensors_delete(ctx, sensor_id: str, yes: bool):
    """Delete a custom sensor."""
    if not yes:
        click.confirm(f"Delete custom sensor {sensor_id}?", abort=True)
    api("DELETE", f"/custom-sensors/{sensor_id}", ctx.obj["base"])
    click.echo(f"Deleted custom sensor: {sensor_id}")


@custom_sensors.command("order")
@click.argument("json_file", type=click.Path(exists=True))
@click.pass_context
def custom_sensors_order(ctx, json_file: str):
    """Set custom sensor display order from a JSON file."""
    with open(json_file) as f:
        payload = json.load(f)
    api("POST", "/custom-sensors/order", ctx.obj["base"], json=payload)
    click.echo("Custom sensor order updated")


# ══════════════════════════════════════════════════════════════════
#  Settings
# ══════════════════════════════════════════════════════════════════


@cli.group()
def settings():
    """View and modify daemon settings."""


@settings.command("show")
@click.pass_context
def settings_show(ctx):
    """Show current daemon settings."""
    data = api("GET", "/settings", ctx.obj["base"])
    fmt_json(data)


@settings.command("update")
@click.option("--startup-delay", type=int, help="Startup delay in seconds")
@click.option("--apply-on-boot/--no-apply-on-boot", default=None,
              help="Re-apply settings on daemon startup")
@click.option("--poll-rate", type=float, help="Sensor polling interval (0.5-5.0 seconds)")
@click.option("--handle-dynamic-temps/--no-handle-dynamic-temps", default=None,
              help="Handle hotplug temperature sources")
@click.option("--liquidctl-integration/--no-liquidctl-integration", default=None,
              help="Enable liquidctl for AIO coolers")
@click.option("--from-json", "json_file", type=click.Path(exists=True),
              help="Update from a JSON file")
@click.pass_context
def settings_update(ctx, startup_delay: Optional[int], apply_on_boot: Optional[bool],
                     poll_rate: Optional[float], handle_dynamic_temps: Optional[bool],
                     liquidctl_integration: Optional[bool], json_file: Optional[str]):
    """Update daemon settings."""
    if json_file:
        with open(json_file) as f:
            payload = json.load(f)
        api("PATCH", "/settings", ctx.obj["base"], json=payload)
        click.echo("Settings updated from file")
        return
    payload = {}
    if startup_delay is not None:
        payload["startup_delay"] = startup_delay
    if apply_on_boot is not None:
        payload["apply_on_boot"] = apply_on_boot
    if poll_rate is not None:
        payload["poll_rate"] = poll_rate
    if handle_dynamic_temps is not None:
        payload["handle_dynamic_temps"] = handle_dynamic_temps
    if liquidctl_integration is not None:
        payload["liquidctl_integration"] = liquidctl_integration
    if not payload:
        raise click.UsageError("No settings to update (use flags or --from-json)")
    api("PATCH", "/settings", ctx.obj["base"], json=payload)
    click.echo("Settings updated")


@settings.command("devices")
@click.option("--uid", "device_uid", help="Show settings for a specific device")
@click.pass_context
def settings_devices(ctx, device_uid: Optional[str]):
    """Show device settings (all or specific)."""
    if device_uid:
        data = api("GET", f"/settings/devices/{device_uid}", ctx.obj["base"])
    else:
        data = api("GET", "/settings/devices", ctx.obj["base"])
    fmt_json(data)


@settings.command("update-device")
@click.argument("device_uid")
@click.argument("json_file", type=click.Path(exists=True))
@click.pass_context
def settings_update_device(ctx, device_uid: str, json_file: str):
    """Update settings for a specific device from a JSON file."""
    with open(json_file) as f:
        payload = json.load(f)
    api("PUT", f"/settings/devices/{device_uid}", ctx.obj["base"], json=payload)
    click.echo(f"Device settings updated for: {device_uid}")


@settings.command("ui")
@click.pass_context
def settings_ui(ctx):
    """Show UI settings."""
    data = api("GET", "/settings/ui", ctx.obj["base"])
    fmt_json(data)


@settings.command("update-ui")
@click.argument("json_file", type=click.Path(exists=True))
@click.pass_context
def settings_update_ui(ctx, json_file: str):
    """Update UI settings from a JSON file."""
    with open(json_file) as f:
        payload = json.load(f)
    api("PUT", "/settings/ui", ctx.obj["base"], json=payload)
    click.echo("UI settings updated")


# ══════════════════════════════════════════════════════════════════
#  Plugins
# ══════════════════════════════════════════════════════════════════


@cli.group()
def plugins():
    """Manage CoolerControl plugins."""


@plugins.command("list")
@click.pass_context
def plugins_list(ctx):
    """List installed plugins."""
    data = api("GET", "/plugins", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    if not data:
        click.echo("No plugins installed")
        return
    items = data if isinstance(data, list) else [data]
    for p in items:
        pid = p.get("id", p.get("plugin_id", "?"))
        name = p.get("name", pid)
        version = p.get("version", "?")
        enabled = p.get("enabled", "?")
        click.echo(f"  {_c(BOLD, name)}")
        click.echo(f"    ID:      {pid}")
        click.echo(f"    Version: {version}")
        click.echo(f"    Enabled: {enabled}")
        click.echo()


@plugins.command("config")
@click.argument("plugin_id")
@click.pass_context
def plugins_config(ctx, plugin_id: str):
    """Show configuration for a plugin."""
    data = api_raw("GET", f"/plugins/{plugin_id}/config", ctx.obj["base"])
    click.echo(data)


@plugins.command("update-config")
@click.argument("plugin_id")
@click.argument("config_file", type=click.Path(exists=True))
@click.pass_context
def plugins_update_config(ctx, plugin_id: str, config_file: str):
    """Update plugin configuration from a file."""
    with open(config_file) as f:
        config_text = f.read()
    url = f"{ctx.obj['base']}/plugins/{plugin_id}/config"
    token = _load_token()
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = SESSION.put(url, data=config_text, headers=headers, timeout=10)
    except requests.ConnectionError:
        raise ApiError("Cannot connect to coolercontrold")
    if resp.status_code not in (200, 204):
        raise ApiError(f"API error {resp.status_code}: {resp.text}")
    click.echo(f"Plugin {plugin_id} config updated")


@plugins.command("ui-check")
@click.argument("plugin_id")
@click.pass_context
def plugins_ui_check(ctx, plugin_id: str):
    """Check if a plugin has a UI component."""
    data = api("GET", f"/plugins/{plugin_id}/ui", ctx.obj["base"])
    fmt_json(data)


@plugins.command("ui-file")
@click.argument("plugin_id")
@click.argument("file_name")
@click.pass_context
def plugins_ui_file(ctx, plugin_id: str, file_name: str):
    """Retrieve a plugin UI file."""
    data = api_raw("GET", f"/plugins/{plugin_id}/ui/{file_name}", ctx.obj["base"])
    click.echo(data)


@plugins.command("lib")
@click.pass_context
def plugins_lib(ctx):
    """Retrieve the CoolerControl plugin UI library (JavaScript)."""
    data = api_raw("GET", "/plugins/lib/cc-plugin-lib.js", ctx.obj["base"])
    click.echo(data)


# ══════════════════════════════════════════════════════════════════
#  ThinkPad Fan Control
# ══════════════════════════════════════════════════════════════════


@cli.command("thinkpad-fan-control")
@click.option("--enable/--disable", required=True, help="Enable or disable ThinkPad fan control")
@click.pass_context
def thinkpad_fan_control(ctx, enable: bool):
    """Enable or disable ThinkPad fan control.

    Allows CoolerControl to override the ThinkPad embedded controller's
    fan management. Only applicable on Lenovo ThinkPad laptops.
    """
    api("PUT", "/thinkpad-fan-control", ctx.obj["base"], json={"enable": enable})
    click.echo(f"ThinkPad fan control {'enabled' if enable else 'disabled'}")


# ══════════════════════════════════════════════════════════════════
#  Detection
# ══════════════════════════════════════════════════════════════════


@cli.command("detect")
@click.option("--load-modules", is_flag=True, help="Also load kernel modules for detected hardware")
@click.pass_context
def detect(ctx, load_modules: bool):
    """Detect hardware (optionally load kernel modules)."""
    if load_modules:
        data = api("POST", "/detect", ctx.obj["base"])
    else:
        data = api("GET", "/detect", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    if data:
        fmt_json(data)
    else:
        click.echo("Hardware detection complete")


# ══════════════════════════════════════════════════════════════════
#  SSE Streaming (watch commands)
# ══════════════════════════════════════════════════════════════════


def _stream_sse(base: str, path: str, label: str, parse_json: bool = True):
    """Stream Server-Sent Events from the daemon."""
    url = f"{base}{path}"
    token = _load_token()
    headers = {"Accept": "text/event-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    click.echo(f"Streaming {label} (Ctrl+C to stop)...", err=True)

    try:
        with SESSION.get(url, headers=headers, stream=True, timeout=None) as resp:
            if resp.status_code != 200:
                raise ApiError(f"SSE connection failed: HTTP {resp.status_code}")
            for line in resp.iter_lines(decode_unicode=True):
                if line and line.startswith("data:"):
                    data_str = line[5:].strip()
                    if parse_json:
                        try:
                            data = json.loads(data_str)
                            click.echo(json.dumps(data, indent=2))
                        except ValueError:
                            click.echo(data_str)
                    else:
                        click.echo(data_str)
    except KeyboardInterrupt:
        click.echo("\nStopped.", err=True)
    except requests.ConnectionError:
        raise ApiError(f"Cannot connect to coolercontrold at {base}. Is the daemon running?")


@cli.command("watch-status")
@click.pass_context
def watch_status(ctx):
    """Stream live status updates (temps, fan speeds) via SSE."""
    _stream_sse(ctx.obj["base"], "/sse/status", "status updates")


@cli.command("watch-logs")
@click.pass_context
def watch_logs(ctx):
    """Stream live log events via SSE."""
    _stream_sse(ctx.obj["base"], "/sse/logs", "log events", parse_json=False)


@cli.command("watch-alerts")
@click.pass_context
def watch_alerts(ctx):
    """Stream live alert events via SSE."""
    _stream_sse(ctx.obj["base"], "/sse/alerts", "alert events")


@cli.command("watch-modes")
@click.pass_context
def watch_modes(ctx):
    """Stream mode activation events via SSE."""
    _stream_sse(ctx.obj["base"], "/sse/modes", "mode events")


# ══════════════════════════════════════════════════════════════════
#  Logs
# ══════════════════════════════════════════════════════════════════


@cli.command("logs")
@click.option("--lines", "-n", type=int, default=50, help="Number of lines to show")
@click.pass_context
def show_logs(ctx, lines: int):
    """Show daemon logs."""
    data = api("GET", "/logs", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    if isinstance(data, list):
        for line in data[-lines:]:
            click.echo(line)
    elif isinstance(data, str):
        for line in data.strip().split("\n")[-lines:]:
            click.echo(line)
    else:
        fmt_json(data)


# ══════════════════════════════════════════════════════════════════
#  Quick shortcuts (top-level convenience commands)
# ══════════════════════════════════════════════════════════════════


@cli.command("fan")
@click.argument("device_uid")
@click.argument("channel")
@click.argument("duty", type=int)
@click.pass_context
def quick_fan(ctx, device_uid: str, channel: str, duty: int):
    """Quick: set fan duty cycle (shortcut for devices set-manual)."""
    if duty < 0 or duty > 100:
        raise click.BadParameter("Duty must be 0-100")
    api("PUT", f"/devices/{device_uid}/settings/{channel}/manual",
        ctx.obj["base"], json={"speed_fixed": duty})
    click.echo(f"{channel} -> {duty}%")


@cli.command("temps")
@click.pass_context
def quick_temps(ctx):
    """Quick: show all temperatures with color coding."""
    data = api("POST", "/status", ctx.obj["base"])
    for device in data or []:
        name = device.get("d_name", "?")
        for status_entry in device.get("status", []):
            for t in status_entry.get("temps", []):
                temp_val = t["temp"]
                click.echo(f"  {name:20s} {t['name']:30s} {_temp_color(temp_val)}C")


@cli.command("fans")
@click.pass_context
def quick_fans(ctx):
    """Quick: show all fan speeds and duties."""
    data = api("POST", "/status", ctx.obj["base"])
    for device in data or []:
        name = device.get("d_name", "?")
        for status_entry in device.get("status", []):
            for ch in status_entry.get("channels", []):
                duty = ch.get("duty")
                rpm = ch.get("rpm")
                duty_str = f"{duty:5.1f}%" if duty is not None else "  N/A"
                rpm_str = f"{rpm:5d} RPM" if rpm is not None else ""
                click.echo(f"  {name:20s} {ch['name']:30s} {duty_str}  {rpm_str}")


# ══════════════════════════════════════════════════════════════════
#  Export (Nix / Home Manager)
# ══════════════════════════════════════════════════════════════════


def _to_nix(data, indent="", key_field=None):
    """Convert Python data to Nix-ish representation."""
    import re

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
            # Convert to attrset
            lines = ["{"]
            for x in data:
                key = _safe_key(x[key_field])
                val = _to_nix(x, indent + "  ")
                lines.append(f"{indent}  {key} = {val};")
            lines.append(f"{indent}}}")
            return "\n".join(lines)
        else:
            # Inline short simple lists
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
        
        # Inline very short simple dicts
        if len(data) <= 2 and all(isinstance(v, (int, float, str, bool)) or v is None for v in data.values()):
            return "{ " + "; ".join(f"{k} = {_to_nix(v)}" for k, v in data.items()) + "; }"

        lines = ["{\n"]
        for k, v in data.items():
            lines.append(f"{indent}  {k} = {_to_nix(v, indent + '  ')};\n")
        lines.append(f"{indent}}}")
        return "".join(lines)
    return str(data)


@cli.command("export-config")
@click.pass_context
def export_config(ctx):
    """Export current daemon state as a Nix attrset for Home Manager.

    Outputs a 1:1 declarative configuration block that can be pasted
    directly into your coolercontrol.nix file.
    """
    import datetime
    import re

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
        
        # settings is GET /devices/{uid}/settings
        settings = api("GET", f"/devices/{uid}/settings", base) or {}
        
        # legacy690 is usually only checkable via hardware info if GET /asetek690 fails (405)
        # We will try to fetch it but catch the 405
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
    # Map speed_profile from [temp, duty] to {temp, duty}
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
    plugins = plugins_resp if isinstance(plugins_resp, list) else [plugins_resp] if plugins_resp else []
    for p in plugins:
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
                # Skip if unauthorized
                continue
            raise e
    click.echo("  };\n")

    # ── Alerts ──
    click.echo("  # ── Alerts ──")
    resp = api("GET", "/alerts", base)
    alerts = resp.get("alerts", []) if isinstance(resp, dict) else resp or []
    click.echo(f"  alerts = {_to_nix(alerts, '  ')};\n")

    # ── Global Settings ──
    click.echo("  # ── Global Settings ──")
    settings = api("GET", "/settings", base) or {}
    click.echo(f"  settings = {_to_nix(settings, '  ')};\n")

    click.echo("}")


def main():
    cli()


if __name__ == "__main__":
    main()
