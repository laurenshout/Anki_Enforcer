from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

from aqt.qt import (
    QApplication,
    QAction,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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
    QToolButton,
    Qt,
    QVBoxLayout,
)

from ..config import ConfigStore
from ..paths import CONFIG_JSON_PATH, IMAGES_DIR, SCRIPTS_DIR
from ..services.fallback import FallbackController, hash_password
from ..services.progress import ProgressTracker
from .popup import PopupManager

SETTINGS_ACCESS_AUTH_SECONDS = 300


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

        self.setWindowTitle("Anki Enforcer Settings")
        self.resize(700, 560)

        self.enabled_checkbox = QCheckBox("Enable Anki Enforcer")
        self.deck_list = QListWidget()
        self.deck_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.deck_list.setMinimumHeight(240)

        self.popup_duration = QSpinBox()
        self.popup_duration.setRange(1, 15)
        self.popup_duration.setSuffix(" sec")
        self.anki_executable_path = QLineEdit()
        self.anki_executable_path.setPlaceholderText("Path to anki.exe")
        self.browse_anki_path_btn = QPushButton("Browse...")

        self.focus_behavior = QComboBox()
        self.focus_behavior.addItem("Standard focus lock", "warn_only")
        self.focus_behavior.addItem("Aggressive focus lock", "attempt_refocus")

        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password.setPlaceholderText("Set fallback password")
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password.setPlaceholderText("Confirm new fallback password")
        self.password_toggle_btn = QToolButton()
        self.password_toggle_btn.setText("Show")
        self.password_toggle_btn.setCheckable(True)
        self.password_toggle_btn.setToolTip("Show or hide fallback password input")
        self.password_help_btn = QPushButton("Password Help")
        self.password_state_label = QLabel()
        self.password_state_label.setWordWrap(True)
        self.password_change_help_label = QLabel()
        self.password_change_help_label.setWordWrap(True)
        self.assets_info = QLabel("Popup images/messages are bundled with the add-on in MVP.")
        self.assets_info.setWordWrap(True)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.refresh_status_btn = QPushButton("Refresh Status")
        self.autostart_status_label = QLabel()
        self.autostart_status_label.setWordWrap(True)
        self.refresh_autostart_btn = QPushButton("Refresh Auto-Start")
        self.enable_autostart_btn = QPushButton("Enable Auto-Start")
        self.disable_autostart_btn = QPushButton("Disable Auto-Start")

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
        anki_path_row = QHBoxLayout()
        anki_path_row.addWidget(self.anki_executable_path, 1)
        anki_path_row.addWidget(self.browse_anki_path_btn)
        form.addRow("Anki executable path", anki_path_row)
        form.addRow("Popup assets", self.assets_info)
        form.addRow("Focus lock strength", self.focus_behavior)
        password_row = QHBoxLayout()
        password_row.addWidget(self.new_password, 1)
        password_row.addWidget(self.password_toggle_btn)
        password_row.addWidget(self.password_help_btn)
        form.addRow("Fallback password", password_row)
        form.addRow("Confirm password", self.confirm_password)
        form.addRow("Password status", self.password_state_label)
        form.addRow("Password help", self.password_change_help_label)
        form.addRow("Current study status", self.status_label)
        form.addRow("Windows auto-start", self.autostart_status_label)
        root.addLayout(form)

        status_row = QHBoxLayout()
        status_row.addStretch(1)
        status_row.addWidget(self.refresh_status_btn)
        root.addLayout(status_row)

        autostart_row = QHBoxLayout()
        autostart_row.addWidget(self.refresh_autostart_btn)
        autostart_row.addWidget(self.enable_autostart_btn)
        autostart_row.addWidget(self.disable_autostart_btn)
        root.addLayout(autostart_row)

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
        self.refresh_autostart_btn.clicked.connect(self._refresh_autostart_status)
        self.enable_autostart_btn.clicked.connect(self._enable_autostart)
        self.disable_autostart_btn.clicked.connect(self._disable_autostart)
        self.browse_anki_path_btn.clicked.connect(self._browse_anki_path)
        self.deck_list.itemDoubleClicked.connect(self._toggle_deck_item)
        self.password_toggle_btn.toggled.connect(self._toggle_password_visibility)
        self.password_help_btn.clicked.connect(self._show_password_reset_help)

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
        self.anki_executable_path.setText(str(cfg.get("anki_executable_path", "") or ""))
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
        self._refresh_password_state()
        self._refresh_progress_status()
        self.new_password.setText(str(cfg.get("fallback_password_plain", "") or ""))
        self.confirm_password.clear()
        self._refresh_autostart_status()

    def _refresh_bypass_status(self) -> None:
        if self.fallback.is_active():
            self.bypass_status.setText("Active (persistent until disabled)")
            return
        self.bypass_status.setText("Inactive")

    def _refresh_assets_info(self) -> None:
        if IMAGES_DIR.is_dir():
            self.assets_info.setText(f"Bundled assets path: {IMAGES_DIR}")
            return
        self.assets_info.setText(
            "Bundled popup images are missing (`assets/images`). Popup will fall back to text-only mode."
        )

    def _refresh_progress_status(self) -> None:
        cfg = self.config_store.load()
        status = self.progress.get_status(self.mw, cfg)
        state = "Complete" if status.complete else "Incomplete"
        self.status_label.setText(f"{state}: {status.reason}")

    def _autostart_script_path(self) -> str:
        return str(SCRIPTS_DIR / "anki_autostart.ps1")

    def _suggest_anki_path(self) -> str:
        configured = self.anki_executable_path.text().strip()
        if configured:
            return configured

        app = QApplication.instance()
        if app is not None:
            try:
                app_path = app.applicationFilePath()
            except Exception:
                app_path = ""
            if app_path and os.path.isfile(app_path):
                return app_path

        if sys.executable and os.path.isfile(sys.executable):
            return sys.executable

        return ""

    def _run_autostart_action(self, action: str) -> tuple[bool, str]:
        if os.name != "nt":
            return (False, "Windows-only feature.")
        script_path = self._autostart_script_path()
        if not os.path.isfile(script_path):
            return (False, f"Autostart script not found: {script_path}")

        command = [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            script_path,
            "-Action",
            action,
        ]
        anki_path = self.anki_executable_path.text().strip()
        if not anki_path:
            anki_path = self._suggest_anki_path()
        if anki_path:
            command.extend(["-AnkiPath", anki_path])

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except Exception as exc:
            return (False, f"Failed to run autostart script: {exc}")

        output = (result.stdout or "").strip()
        if result.returncode != 0:
            err = (result.stderr or "").strip()
            return (False, err or output or "Autostart command failed.")
        return (True, output)

    def _refresh_autostart_status(self) -> None:
        ok, message = self._run_autostart_action("status")
        if not ok:
            self.autostart_status_label.setText(f"Unavailable: {message}")
            self.enable_autostart_btn.setEnabled(False)
            self.disable_autostart_btn.setEnabled(False)
            return

        enabled = "Autostart enabled: True" in message
        self.autostart_status_label.setText("Enabled" if enabled else "Disabled")
        self.enable_autostart_btn.setEnabled(not enabled)
        self.disable_autostart_btn.setEnabled(enabled)

    def _enable_autostart(self) -> None:
        anki_path = self.anki_executable_path.text().strip()
        if not anki_path:
            QMessageBox.warning(
                self,
                "Windows Auto-Start",
                "Set the Anki executable path first. Use Browse... and select anki.exe.",
            )
            return
        if not os.path.isfile(anki_path):
            QMessageBox.warning(
                self,
                "Windows Auto-Start",
                f"Configured Anki executable path does not exist:\n{anki_path}",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Enable Windows Auto-Start",
            "Enable launching Anki automatically when you log into Windows?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, message = self._run_autostart_action("enable")
        if ok:
            QMessageBox.information(self, "Windows Auto-Start", "Auto-start enabled.")
        else:
            QMessageBox.warning(self, "Windows Auto-Start", message)
        self._refresh_autostart_status()

    def _disable_autostart(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Disable Windows Auto-Start",
            "Disable launching Anki automatically at Windows login?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, message = self._run_autostart_action("disable")
        if ok:
            QMessageBox.information(self, "Windows Auto-Start", "Auto-start disabled.")
        else:
            QMessageBox.warning(self, "Windows Auto-Start", message)
        self._refresh_autostart_status()

    def _refresh_password_state(self) -> None:
        has_password = bool(str(self._config.get("fallback_password_hash", "") or "").strip())
        has_recoverable = bool(str(self._config.get("fallback_password_plain", "") or "").strip())
        if has_password:
            if has_recoverable:
                self.password_state_label.setText(
                    "Configured. Current saved password is loaded in this field."
                )
            else:
                self.password_state_label.setText(
                    "Configured, but previous value is not recoverable. Set a new password to enable display."
                )
            self.new_password.setPlaceholderText("Current fallback password")
            self.confirm_password.setPlaceholderText("Re-enter to confirm change")
            self.password_change_help_label.setText(
                "To change the password, edit the top field, re-enter the new value below, then click Save."
            )
            return
        self.password_state_label.setText("Not configured.")
        self.new_password.setPlaceholderText("Set fallback password")
        self.confirm_password.setPlaceholderText("Confirm new fallback password")
        self.password_change_help_label.setText(
            "Enter the password in both fields, then click Save."
        )

    def _browse_anki_path(self) -> None:
        start_dir = self.anki_executable_path.text().strip()
        if not start_dir:
            start_dir = os.path.dirname(self._suggest_anki_path()) or os.path.expanduser("~")
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select Anki executable",
            start_dir,
            "Executable (anki.exe);;All files (*)",
        )
        if not selected:
            return
        self.anki_executable_path.setText(selected)
        self._refresh_autostart_status()

    def _selected_deck_ids(self) -> list[int]:
        selected: list[int] = []
        for i in range(self.deck_list.count()):
            item = self.deck_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(int(item.data(Qt.ItemDataRole.UserRole)))
        return selected

    def _toggle_deck_item(self, item: QListWidgetItem) -> None:
        if item.checkState() == Qt.CheckState.Checked:
            item.setCheckState(Qt.CheckState.Unchecked)
            return
        item.setCheckState(Qt.CheckState.Checked)

    def _save(self) -> None:
        cfg = self.config_store.load()
        cfg["enabled"] = self.enabled_checkbox.isChecked()
        cfg["required_deck_ids"] = self._selected_deck_ids()
        cfg["popup_duration_seconds"] = self.popup_duration.value()
        cfg["focus_loss_behavior"] = str(self.focus_behavior.currentData())
        cfg["anki_executable_path"] = self.anki_executable_path.text().strip()

        existing_password = str(cfg.get("fallback_password_plain", "") or "")
        new_password = self.new_password.text().strip()
        confirm_password = self.confirm_password.text().strip()

        if not confirm_password and new_password == existing_password:
            self._config = self.config_store.save(cfg)
            self.accept()
            return

        if new_password or confirm_password:
            if len(new_password) < 4:
                QMessageBox.warning(
                    self,
                    "Fallback Password",
                    "Password must be at least 4 characters.",
                )
                return
            if new_password != confirm_password:
                QMessageBox.warning(
                    self,
                    "Fallback Password",
                    "Password fields do not match.",
                )
                return

        if new_password:
            cfg["fallback_password_hash"] = hash_password(new_password)
            cfg["fallback_password_plain"] = new_password

        self._config = self.config_store.save(cfg)
        self.accept()

    def _toggle_password_visibility(self, checked: bool) -> None:
        self.new_password.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self.confirm_password.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self.password_toggle_btn.setText("Hide" if checked else "Show")

    def _show_password_reset_help(self) -> None:
        QMessageBox.information(
            self,
            "Password Help",
            (
                "The field can display the currently saved password when available.\n\n"
                "Notes:\n"
                "1. Existing installs may not have recoverable password text yet.\n"
                "2. Set/save a new password once to make it displayable.\n"
                f"3. Config path: {CONFIG_JSON_PATH}"
            ),
        )

    def _activate_bypass(self) -> None:
        password, ok = QInputDialog.getText(
            self,
            "Activate Fallback Bypass",
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
        self.popup.show_warning(self.mw, cfg, reason)


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

    action = QAction("Anki Enforcer Settings", mw)
    action.triggered.connect(
        lambda: open_settings_dialog(mw, config_store, fallback, popup, progress)
    )
    mw.form.menuTools.addAction(action)
    setattr(mw, action_attr, action)


def open_settings_dialog(
    mw: Any,
    config_store: ConfigStore,
    fallback: FallbackController,
    popup: PopupManager,
    progress: ProgressTracker,
) -> None:
    cfg = config_store.load()
    if _settings_access_requires_password(cfg) and not (
        fallback.is_active() or fallback.has_settings_access_authorization()
    ):
        password, ok = QInputDialog.getText(
            mw,
            "Protected Settings",
            "Enter fallback password to open Anki Enforcer settings",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return

        result = fallback.authorize_settings_access(
            password,
            duration_seconds=SETTINGS_ACCESS_AUTH_SECONDS,
        )
        if not result.ok:
            QMessageBox.warning(mw, "Protected Settings", result.message)
            return
        QMessageBox.information(mw, "Protected Settings", result.message)

    dialog = SettingsDialog(mw, config_store, fallback, popup, progress)
    dialog.exec()


def _settings_access_requires_password(config: dict[str, Any]) -> bool:
    if not bool(config.get("enabled", False)):
        return False
    if not (config.get("required_deck_ids") or []):
        return False
    if not str(config.get("fallback_password_hash", "") or "").strip():
        return False
    return True
