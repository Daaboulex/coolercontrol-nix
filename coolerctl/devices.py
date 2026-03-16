"""Device listing and per-channel control."""

from typing import Optional

import click

from .api import api
from .output import fmt_json, _c, BOLD


@click.group()
def devices():
    """List and manage cooling devices."""


@devices.command("list")
@click.pass_context
def devices_list(ctx):
    """List all detected devices."""
    data = api("GET", "/devices", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    devs = data if isinstance(data, list) else data.get("devices", []) if data else []
    for dev in devs:
        uid = dev.get("uid", "?")
        name = dev.get("name", uid)
        d_type = dev.get("d_type", "")
        info_data = dev.get("info", {})
        model = info_data.get("model", dev.get("model", ""))
        click.echo(f"  {_c(BOLD, name)}")
        click.echo(f"    UID:    {uid}")
        click.echo(f"    Type:   {d_type}")
        if model:
            click.echo(f"    Model:  {model}")
        channels = info_data.get("channels", {})
        if channels:
            fan_ch = [k for k, v in channels.items() if v.get("speed_options")]
            temp_ch = [k for k, v in channels.items()
                       if not v.get("speed_options") and not v.get("lcd_info") and not v.get("lighting_modes")]
            lcd_ch = [k for k, v in channels.items() if v.get("lcd_info")]
            light_ch = [k for k, v in channels.items() if v.get("lighting_modes")]
            if fan_ch:
                click.echo(f"    Fan channels:      {len(fan_ch)} ({', '.join(fan_ch[:5])})")
            if temp_ch:
                click.echo(f"    Temp sensors:      {len(temp_ch)} ({', '.join(temp_ch[:5])})")
            if lcd_ch:
                click.echo(f"    LCD screens:       {len(lcd_ch)} ({', '.join(lcd_ch)})")
            if light_ch:
                click.echo(f"    Lighting channels: {len(light_ch)} ({', '.join(light_ch)})")
        click.echo()


@devices.command("settings")
@click.argument("device_uid")
@click.pass_context
def devices_settings(ctx, device_uid: str):
    """Show settings for a device."""
    data = api("GET", f"/devices/{device_uid}/settings", ctx.obj["base"])
    fmt_json(data)


@devices.command("set-manual")
@click.argument("device_uid")
@click.argument("channel")
@click.argument("duty", type=int)
@click.pass_context
def devices_set_manual(ctx, device_uid: str, channel: str, duty: int):
    """Set a channel to manual duty cycle (0-100%)."""
    if duty < 0 or duty > 100:
        raise click.BadParameter("Duty must be 0-100")
    api("PUT", f"/devices/{device_uid}/settings/{channel}/manual",
        ctx.obj["base"], json={"speed_fixed": duty})
    click.echo(f"Set {channel} -> {duty}% (manual)")


@devices.command("set-profile")
@click.argument("device_uid")
@click.argument("channel")
@click.argument("profile_uid")
@click.pass_context
def devices_set_profile(ctx, device_uid: str, channel: str, profile_uid: str):
    """Assign a profile to a device channel."""
    api("PUT", f"/devices/{device_uid}/settings/{channel}/profile",
        ctx.obj["base"], json={"profile_uid": profile_uid})
    click.echo(f"Set {channel} -> profile {profile_uid}")


@devices.command("reset-channel")
@click.argument("device_uid")
@click.argument("channel")
@click.pass_context
def devices_reset(ctx, device_uid: str, channel: str):
    """Reset a channel to default."""
    api("PUT", f"/devices/{device_uid}/settings/{channel}/reset", ctx.obj["base"])
    click.echo(f"Reset {channel}")


@devices.command("set-pwm")
@click.argument("device_uid")
@click.argument("channel")
@click.argument("pwm_mode", type=int)
@click.pass_context
def devices_set_pwm(ctx, device_uid: str, channel: str, pwm_mode: int):
    """Set PWM mode for a channel (DEPRECATED)."""
    api("PUT", f"/devices/{device_uid}/settings/{channel}/pwm",
        ctx.obj["base"], json={"pwm_mode": pwm_mode})
    click.echo(f"Set {channel} PWM mode -> {pwm_mode}")


@devices.command("set-lighting")
@click.argument("device_uid")
@click.argument("channel")
@click.option("--mode", "-m", required=True, help="Lighting mode name")
@click.option("--color", "-c", multiple=True, help="RGB color as R,G,B (can repeat)")
@click.option("--speed", "-s", help="Animation speed")
@click.pass_context
def devices_set_lighting(ctx, device_uid: str, channel: str, mode: str,
                          color: tuple, speed: Optional[str]):
    """Set channel lighting mode and colors."""
    colors = []
    for c in color:
        parts = [int(x.strip()) for x in c.split(",")]
        if len(parts) != 3:
            raise click.BadParameter(f"Color must be R,G,B: got {c}")
        colors.append(parts)
    payload = {"mode": mode, "colors": colors}
    if speed:
        payload["speed"] = speed
    api("PUT", f"/devices/{device_uid}/settings/{channel}/lighting",
        ctx.obj["base"], json=payload)
    click.echo(f"Set {channel} lighting -> {mode}")


@devices.command("set-lcd")
@click.argument("device_uid")
@click.argument("channel")
@click.option("--mode", "-m", required=True, help="LCD mode (none, static, carousel, liquid-temp)")
@click.option("--brightness", "-b", type=int, help="LCD brightness 0-100")
@click.pass_context
def devices_set_lcd(ctx, device_uid: str, channel: str, mode: str,
                     brightness: Optional[int]):
    """Set channel LCD mode."""
    payload = {"mode": mode, "colors": []}
    if brightness is not None:
        payload["brightness"] = brightness
    api("PUT", f"/devices/{device_uid}/settings/{channel}/lcd",
        ctx.obj["base"], json=payload)
    click.echo(f"Set {channel} LCD -> {mode}")


@devices.command("asetek690")
@click.argument("device_uid")
@click.option("--legacy/--no-legacy", default=False, help="Set legacy AseTek 690 mode")
@click.pass_context
def devices_asetek690(ctx, device_uid: str, legacy: bool):
    """Set AseTek 690 legacy mode for a device."""
    api("PATCH", f"/devices/{device_uid}/asetek690",
        ctx.obj["base"], json={"is_legacy690": legacy})
    click.echo(f"AseTek 690 legacy mode {'enabled' if legacy else 'disabled'} for {device_uid}")
