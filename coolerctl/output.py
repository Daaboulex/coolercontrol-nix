"""Terminal output formatting and color helpers."""

import json
import sys

import click

BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
RESET = "\033[0m"


def _use_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(color: str, text: str) -> str:
    if _use_color():
        return f"{color}{text}{RESET}"
    return str(text)


def _temp_color(temp: float) -> str:
    """Color-code a temperature value."""
    if temp > 80:
        return _c(RED, f"{temp:6.1f}")
    elif temp > 60:
        return _c(YELLOW, f"{temp:6.1f}")
    else:
        return _c(GREEN, f"{temp:6.1f}")


def fmt_json(data, compact: bool = False):
    """Print JSON output."""
    if compact:
        click.echo(json.dumps(data, separators=(",", ":")))
    else:
        click.echo(json.dumps(data, indent=2))
