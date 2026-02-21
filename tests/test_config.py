"""Tests for configuration module."""

from google_map_leadgen.config import (
    CSV_FILENAME,
    DEBUG,
    HEADLESS,
    MAX_TABS,
    SAVE_AS_CSV,
    TARGET_LEADS,
)


class TestConfigDefaults:
    def test_target_leads_default(self):
        assert TARGET_LEADS == 25

    def test_max_tabs_default(self):
        assert MAX_TABS == 2

    def test_headless_default(self):
        assert HEADLESS is True

    def test_debug_default(self):
        assert DEBUG is False

    def test_save_as_csv_default(self):
        assert SAVE_AS_CSV is True

    def test_csv_filename_default(self):
        assert CSV_FILENAME == "scraped_data.csv"


class TestConfigFromEnv:
    def test_target_leads_from_env(self, monkeypatch):
        import importlib

        import google_map_leadgen.config as config_module

        monkeypatch.setenv("LEADS", "50")
        importlib.reload(config_module)
        assert config_module.TARGET_LEADS == 50

    def test_max_tabs_from_env(self, monkeypatch):
        import importlib

        import google_map_leadgen.config as config_module

        monkeypatch.setenv("MAX_TAB_ALLOWED", "4")
        importlib.reload(config_module)
        assert config_module.MAX_TABS == 4

    def test_headless_false_from_env(self, monkeypatch):
        import importlib

        import google_map_leadgen.config as config_module

        monkeypatch.setenv("HEADLESS", "false")
        importlib.reload(config_module)
        assert config_module.HEADLESS is False

    def test_debug_true_from_env(self, monkeypatch):
        import importlib

        import google_map_leadgen.config as config_module

        monkeypatch.setenv("DEBUG", "true")
        importlib.reload(config_module)
        assert config_module.DEBUG is True
