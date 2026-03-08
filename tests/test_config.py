"""Tests for work_tracker.config."""

from pathlib import Path

from work_tracker.config import (
    load_config,
    save_config,
    config_path,
    config_dir,
    _deep_merge,
    _deep_copy_dict,
    DEFAULTS,
)


class TestXDGPaths:
    def test_config_dir_uses_xdg(self, tmp_config_dir):
        assert str(config_dir()).startswith(str(tmp_config_dir / "config"))


class TestLoadConfig:
    def test_defaults_without_config_file(self, tmp_config_dir):
        cfg = load_config()
        assert cfg["default_category"] == "other"
        assert cfg["reminder"]["interval_minutes"] == 90
        assert cfg["reminder"]["enabled"] is False

    def test_database_url_populated(self, tmp_config_dir):
        cfg = load_config()
        assert cfg["database_url"] != ""

    def test_loads_user_overrides(self, tmp_config_dir):
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('default_category = "dev"\n')
        cfg = load_config()
        assert cfg["default_category"] == "dev"


class TestSaveConfig:
    def test_roundtrip(self, tmp_config_dir):
        cfg = load_config()
        cfg["default_category"] = "meeting"
        save_config(cfg)

        cfg2 = load_config()
        assert cfg2["default_category"] == "meeting"

    def test_creates_config_dir(self, tmp_config_dir):
        cfg = load_config()
        save_config(cfg)
        assert config_path().exists()


class TestDeepMerge:
    def test_shallow_override(self):
        base = {"a": 1, "b": 2}
        _deep_merge(base, {"b": 3})
        assert base == {"a": 1, "b": 3}

    def test_nested_merge(self):
        base = {"x": {"a": 1, "b": 2}}
        _deep_merge(base, {"x": {"b": 3}})
        assert base == {"x": {"a": 1, "b": 3}}

    def test_new_keys(self):
        base = {"a": 1}
        _deep_merge(base, {"b": 2})
        assert base == {"a": 1, "b": 2}


class TestDeepCopy:
    def test_independent_copy(self):
        original = {"a": {"b": 1}}
        copy = _deep_copy_dict(original)
        copy["a"]["b"] = 99
        assert original["a"]["b"] == 1
