from __future__ import annotations

import logging
import math
import os
import random
from pathlib import Path
from typing import Any, Optional

from aqt.qt import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPixmap,
    QTimer,
    Qt,
    QVBoxLayout,
)


logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}

BUNDLED_MESSAGES = [
    "No excuses. Finish your decks first.",
    "Sit down and review your cards.",
    "You can leave after the required decks are done.",
    "Back to work. Decks first, distractions later.",
    "Finish today's cards before you disappear.",
    "Your future self wants those reviews done first.",
]


class InsultPopupDialog(QDialog):
    def __init__(
        self,
        parent: Any,
        message: str,
        image_path: Optional[Path],
        duration_ms: int,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Back To Studying")
        self.setModal(False)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        root = QVBoxLayout(self)
        row = QHBoxLayout()
        root.addLayout(row)
        image_display_width = 0
        image_display_height = 0

        if image_path and image_path.exists():
            image_label = QLabel()
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                scaled = self._scaled_popup_pixmap(pixmap)
                image_display_width = scaled.width()
                image_display_height = scaled.height()
                image_label.setPixmap(scaled)
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                image_label.setFixedSize(image_display_width, image_display_height)
                row.addWidget(image_label)

        text = QLabel(message)
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setMinimumWidth(240)
        row.addWidget(text)

        self.resize(max(650, image_display_width + 310), max(280, image_display_height + 40))
        QTimer.singleShot(duration_ms, self.close)

    def _scaled_popup_pixmap(self, pixmap: QPixmap) -> QPixmap:
        target_width, target_height = 512, 512
        width = max(1, pixmap.width())
        height = max(1, pixmap.height())

        # Scale to cover the square, then center-crop to a strict 512x512 output.
        scale = max(target_width / width, target_height / height)
        scaled_width = max(target_width, int(math.ceil(width * scale)))
        scaled_height = max(target_height, int(math.ceil(height * scale)))

        scaled = self._resize_pixmap_high_quality(pixmap, scaled_width, scaled_height)

        x = max(0, (scaled.width() - target_width) // 2)
        y = max(0, (scaled.height() - target_height) // 2)
        return scaled.copy(x, y, target_width, target_height)

    def _resize_pixmap_high_quality(
        self, pixmap: QPixmap, target_width: int, target_height: int
    ) -> QPixmap:
        current = pixmap
        target_width = max(1, int(target_width))
        target_height = max(1, int(target_height))

        if current.width() == target_width and current.height() == target_height:
            return current

        # Multi-step downscaling reduces softness/artifacts on larger source images.
        while current.width() > target_width * 2 or current.height() > target_height * 2:
            next_width = max(target_width, current.width() // 2)
            next_height = max(target_height, current.height() // 2)
            current = current.scaled(
                next_width,
                next_height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        return current.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )


class PopupManager:
    def __init__(self) -> None:
        self._live_dialogs: list[QDialog] = []
        self._last_message: Optional[str] = None
        self._last_image_path: Optional[str] = None

    def show_warning(self, parent: Any, config: dict[str, Any], addon_dir: str, reason: str = "") -> None:
        message = self._pick_message(config, reason)
        image_path = self._pick_image(addon_dir)
        duration_ms = int(config.get("popup_duration_seconds", 4)) * 1000

        dialog = InsultPopupDialog(parent, message, image_path, duration_ms)
        dialog.finished.connect(lambda _=0, d=dialog: self._drop_dialog(d))
        self._live_dialogs.append(dialog)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _drop_dialog(self, dialog: QDialog) -> None:
        self._live_dialogs = [d for d in self._live_dialogs if d is not dialog]

    def _pick_message(self, config: dict[str, Any], reason: str) -> str:
        # MVP uses bundled messages (not user-configurable).
        _ = config  # kept in signature for compatibility
        base = self._random_non_repeating(BUNDLED_MESSAGES, self._last_message)
        self._last_message = base
        return f"{base}\n\n{reason}".strip() if reason else base

    def _pick_image(self, addon_dir: str) -> Optional[Path]:
        # MVP uses bundled images shipped with the add-on.
        folder = Path(addon_dir) / "assets" / "images"
        if not folder.exists() or not folder.is_dir():
            logger.debug("Popup image folder missing: %s", folder)
            return None

        try:
            candidates = [
                p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            ]
        except OSError as exc:
            logger.warning("Could not read popup image folder %s: %s", folder, exc)
            return None

        if not candidates:
            logger.debug("No popup images found in %s", folder)
            return None

        random.shuffle(candidates)
        if self._last_image_path and len(candidates) > 1:
            candidates.sort(key=lambda p: str(p) == self._last_image_path)

        for candidate in candidates:
            if self._is_loadable_image(candidate):
                self._last_image_path = str(candidate)
                return candidate

        logger.warning("No loadable popup images found in %s (files present but invalid/unreadable).", folder)
        return None

    def _is_loadable_image(self, path: Path) -> bool:
        try:
            pixmap = QPixmap(str(path))
            return not pixmap.isNull()
        except Exception as exc:
            logger.warning("Failed to load popup image %s: %s", path, exc)
            return False

    def _random_non_repeating(self, items: list[str], previous: Optional[str]) -> str:
        if not items:
            return "Finish your required decks first."
        if len(items) == 1:
            return items[0]

        filtered = [item for item in items if item != previous]
        return random.choice(filtered or items)
