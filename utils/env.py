"""Utility helpers for reading environment variables used by Fragment."""

from __future__ import annotations

import os
from typing import Optional

_TRUE_VALUES = {"1", "true", "t", "yes", "y", "on", "enable", "enabled"}
_FALSE_VALUES = {"0", "false", "f", "no", "n", "off", "disable", "disabled"}


def get_bool_env(name: str, default: Optional[bool] = None) -> Optional[bool]:
    """Return a boolean value for *name* if the environment variable is set.

    Parameters
    ----------
    name:
        The environment variable name to inspect.
    default:
        The value that should be returned when *name* is not set or cannot be
        interpreted as a boolean. When ``None`` the caller can detect that no
        override was provided.
    """
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return default


__all__ = ["get_bool_env"]
