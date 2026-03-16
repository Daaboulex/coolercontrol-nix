"""Authentication and token management."""

import os
from typing import Optional

import click

from .api import api, ApiError, SESSION, TOKEN_PATH


@click.group()
def auth():
    """Manage authentication."""


@auth.command("login")
@click.option("--password", "-p", prompt=True, hide_input=True, help="Admin password")
@click.pass_context
def auth_login(ctx, password: str):
    """Login and save a bearer token for future CLI use."""
    base = ctx.obj["base"]
    import base64
    auth_bytes = f"CCAdmin:{password}".encode("utf-8")
    auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")
    headers = {"Authorization": f"Basic {auth_b64}"}

    resp = SESSION.post(f"{base}/login", headers=headers, timeout=10)
    if resp.status_code != 200:
        resp = SESSION.post(f"{base}/login", json={"current_password": password}, timeout=10)

    if resp.status_code != 200:
        raise ApiError(f"Login failed (HTTP {resp.status_code}) — check your password")

    resp = SESSION.post(f"{base}/tokens", timeout=10,
                        json={"label": "coolerctl"})
    if resp.status_code != 200:
        raise ApiError(f"Failed to create token: {resp.text}")
    token_data = resp.json()
    token = token_data.get("token", "")
    if not token:
        raise ApiError("No token in response")
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(token)
    os.chmod(TOKEN_PATH, 0o600)
    click.echo(f"Logged in — token saved to {TOKEN_PATH}")


@auth.command("logout")
@click.pass_context
def auth_logout_api(ctx):
    """Logout from the daemon (invalidates session)."""
    api("POST", "/logout", ctx.obj["base"])
    if os.path.isfile(TOKEN_PATH):
        os.remove(TOKEN_PATH)
    click.echo("Logged out")


@auth.command("verify")
@click.pass_context
def auth_verify(ctx):
    """Verify current session authentication."""
    try:
        api("POST", "/verify-session", ctx.obj["base"])
        click.echo("Session is valid")
    except ApiError as e:
        click.echo(f"Session invalid: {e}", err=True)
        import sys
        sys.exit(1)


@auth.command("set-password")
@click.option("--current-password", "-c", prompt="Current password", hide_input=True,
              help="Current admin password")
@click.option("--new-password", "-p", prompt="New password", hide_input=True,
              confirmation_prompt=True, help="New admin password")
@click.pass_context
def auth_set_password(ctx, current_password: str, new_password: str):
    """Set the daemon admin password."""
    api("POST", "/set-passwd", ctx.obj["base"],
        json={"current_password": current_password, "new_password": new_password})
    click.echo("Password set")


@auth.command("token")
@click.argument("token_value")
def auth_set_token(token_value: str):
    """Set a bearer token directly (from CoolerControl UI)."""
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(token_value)
    os.chmod(TOKEN_PATH, 0o600)
    click.echo(f"Token saved to {TOKEN_PATH}")


@auth.command("status")
def auth_status():
    """Check if a token is configured."""
    from .api import _load_token
    token = _load_token()
    if token:
        click.echo(f"Token configured ({len(token)} chars)")
    else:
        click.echo("No token configured")


@auth.command("clear")
def auth_clear():
    """Remove saved token."""
    if os.path.isfile(TOKEN_PATH):
        os.remove(TOKEN_PATH)
        click.echo("Token removed")
    else:
        click.echo("No token to remove")


# ── Tokens group ──


@click.group()
def tokens():
    """Manage API access tokens."""


@tokens.command("list")
@click.pass_context
def tokens_list(ctx):
    """List all access tokens."""
    from .output import fmt_json
    data = api("GET", "/tokens", ctx.obj["base"])
    if ctx.obj["json"]:
        fmt_json(data)
        return
    if not data:
        click.echo("No tokens found")
        return
    for t in data if isinstance(data, list) else [data]:
        tid = t.get("id", t.get("token_id", "?"))
        label = t.get("label", t.get("name", "?"))
        created = t.get("created_at", "")
        expires = t.get("expires_at", "never")
        click.echo(f"  {tid:40s} {label:20s} created={created}  expires={expires}")


@tokens.command("create")
@click.option("--label", "-l", default="coolerctl", help="Token label/name")
@click.option("--expires", help="Expiration timestamp (ISO 8601)")
@click.pass_context
def tokens_create(ctx, label: str, expires: Optional[str]):
    """Create a new access token."""
    from .output import fmt_json
    payload = {"label": label}
    if expires:
        payload["expires_at"] = expires
    data = api("POST", "/tokens", ctx.obj["base"], json=payload)
    if ctx.obj["json"]:
        fmt_json(data)
        return
    if data and data.get("token"):
        click.echo(f"Token created: {data['token']}")
        click.echo("Save this token — it will not be shown again.")
    else:
        fmt_json(data)


@tokens.command("delete")
@click.argument("token_id")
@click.pass_context
def tokens_delete(ctx, token_id: str):
    """Delete an access token."""
    api("DELETE", f"/tokens/{token_id}", ctx.obj["base"])
    click.echo(f"Deleted token: {token_id}")
