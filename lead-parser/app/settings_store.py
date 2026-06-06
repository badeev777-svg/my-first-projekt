"""Persistent filter settings stored in data/filter_settings.json.

On first run, defaults come from env vars (config.py).
After the user saves from the /settings UI, the JSON file takes precedence.
"""
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

SETTINGS_FILE = Path(__file__).parent.parent / "data" / "filter_settings.json"


def _env_defaults() -> dict:
    from app.config import KEYWORDS, MIN_BUDGET, VK_GROUPS
    return {
        "keywords": list(KEYWORDS),
        "stack": [],
        "min_budget": MIN_BUDGET,
        "max_budget": 0,
        "vk_groups": list(VK_GROUPS),
    }


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            defaults = _env_defaults()
            # fill any missing keys from env defaults
            for k, v in defaults.items():
                data.setdefault(k, v)
            return data
        except Exception as e:
            log.warning(f"Could not read filter_settings.json: {e}")
    return _env_defaults()


def save_settings(settings: dict) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    log.info("Filter settings saved")
