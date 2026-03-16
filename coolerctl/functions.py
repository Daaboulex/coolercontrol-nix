"""Fan curve function management."""

import json
from typing import Optional

import click

from .api import api, ApiError
from .output import fmt_json, _c, BOLD


@click.group()
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
