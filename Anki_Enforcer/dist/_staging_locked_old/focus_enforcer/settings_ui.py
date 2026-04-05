from __future__ import annotations

import os
from typing import Any

from aqt.qt import (
    QAction,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    Qt,
    QVBoxLayout,
)

from .config import ConfigStore
from .fallback import FallbackController, hash_password
from .popup import PopupManager
from .progress_tracker import ProgressTracker


def _all_decks(mw: Any) -> list[tuple[int, str]]:
    decks = getattr(getattr(mw, "col", None), "decks", None)
    if decks is None:
        return []

    def _row_to_pair(row: Any) -> tuple[int, str] | None:
        if isinstance(row, dict):
            if "id" in row and "name" in row:
                return (int(row["id"]), str(row["name"]))
            return None

        if hasattr(row, "id") and hasattr(row, "name"):
            return (int(row.id), str(row.name))

        if isinstance(row, (list, tuple)) and len(row) >= 2:
            return (int(row[0]), str(row[1]))

        return None

    if hasattr(decks, "all_names_and_ids"):
        rows = decks.all_names_and_ids() or []
        result: list[tuple[int, str]] = []
        for row in rows:
            pair = _row_to_pair(row)
            if pair is not None:
                result.append(pair)
        return sorted(result, key=lambda x: x[1].lower())

    if hasattr(decks, "allNamesAndIds"):
        rows = decks.allNamesAndIds() or []
        result = []
        for row in rows:
            pair = _row_to_pair(row)
            if pair is not None:
                result.append(pair)
        return sorted(result, key=lambda x: x[1].lower())

    return []


