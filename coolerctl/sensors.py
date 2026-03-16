"""Custom (virtual) sensor management."""

import json

import click

from .api import api, ApiError
from .output import fmt_json, _c, BOLD


@click.group("custom-sensors")
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
