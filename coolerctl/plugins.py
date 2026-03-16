"""Plugin management."""

import click
import requests

from .api import api, api_raw, ApiError, SESSION, _load_token
from .output import fmt_json, _c, BOLD


@click.group()
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
