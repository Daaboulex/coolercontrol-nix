"""coolerctl — CLI for CoolerControl daemon REST API.

Wraps the coolercontrold HTTP API for scripting, automation,
StreamController integration, and LLM-driven fan curve tuning.

Covers all 79 endpoints from the CoolerControl OpenAPI v4.0.0 spec.
"""

import click

from .api import DEFAULT_BASE

# ── Root CLI group ──


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


# ── Register command groups ──

from .auth import auth, tokens  # noqa: E402
from .devices import devices  # noqa: E402
from .lcd import lcd  # noqa: E402
from .profiles import profiles  # noqa: E402
from .functions import functions  # noqa: E402
from .modes import modes  # noqa: E402
from .alerts import alerts  # noqa: E402
from .sensors import custom_sensors  # noqa: E402
from .settings import settings  # noqa: E402
from .plugins import plugins  # noqa: E402

cli.add_command(auth)
cli.add_command(tokens)
cli.add_command(devices)
cli.add_command(lcd)
cli.add_command(profiles)
cli.add_command(functions)
cli.add_command(modes)
cli.add_command(alerts)
cli.add_command(custom_sensors)
cli.add_command(settings)
cli.add_command(plugins)

# ── Register top-level commands ──

from .daemon import handshake, health, shutdown, acknowledge, status  # noqa: E402
from .streaming import watch_status, watch_logs, watch_alerts, watch_modes, show_logs  # noqa: E402
from .shortcuts import quick_fan, quick_temps, quick_fans, thinkpad_fan_control, detect  # noqa: E402
from .export import export_config  # noqa: E402

cli.add_command(handshake)
cli.add_command(health)
cli.add_command(shutdown)
cli.add_command(acknowledge)
cli.add_command(status)
cli.add_command(watch_status)
cli.add_command(watch_logs)
cli.add_command(watch_alerts)
cli.add_command(watch_modes)
cli.add_command(show_logs)
cli.add_command(quick_fan)
cli.add_command(quick_temps)
cli.add_command(quick_fans)
cli.add_command(thinkpad_fan_control)
cli.add_command(detect)
cli.add_command(export_config)


def main():
    cli()
