"""Tests for work_tracker.config."""

from pathlib import Path

from work_tracker.config import (
    load_config,
    save_config,
    config_path,
    config_dir,
    data_dir,
    default_db_path,
    _deep_merge,
    _deep_copy_dict,
    DEFAULTS,
)


class TestXDGPaths:
    def test_config_dir_uses_xdg(self, tmp_config_dir):
        assert str(config_dir()).startswith(str(tmp_config_dir / "config"))

    def test_data_dir_uses_xdg(self, tmp_config_dir):
        assert str(data_dir()).startswith(str(tmp_config_dir / "data"))

    def test_db_path_under_data_dir(self, tmp_config_dir):
        assert str(default_db_path()).endswith("work-tracker.db")
        assert "work-tracker" in str(default_db_path())


class TestLoadConfig:
    def test_defaults_without_config_file(self, tmp_config_dir):
        cfg = load_config()
        assert cfg["default_category"] == "other"
        assert cfg["ai"]["enabled"] is True
        assert cfg["ai"]["model"] == "claude-sonnet-4-20250514"
        assert cfg["reminder"]["interval_minutes"] == 90
        assert cfg["reminder"]["enabled"] is False
        assert cfg["db_path"] != ""

    def test_loads_user_overrides(self, tmp_config_dir):
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('default_category = "dev"\n\n[ai]\nmodel = "custom-model"\n')
        cfg = load_config()
        assert cfg["default_category"] == "dev"
        assert cfg["ai"]["model"] == "custom-model"
        assert cfg["ai"]["enabled"] is True  # default preserved

    def test_db_path_populated(self, tmp_config_dir):
        cfg = load_config()
        assert "work-tracker.db" in cfg["db_path"]


class TestSaveConfig:
    def test_roundtrip(self, tmp_config_dir):
        cfg = load_config()
        cfg["default_category"] = "meeting"
        cfg["ai"]["model"] = "test-model"
        save_config(cfg)

        cfg2 = load_config()
        assert cfg2["default_category"] == "meeting"
        assert cfg2["ai"]["model"] == "test-model"

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
