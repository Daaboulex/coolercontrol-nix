"""Daemon operations: handshake, health, shutdown, acknowledge, status."""

import sys
from typing import Optional

import click

from .api import api
from .output import fmt_json, _c, _temp_color, BOLD, GREEN, RED, YELLOW


@click.command()
@click.pass_context
def handshake(ctx):
    """Verify daemon connection (no auth required)."""
    from .api import ApiError
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


@click.command()
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


@click.command()
@click.pass_context
def shutdown(ctx):
    """Shutdown the CoolerControl daemon."""
    api("POST", "/shutdown", ctx.obj["base"])
    click.echo("Daemon shutdown requested")


@click.command()
@click.pass_context
def acknowledge(ctx):
    """Acknowledge daemon log issues."""
    api("POST", "/acknowledge", ctx.obj["base"])
    click.echo("Log issues acknowledged")


@click.command()
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
        status_entries = device.get("status", device.get("status_history", []))
        if isinstance(status_entries, list) and status_entries:
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
