"""Logging helpers with ANSI colors."""
from __future__ import annotations

import sys
from typing import Iterable

COLORS = {
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "reset": "\033[0m",
}


def _colorize(text: str, color: str) -> str:
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def success(message: str) -> None:
    print(_colorize(f"✅ {message}", "green"))


def warning(message: str) -> None:
    print(_colorize(f"⚠️ {message}", "yellow"))


def error(message: str) -> None:
    print(_colorize(f"❌ {message}", "red"), file=sys.stderr)


def bullet_list(title: str, items: Iterable[str]) -> None:
    print(_colorize(title, "green"))
    for idx, item in enumerate(items, start=1):
        print(f"  {idx}. {item}")
