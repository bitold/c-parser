from __future__ import annotations

import os


def parse_optional_path_env(name: str, *, default: str) -> str | None:
    """Return env var value if it is set, otherwise return default."""
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip()
    return None if not value or value.lower() in {"0", "false", "off", "none"} else value


def require_env(name: str) -> str:
    """Raise RuntimeError if env var is not set."""
    raw = os.getenv(name)
    value = (raw or "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


__all__ = [
    "parse_optional_path_env",
    "require_env",
]
