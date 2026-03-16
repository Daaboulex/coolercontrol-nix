"""Temperature/sensor alert management."""

import json
from typing import Optional

import click

from .api import api, ApiError
from .output import fmt_json, _c, GREEN, RED


@click.group()
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
