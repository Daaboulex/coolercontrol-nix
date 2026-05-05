"""Fan curve profile management."""

import json
from typing import Optional

import click

from .api import api, ApiError
from .output import fmt_json, _c, BOLD


@click.group()
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
    all_profiles = api("GET", "/profiles", ctx.obj["base"])
    items = all_profiles if isinstance(all_profiles, list) else all_profiles.get("profiles", [])
    ordered = []
    for uid in uids:
        found = next((p for p in items if p.get("uid") == uid), None)
        if not found:
            raise ApiError(f"Profile {uid} not found")
        ordered.append(found)
    listed_uids = set(uids)
    for p in items:
        if p.get("uid") not in listed_uids:
            ordered.append(p)
    api("POST", "/profiles/order", ctx.obj["base"], json={"profiles": ordered})
    click.echo(f"Profile order updated ({len(uids)} positioned)")
