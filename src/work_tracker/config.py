"""XDG-compliant configuration loading for work-tracker."""

from __future__ import annotations

import os
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


DEFAULTS = {
    "db_path": "",  # filled dynamically from XDG_DATA_HOME
    "default_category": "other",
    "ai": {
        "model": "claude-sonnet-4-20250514",
        "enabled": True,
    },
    "reminder": {
        "interval_minutes": 90,
        "enabled": False,
    },
}


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def config_dir() -> Path:
    return _xdg_config_home() / "work-tracker"


def config_path() -> Path:
    return config_dir() / "config.toml"


def data_dir() -> Path:
    return _xdg_data_home() / "work-tracker"


def default_db_path() -> Path:
    return data_dir() / "work-tracker.db"


def load_config() -> dict:
    """Load config from TOML file, merged with defaults."""
    cfg = _deep_copy_dict(DEFAULTS)
    cfg["db_path"] = str(default_db_path())

    path = config_path()
    if path.exists():
        with open(path, "rb") as f:
            user_cfg = tomllib.load(f)
        _deep_merge(cfg, user_cfg)

    return cfg


def save_config(cfg: dict) -> None:
    """Write config dict as TOML to the config file."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        _write_toml(f, cfg)


def _deep_copy_dict(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        out[k] = _deep_copy_dict(v) if isinstance(v, dict) else v
    return out


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def _write_toml(f, d: dict, prefix: str = "") -> None:
    """Minimal TOML writer sufficient for our flat-ish config."""
    tables = []
    for k, v in d.items():
        if isinstance(v, dict):
            tables.append((k, v))
        elif isinstance(v, bool):
            f.write(f"{k} = {str(v).lower()}\n")
        elif isinstance(v, int):
            f.write(f"{k} = {v}\n")
        else:
            f.write(f'{k} = "{v}"\n')

    for k, v in tables:
        section = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        f.write(f"\n[{section}]\n")
        _write_toml(f, v, section)
