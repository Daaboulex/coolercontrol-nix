"""SSE streaming and log viewing."""

import json

import click
import requests

from .api import ApiError, SESSION, _load_token


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


@click.command("watch-status")
@click.pass_context
def watch_status(ctx):
    """Stream live status updates (temps, fan speeds) via SSE."""
    _stream_sse(ctx.obj["base"], "/sse/status", "status updates")


@click.command("watch-logs")
@click.pass_context
def watch_logs(ctx):
    """Stream live log events via SSE."""
    _stream_sse(ctx.obj["base"], "/sse/logs", "log events", parse_json=False)


@click.command("watch-alerts")
@click.pass_context
def watch_alerts(ctx):
    """Stream live alert events via SSE."""
    _stream_sse(ctx.obj["base"], "/sse/alerts", "alert events")


@click.command("watch-modes")
@click.pass_context
def watch_modes(ctx):
    """Stream mode activation events via SSE."""
    _stream_sse(ctx.obj["base"], "/sse/modes", "mode events")


@click.command("logs")
@click.option("--lines", "-n", type=int, default=50, help="Number of lines to show")
@click.pass_context
def show_logs(ctx, lines: int):
    """Show daemon logs."""
    from .api import api
    from .output import fmt_json
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
