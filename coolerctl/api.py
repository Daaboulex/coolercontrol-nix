"""HTTP client for coolercontrold REST API."""

import json
import os

import click
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_BASE = "https://localhost:11987"
TOKEN_PATH = os.path.expanduser("~/.config/coolerctl/token")
SESSION = requests.Session()
SESSION.verify = False  # CoolerControl uses self-signed certs by default


class ApiError(click.ClickException):
    """API call failed."""


def _load_token() -> str | None:
    """Load saved bearer token from disk."""
    if os.path.isfile(TOKEN_PATH):
        with open(TOKEN_PATH) as f:
            return f.read().strip()
    return os.environ.get("COOLERCONTROL_TOKEN")


def api(method: str, path: str, base: str = DEFAULT_BASE, **kwargs) -> dict | list | None:
    """Make an API call to coolercontrold."""
    url = f"{base}{path}"
    token = _load_token()
    if token:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
    try:
        resp = SESSION.request(method, url, timeout=kwargs.pop("timeout", 10), **kwargs)
    except requests.ConnectionError:
        raise ApiError(f"Cannot connect to coolercontrold at {base}. Is the daemon running?")
    if resp.status_code == 200:
        try:
            return resp.json()
        except ValueError:
            return None
    elif resp.status_code == 204:
        return None
    else:
        detail = ""
        try:
            detail = resp.json().get("error", resp.text)
        except (ValueError, AttributeError):
            detail = resp.text
        raise ApiError(f"API error {resp.status_code}: {detail}")


def api_upload(method: str, path: str, file_path: str, base: str = DEFAULT_BASE) -> dict | None:
    """Upload a file via multipart form to coolercontrold."""
    url = f"{base}{path}"
    token = _load_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if not os.path.isfile(file_path):
        raise ApiError(f"File not found: {file_path}")
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        try:
            resp = SESSION.request(method, url, files=files, headers=headers, timeout=30)
        except requests.ConnectionError:
            raise ApiError(f"Cannot connect to coolercontrold at {base}. Is the daemon running?")
    if resp.status_code in (200, 204):
        try:
            return resp.json()
        except ValueError:
            return None
    else:
        detail = ""
        try:
            detail = resp.json().get("error", resp.text)
        except (ValueError, AttributeError):
            detail = resp.text
        raise ApiError(f"API error {resp.status_code}: {detail}")


def api_raw(method: str, path: str, base: str = DEFAULT_BASE, **kwargs) -> str:
    """Make an API call returning raw text."""
    url = f"{base}{path}"
    token = _load_token()
    if token:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
    try:
        resp = SESSION.request(method, url, timeout=kwargs.pop("timeout", 10), **kwargs)
    except requests.ConnectionError:
        raise ApiError(f"Cannot connect to coolercontrold at {base}. Is the daemon running?")
    if resp.status_code in (200, 204):
        return resp.text
    else:
        raise ApiError(f"API error {resp.status_code}: {resp.text}")
