"""Process-wide UI language for NOWA demos.

Precedence when a demo starts: explicit ``--lang`` > ``NOWA_LANG`` > a saved
in-UI preference > English. Call :func:`get_language` at use time so a toggle
is visible on the next frame.
"""

from __future__ import annotations

import os

SUPPORTED = ("en", "ru")
DEFAULT_LANG = "en"

_override: str | None = None


def set_language(lang: str) -> None:
    """Pin the language for this process, ahead of ``NOWA_LANG``."""

    global _override
    if lang not in SUPPORTED:
        raise ValueError(f"Unsupported language: {lang}")
    _override = lang


def reset_language() -> None:
    """Drop the pin so ``NOWA_LANG`` or the English default applies again."""

    global _override
    _override = None


def get_language() -> str:
    if _override in SUPPORTED:
        return _override
    env = os.environ.get("NOWA_LANG", "").strip().lower()
    if env in SUPPORTED:
        return env
    return DEFAULT_LANG


def resolve_lang(explicit: str | None = None) -> str:
    """Resolve a startup language. ``explicit`` is the ``--lang`` value."""

    if explicit in SUPPORTED:
        return explicit
    return get_language()


__all__ = [
    "DEFAULT_LANG",
    "SUPPORTED",
    "get_language",
    "reset_language",
    "resolve_lang",
    "set_language",
]
