"""Top-level convenience commands."""

import click

from .api import api
from .output import fmt_json, _temp_color


@click.command("fan")
@click.argument("device_uid")
@click.argument("channel")
@click.argument("duty", type=int)
@click.pass_context
def quick_fan(ctx, device_uid: str, channel: str, duty: int):
    """Quick: set fan duty cycle (shortcut for devices set-manual)."""
    if duty < 0 or duty > 100:
        raise click.BadParameter("Duty must be 0-100")
    api("PUT", f"/devices/{device_uid}/settings/{channel}/manual",
        ctx.obj["base"], json={"speed_fixed": duty})
    click.echo(f"{channel} -> {duty}%")


@click.command("temps")
@click.pass_context
def quick_temps(ctx):
    """Quick: show all temperatures with color coding."""
    data = api("POST", "/status", ctx.obj["base"])
    for device in data or []:
        name = device.get("d_name", "?")
        for status_entry in device.get("status", []):
            for t in status_entry.get("temps", []):
                temp_val = t["temp"]
                click.echo(f"  {name:20s} {t['name']:30s} {_temp_color(temp_val)}C")


@click.command("fans")
@click.pass_context
def quick_fans(ctx):
    """Quick: show all fan speeds and duties."""
    data = api("POST", "/status", ctx.obj["base"])
    for device in data or []:
        name = device.get("d_name", "?")
        for status_entry in device.get("status", []):
            for ch in status_entry.get("channels", []):
                duty = ch.get("duty")
                rpm = ch.get("rpm")
                duty_str = f"{duty:5.1f}%" if duty is not None else "  N/A"
                rpm_str = f"{rpm:5d} RPM" if rpm is not None else ""
                click.echo(f"  {name:20s} {ch['name']:30s} {duty_str}  {rpm_str}")


@click.command("thinkpad-fan-control")
@click.option("--enable/--disable", required=True, help="Enable or disable ThinkPad fan control")
@click.pass_context
def thinkpad_fan_control(ctx, enable: bool):
    """Enable or disable ThinkPad fan control.

    Allows CoolerControl to override the ThinkPad embedded controller's
    fan management. Only applicable on Lenovo ThinkPad laptops.
    """
    api("PUT", "/thinkpad-fan-control", ctx.obj["base"], json={"enable": enable})
    click.echo(f"ThinkPad fan control {'enabled' if enable else 'disabled'}")


@click.command("detect")
@click.option("--load-modules", is_flag=True, help="Also load kernel modules for detected hardware")
@click.pass_context
def detect(ctx, load_modules: bool):
    """Detect hardware (optionally load kernel modules)."""
    if load_modules:
        data = api("POST", "/detect", ctx.obj["base"])
    else:
        data = api("GET", "/detect", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    if data:
        fmt_json(data)
    else:
        click.echo("Hardware detection complete")
