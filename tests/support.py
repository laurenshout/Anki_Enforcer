from __future__ import annotations

import sys
import types
from copy import deepcopy
from types import SimpleNamespace


class DummySignal:
    def __init__(self) -> None:
        self._callbacks: list[object] = []

    def connect(self, callback: object) -> None:
        self._callbacks.append(callback)


class DummyQObject:
    def __init__(self, parent: object | None = None, *args: object, **kwargs: object) -> None:
        self._parent = parent

    def parentWidget(self) -> object | None:
        return self._parent


class DummyWidget(DummyQObject):
    def __getattr__(self, _name: str):
        def _noop(*_args: object, **_kwargs: object) -> None:
            return None

        return _noop


class DummyAction(DummyWidget):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.triggered = DummySignal()


class DummyPixmap:
    def __init__(self, _path: str = "") -> None:
        self._width = 512
        self._height = 512
        self._is_null = False

    def isNull(self) -> bool:
        return self._is_null

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height

    def scaled(self, width: int, height: int, *_args: object, **_kwargs: object) -> "DummyPixmap":
        scaled = DummyPixmap()
        scaled._width = width
        scaled._height = height
        scaled._is_null = self._is_null
        return scaled

    def copy(self, _x: int, _y: int, width: int, height: int) -> "DummyPixmap":
        copied = DummyPixmap()
        copied._width = width
        copied._height = height
        copied._is_null = self._is_null
        return copied


class DummyTimer:
    calls: list[tuple[int, object]] = []
    auto_run = False

    @classmethod
    def reset(cls) -> None:
        cls.calls = []
        cls.auto_run = False

    @classmethod
    def singleShot(cls, delay_ms: int, callback: object) -> None:
        cls.calls.append((delay_ms, callback))
        if cls.auto_run and callable(callback):
            callback()


class DummyApplication:
    _instance: object | None = None

    @classmethod
    def instance(cls) -> object | None:
        return cls._instance


class DummyEvent:
    class Type:
        Close = 1
        WindowStateChange = 2
        WindowDeactivate = 3
        Resize = 4
        Move = 5


class FakeAddonManager:
    def __init__(self, configs: dict[str, dict[str, object]] | None = None) -> None:
        self._configs = deepcopy(configs or {})
        self.writes: list[tuple[str, dict[str, object]]] = []

    def getConfig(self, key: str) -> dict[str, object]:
        return deepcopy(self._configs.get(key, {}))

    def writeConfig(self, key: str, value: dict[str, object]) -> None:
        self._configs[key] = deepcopy(value)
        self.writes.append((key, deepcopy(value)))


fake_mw = SimpleNamespace(addonManager=FakeAddonManager())
fake_gui_hooks = SimpleNamespace(
    profile_did_open=[],
    webview_will_set_content=[],
    webview_did_receive_js_message=[],
)

fake_qt = types.ModuleType("aqt.qt")
fake_qt.QApplication = DummyApplication
fake_qt.QAction = DummyAction
fake_qt.QCheckBox = DummyWidget
fake_qt.QComboBox = DummyWidget
fake_qt.QDialog = DummyWidget
fake_qt.QDialogButtonBox = type(
    "QDialogButtonBox",
    (DummyWidget,),
    {"StandardButton": SimpleNamespace(Save=1, Cancel=2)},
)
fake_qt.QEvent = DummyEvent
fake_qt.QFileDialog = DummyWidget
fake_qt.QFormLayout = DummyWidget
fake_qt.QHBoxLayout = DummyWidget
fake_qt.QInputDialog = DummyWidget
fake_qt.QLabel = DummyWidget
fake_qt.QLineEdit = type(
    "QLineEdit",
    (DummyWidget,),
    {"EchoMode": SimpleNamespace(Password=1, Normal=0)},
)
fake_qt.QListWidget = type(
    "QListWidget",
    (DummyWidget,),
    {"SelectionMode": SimpleNamespace(NoSelection=0)},
)
fake_qt.QListWidgetItem = DummyWidget
fake_qt.QMessageBox = type(
    "QMessageBox",
    (DummyWidget,),
    {"StandardButton": SimpleNamespace(Yes=1)},
)
fake_qt.QObject = DummyQObject
fake_qt.QPixmap = DummyPixmap
fake_qt.QPushButton = DummyWidget
fake_qt.QSpinBox = DummyWidget
fake_qt.QTimer = DummyTimer
fake_qt.QToolButton = DummyWidget
fake_qt.QVBoxLayout = DummyWidget
fake_qt.QWidget = DummyWidget
fake_qt.Qt = SimpleNamespace(
    WindowState=SimpleNamespace(WindowNoState=0, WindowMinimized=1, WindowMaximized=2, WindowFullScreen=4),
    ApplicationState=SimpleNamespace(ApplicationActive=1),
    WindowType=SimpleNamespace(Tool=1, WindowStaysOnTopHint=2),
    AlignmentFlag=SimpleNamespace(AlignCenter=0),
    AspectRatioMode=SimpleNamespace(IgnoreAspectRatio=0),
    TransformationMode=SimpleNamespace(SmoothTransformation=0),
    ItemDataRole=SimpleNamespace(UserRole=0),
    ItemFlag=SimpleNamespace(ItemIsUserCheckable=1),
    CheckState=SimpleNamespace(Unchecked=0, Checked=2),
)

