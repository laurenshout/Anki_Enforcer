from __future__ import annotations

from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
ADDON_ROOT = PACKAGE_DIR.parent
ASSETS_DIR = ADDON_ROOT / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
SCRIPTS_DIR = ADDON_ROOT / "scripts"
CONFIG_JSON_PATH = ADDON_ROOT / "config.json"
