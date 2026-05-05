"""Mode management (profile combinations)."""

import json
from typing import Optional

import click

from .api import api, ApiError
from .output import fmt_json, _c, BOLD


@click.group()
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
