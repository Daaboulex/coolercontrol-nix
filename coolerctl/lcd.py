"""LCD screen image management."""

from typing import Optional

import click

from .api import api, api_upload
from .output import fmt_json


@click.group()
def lcd():
    """Manage LCD screen images."""


@lcd.command("list-images")
@click.argument("device_uid")
@click.argument("channel")
@click.pass_context
def lcd_list_images(ctx, device_uid: str, channel: str):
    """List LCD images for a device channel."""
    data = api("GET", f"/devices/{device_uid}/settings/{channel}/lcd/images", ctx.obj["base"])
    fmt_json(data)


@lcd.command("upload-image")
@click.argument("device_uid")
@click.argument("channel")
@click.argument("image_path", type=click.Path(exists=True))
@click.pass_context
def lcd_upload_image(ctx, device_uid: str, channel: str, image_path: str):
    """Upload an image to an LCD screen (processes for optimal display)."""
    result = api_upload("POST", f"/devices/{device_uid}/settings/{channel}/lcd/images",
                        image_path, ctx.obj["base"])
    click.echo(f"Uploaded image to {channel} on {device_uid}")
    if result:
        fmt_json(result)


@lcd.command("update-settings")
@click.argument("device_uid")
@click.argument("channel")
@click.option("--mode", "-m", help="LCD mode")
@click.option("--brightness", "-b", type=int, help="Brightness 0-100")
@click.option("--orientation", type=int, help="Screen orientation in degrees")
@click.pass_context
def lcd_update_settings(ctx, device_uid: str, channel: str, mode: Optional[str],
                         brightness: Optional[int], orientation: Optional[int]):
    """Update LCD image display settings."""
    payload = {}
    if mode:
        payload["mode"] = mode
    if brightness is not None:
        payload["brightness"] = brightness
    if orientation is not None:
        payload["orientation"] = orientation
    if not payload:
        raise click.UsageError("No settings to update (use --mode, --brightness, or --orientation)")
    api("PUT", f"/devices/{device_uid}/settings/{channel}/lcd/images",
        ctx.obj["base"], json=payload)
    click.echo(f"Updated LCD settings for {channel} on {device_uid}")


@lcd.command("set-shutdown-image")
@click.argument("device_uid")
@click.argument("channel")
@click.argument("image_path", type=click.Path(exists=True))
@click.pass_context
def lcd_set_shutdown_image(ctx, device_uid: str, channel: str, image_path: str):
    """Set the image displayed when the daemon shuts down."""
    result = api_upload("PUT", f"/devices/{device_uid}/settings/{channel}/lcd/shutdown-image",
                        image_path, ctx.obj["base"])
    click.echo(f"Set shutdown image for {channel} on {device_uid}")
    if result:
        fmt_json(result)


@lcd.command("clear-shutdown-image")
@click.argument("device_uid")
@click.argument("channel")
@click.pass_context
def lcd_clear_shutdown_image(ctx, device_uid: str, channel: str):
    """Clear the LCD shutdown image."""
    api("DELETE", f"/devices/{device_uid}/settings/{channel}/lcd/shutdown-image", ctx.obj["base"])
    click.echo(f"Cleared shutdown image for {channel} on {device_uid}")
