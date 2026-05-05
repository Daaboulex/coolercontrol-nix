"""Daemon settings management."""

import json
from typing import Optional

import click

from .api import api
from .output import fmt_json


@click.group()
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