fake_aqt = types.ModuleType("aqt")
fake_aqt.mw = fake_mw
fake_aqt.gui_hooks = fake_gui_hooks
fake_aqt.qt = fake_qt

sys.modules.setdefault("aqt", fake_aqt)
sys.modules.setdefault("aqt.qt", fake_qt)


def reset_fake_addon_manager(configs: dict[str, dict[str, object]] | None = None) -> FakeAddonManager:
    fake_mw.addonManager = FakeAddonManager(configs)
    return fake_mw.addonManager


def reset_fake_gui_hooks() -> None:
    fake_gui_hooks.profile_did_open = []
    fake_gui_hooks.webview_will_set_content = []
    fake_gui_hooks.webview_did_receive_js_message = []


def reset_fake_qapplication() -> None:
    DummyApplication._instance = None


def reset_fake_qtimer() -> None:
    DummyTimer.reset()


class MemoryConfigStore:
    def __init__(self, initial: dict[str, object] | None = None) -> None:
        self._config = deepcopy(initial or {})

    def load(self) -> dict[str, object]:
        return deepcopy(self._config)

    def save(self, config: dict[str, object]) -> dict[str, object]:
        self._config = deepcopy(config)
        return deepcopy(self._config)


class RecordingPopup:
    def __init__(self) -> None:
        self.calls: list[tuple[object, dict[str, object], str]] = []

    def show_warning(self, parent: object, config: dict[str, object], reason: str = "") -> None:
        self.calls.append((parent, deepcopy(config), reason))


class StaticFallback:
    def __init__(self, active: bool = False) -> None:
        self._active = active

    def is_active(self) -> bool:
        return self._active


class StaticProgress:
    def __init__(self, complete: bool, reason: str = "status") -> None:
        self.complete = complete
        self.reason = reason

    def get_status(self, _mw: object, _config: dict[str, object]) -> SimpleNamespace:
        return SimpleNamespace(complete=self.complete, reason=self.reason)


class FakeMainWindow(DummyWidget):
    def __init__(self) -> None:
        super().__init__(None)
        self._window_state = 0
        self.event_filters: list[object] = []
        self.raise_calls = 0
        self.activate_calls = 0
        self.show_normal_calls = 0
        self.show_maximized_calls = 0
        self.show_full_screen_calls = 0
        self.show_calls = 0
        self.window_flags: dict[object, bool] = {}

    def installEventFilter(self, event_filter: object) -> None:
        self.event_filters.append(event_filter)

    def windowState(self) -> int:
        return self._window_state

    def setWindowState(self, state: int) -> None:
        self._window_state = state

    def showNormal(self) -> None:
        self.show_normal_calls += 1
        self._window_state = 0

    def showMaximized(self) -> None:
        self.show_maximized_calls += 1
        self._window_state = fake_qt.Qt.WindowState.WindowMaximized

    def showFullScreen(self) -> None:
        self.show_full_screen_calls += 1
        self._window_state = fake_qt.Qt.WindowState.WindowFullScreen

    def show(self) -> None:
        self.show_calls += 1

    def isMaximized(self) -> bool:
        return bool(self._window_state & fake_qt.Qt.WindowState.WindowMaximized)

    def isFullScreen(self) -> bool:
        return bool(self._window_state & fake_qt.Qt.WindowState.WindowFullScreen)

    def setWindowFlag(self, flag: object, enabled: bool = True) -> None:
        self.window_flags[flag] = enabled

    def raise_(self) -> None:
        self.raise_calls += 1

    def activateWindow(self) -> None:
        self.activate_calls += 1


class FakeWindowEvent:
    def __init__(self, event_type: int, old_state: int = 0) -> None:
        self._type = event_type
        self._old_state = old_state
        self.ignored = False

    def type(self) -> int:
        return self._type

    def ignore(self) -> None:
        self.ignored = True

    def oldState(self) -> int:
        return self._old_state