class SettingsDialog(QDialog):
    def __init__(
        self,
        mw: Any,
        config_store: ConfigStore,
        fallback: FallbackController,
        popup: PopupManager,
        progress: ProgressTracker,
    ) -> None:
        super().__init__(mw)
        self.mw = mw
        self.config_store = config_store
        self.fallback = fallback
        self.popup = popup
        self.progress = progress
        self._config = self.config_store.load()

        self.setWindowTitle("Focus Enforcement Add-on Settings")
        self.resize(700, 560)

        self.enabled_checkbox = QCheckBox("Enable focus enforcement")
        self.deck_list = QListWidget()
        self.deck_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.deck_list.setMinimumHeight(240)

        self.popup_duration = QSpinBox()
        self.popup_duration.setRange(1, 15)
        self.popup_duration.setSuffix(" sec")

        self.focus_behavior = QComboBox()
        self.focus_behavior.addItem("Warn only on focus loss", "warn_only")
        self.focus_behavior.addItem("Warn and attempt refocus", "attempt_refocus")

        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password.setPlaceholderText("Leave empty to keep current password")
        self.assets_info = QLabel("Popup images/messages are bundled with the add-on in MVP.")
        self.assets_info.setWordWrap(True)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.refresh_status_btn = QPushButton("Refresh Status")

        self.bypass_status = QLabel()
        self.activate_bypass_btn = QPushButton("Activate Fallback Bypass")
        self.deactivate_bypass_btn = QPushButton("Disable Fallback Bypass")
        self.test_popup_btn = QPushButton("Test Popup")

        self._build_ui()
        self._populate_decks()
        self._load_values()
        self._wire_events()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        form = QFormLayout()
        root.addWidget(self.enabled_checkbox)
        form.addRow("Required decks", self.deck_list)
        form.addRow("Popup duration", self.popup_duration)
        form.addRow("Popup assets", self.assets_info)
        form.addRow("Focus-loss behavior", self.focus_behavior)
        form.addRow("Fallback password", self.new_password)
        form.addRow("Current study status", self.status_label)
        root.addLayout(form)

        status_row = QHBoxLayout()
        status_row.addStretch(1)
        status_row.addWidget(self.refresh_status_btn)
        root.addLayout(status_row)

        bypass_row = QHBoxLayout()
        bypass_row.addWidget(QLabel("Fallback bypass"))
        bypass_row.addWidget(self.bypass_status, 1)
        bypass_row.addWidget(self.activate_bypass_btn)
        bypass_row.addWidget(self.deactivate_bypass_btn)
        root.addLayout(bypass_row)

        tools_row = QHBoxLayout()
        tools_row.addStretch(1)
        tools_row.addWidget(self.test_popup_btn)
        root.addLayout(tools_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _wire_events(self) -> None:
        self.activate_bypass_btn.clicked.connect(self._activate_bypass)
        self.deactivate_bypass_btn.clicked.connect(self._deactivate_bypass)
        self.test_popup_btn.clicked.connect(self._test_popup)
        self.refresh_status_btn.clicked.connect(self._refresh_progress_status)

    def _populate_decks(self) -> None:
        self.deck_list.clear()
        for deck_id, name in _all_decks(self.mw):
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, deck_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.deck_list.addItem(item)

    def _load_values(self) -> None:
        cfg = self._config
        self.enabled_checkbox.setChecked(bool(cfg.get("enabled", False)))
        self.popup_duration.setValue(int(cfg.get("popup_duration_seconds", 4)))
        self._refresh_assets_info()

        selected_behavior = str(cfg.get("focus_loss_behavior", "warn_only"))
        index = self.focus_behavior.findData(selected_behavior)
        self.focus_behavior.setCurrentIndex(max(index, 0))

        selected_ids = {int(x) for x in (cfg.get("required_deck_ids") or [])}
        for i in range(self.deck_list.count()):
            item = self.deck_list.item(i)
            deck_id = int(item.data(Qt.ItemDataRole.UserRole))
            item.setCheckState(
                Qt.CheckState.Checked if deck_id in selected_ids else Qt.CheckState.Unchecked
            )

        self._refresh_bypass_status()
        self._refresh_progress_status()

    def _refresh_bypass_status(self) -> None:
        if self.fallback.is_active():
            self.bypass_status.setText("Active (persistent until disabled)")
            return
        self.bypass_status.setText("Inactive")

    def _refresh_assets_info(self) -> None:
        assets_dir = os.path.join(os.path.dirname(__file__), "assets", "images")
        if os.path.isdir(assets_dir):
            self.assets_info.setText(f"Bundled assets path: {assets_dir}")
            return
        self.assets_info.setText(
            "Bundled popup images are missing (`assets/images`). Popup will fall back to text-only mode."
        )

    def _refresh_progress_status(self) -> None:
        cfg = self.config_store.load()
        status = self.progress.get_status(self.mw, cfg)
        state = "Complete" if status.complete else "Incomplete"
        self.status_label.setText(f"{state}: {status.reason}")

    def _selected_deck_ids(self) -> list[int]:
        selected: list[int] = []
        for i in range(self.deck_list.count()):
            item = self.deck_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(int(item.data(Qt.ItemDataRole.UserRole)))
        return selected

    def _save(self) -> None:
        cfg = self.config_store.load()
        cfg["enabled"] = self.enabled_checkbox.isChecked()
        cfg["required_deck_ids"] = self._selected_deck_ids()
        cfg["popup_duration_seconds"] = self.popup_duration.value()
        cfg["focus_loss_behavior"] = str(self.focus_behavior.currentData())

        new_password = self.new_password.text()
        if new_password:
            cfg["fallback_password_hash"] = hash_password(new_password)

        self._config = self.config_store.save(cfg)
        self.accept()

    def _activate_bypass(self) -> None:
        password, ok = QInputDialog.getText(
            self,
            "Activate Session Bypass",
            "Enter fallback password",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return

        result = self.fallback.activate_with_password(password)
        if result.ok:
            self._refresh_bypass_status()
            QMessageBox.information(
                self,
                "Fallback Bypass",
                result.message,
            )
        else:
            QMessageBox.warning(self, "Fallback Bypass", result.message)

    def _deactivate_bypass(self) -> None:
        self.fallback.deactivate()
        self._refresh_bypass_status()
        self._refresh_progress_status()
        QMessageBox.information(self, "Fallback Bypass", "Fallback bypass disabled.")

    def _test_popup(self) -> None:
        cfg = self.config_store.load()
        status = self.progress.get_status(self.mw, cfg)
        reason = f"Test popup. Current status: {status.reason}"
        self.popup.show_warning(self.mw, cfg, os.path.dirname(__file__), reason)


def install_settings_action(
    mw: Any,
    config_store: ConfigStore,
    fallback: FallbackController,
    popup: PopupManager,
    progress: ProgressTracker,
) -> None:
    action_attr = "_focus_enforcement_settings_action"
    if getattr(mw, action_attr, None) is not None:
        return

    action = QAction("Focus Enforcement Settings", mw)

    def _open_settings() -> None:
        dialog = SettingsDialog(mw, config_store, fallback, popup, progress)
        dialog.exec()

    action.triggered.connect(_open_settings)
    mw.form.menuTools.addAction(action)
    setattr(mw, action_attr, action)
