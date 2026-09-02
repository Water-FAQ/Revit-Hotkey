"""PySide6 user interface for Revit Hotkey."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import (
    QAbstractTableModel,
    QItemSelection,
    QModelIndex,
    QPoint,
    QSettings,
    QSize,
    QSortFilterProxyModel,
    QStandardPaths,
    Qt,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QKeyEvent,
    QPainter,
    QPalette,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QProxyStyle,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .keymap import (
    IGNORED_VKS,
    VK_BACK,
    VK_CONTROL,
    VK_ESCAPE,
    VK_MENU,
    VK_SHIFT,
    convert_combination,
    key_pair_from_vk,
    make_modified_pair,
)
from .model import (
    CommandRecord,
    ShortcutDocument,
    ShortcutXmlError,
    discover_revit_files,
    revit_version_for_path,
)

APP_NAME = "Revit Hotkey"
PROJECT_ISSUES_URL = "https://github.com/Water-FAQ/Revit-Hotkey/issues"
INVALID_INDEX = QModelIndex()

COLORS = {
    "background": "#F4F7FB",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFD",
    "text": "#202B3C",
    "muted": "#6E7B8D",
    "border": "#D8E0EA",
    "blue": "#1672E8",
    "blue_hover": "#0D63D4",
    "blue_soft": "#EAF3FF",
    "green": "#198754",
    "green_soft": "#EAF7F0",
    "red": "#C93F45",
    "red_soft": "#FCEDEF",
    "orange": "#B76A00",
    "disabled": "#A9B3C0",
    "locked": "#F0F2F5",
}


def resource_path(name: str) -> Path:
    return Path(__file__).resolve().parent / "resources" / name


def apply_windows_frame_colors(widget: QWidget) -> None:
    """Keep the native Windows frame light and neutral when DWM supports it."""
    if os.name != "nt":
        return
    try:
        import ctypes

        def colorref(value: str) -> int:
            color = QColor(value)
            return color.red() | (color.green() << 8) | (color.blue() << 16)

        hwnd = ctypes.c_void_p(int(widget.winId()))
        dwm = ctypes.windll.dwmapi
        for attribute, value in (
            (34, colorref("#C7D0DC")),
            (35, colorref(COLORS["background"])),
            (36, colorref(COLORS["text"])),
        ):
            data = ctypes.c_uint(value)
            dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data))
    except (AttributeError, OSError, ValueError):
        pass


def stylesheet() -> str:
    c = COLORS
    return f"""
    QMainWindow, QWidget#central {{ background: {c['background']}; color: {c['text']}; }}
    QWidget {{ font-family: "Segoe UI"; font-size: 10pt; color: {c['text']}; }}
    QLabel#appTitle {{ color: {c['blue']}; font-size: 16pt; font-weight: 700; }}
    QLabel#sectionTitle {{ color: {c['blue']}; font-size: 11pt; font-weight: 650; }}
    QLabel#muted {{ color: {c['muted']}; }}
    QLabel#footer {{ color: {c['muted']}; font-size: 9pt; }}
    QFrame#card {{
        background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 12px;
    }}
    QPushButton {{
        min-height: 36px; padding: 0 14px; background: #E5EBF4;
        border: none; border-radius: 8px; font-weight: 600;
    }}
    QPushButton:hover {{ color: {c['text']}; background: #D8E3F1; }}
    QPushButton:pressed {{ background: #C9D7E8; }}
    QPushButton:disabled {{ color: {c['disabled']}; background: #EEF1F5; }}
    QPushButton#primary {{ background: {c['blue']}; color: white; }}
    QPushButton#primary:hover {{ background: {c['blue_hover']}; color: white; }}
    QPushButton#danger {{ background: #EA3E50; color: white; }}
    QPushButton#danger:hover {{ background: #D93446; color: white; }}
    QPushButton#success {{ background: #198754; color: white; }}
    QPushButton#success:hover {{ background: #157347; color: white; }}
    QLineEdit, QComboBox {{
        min-height: 34px; padding: 0 10px; background: {c['surface']};
        border: 1px solid {c['border']}; border-radius: 8px; selection-background-color: {c['blue']};
    }}
    QLineEdit:focus, QComboBox:focus {{ border: 1px solid {c['blue']}; }}
    QLineEdit:disabled, QComboBox:disabled {{ color: {c['disabled']}; background: #F1F3F6; }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox QAbstractItemView {{
        background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']};
        selection-background-color: #DCEBFF; selection-color: {c['text']};
        outline: none; padding: 3px;
    }}
    QTableView {{
        background: {c['surface']}; alternate-background-color: {c['surface_alt']};
        border: 1px solid {c['border']}; border-radius: 9px; gridline-color: #E5EAF0;
        selection-background-color: #DCEBFF; selection-color: {c['text']};
    }}
    QTableView::item {{ padding: 7px 8px; border: none; }}
    QHeaderView::section {{
        background: #EDF2F8; color: #344256; border: none; border-right: 1px solid {c['border']};
        border-bottom: 1px solid {c['border']}; padding: 8px; font-weight: 650;
    }}
    QCheckBox {{ spacing: 9px; }}
    QCheckBox::indicator {{ width: 38px; height: 20px; border-radius: 10px; background: #BCC6D2; }}
    QCheckBox::indicator:checked {{ background: {c['blue']}; }}
    QCheckBox::indicator:disabled {{ background: #D8DEE6; }}
    QScrollBar:vertical {{
        background: #F1F4F8; width: 10px; margin: 0; border: none;
    }}
    QScrollBar::handle:vertical {{
        background: #B8C5D6; min-height: 30px; border-radius: 5px; margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{ background: #8FA3BC; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QScrollBar:horizontal {{
        background: #F1F4F8; height: 10px; margin: 0; border: none;
    }}
    QScrollBar::handle:horizontal {{
        background: #B8C5D6; min-width: 30px; border-radius: 5px; margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: #8FA3BC; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; border: none; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
    QToolTip {{
        background: #F8FAFD; color: {c['text']}; border: 1px solid #C8D2DF;
        border-radius: 4px; padding: 4px 7px;
    }}
    QMenu {{ background: {c['surface']}; border: 1px solid {c['border']}; padding: 5px; }}
    QMenu::item {{ padding: 7px 28px 7px 12px; border-radius: 5px; }}
    QMenu::item:selected {{ background: {c['blue_soft']}; color: {c['blue']}; }}
    """


class KeyCaptureLineEdit(QLineEdit):
    pair_captured = Signal(str, str)
    pair_cleared = Signal()
    capture_cancelled = Signal()
    capture_message = Signal(str, str)

    def __init__(self, language: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.language = language
        self._pending = []
        self._waiting_modifier = False
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPlaceholderText("Нажмите две клавиши")
        self.setToolTip(
            "Комбинация для английской раскладки"
            if language == "en"
            else "Комбинация для русской раскладки"
        )

    def reset_capture(self) -> None:
        self._pending.clear()
        self._waiting_modifier = False

    def focusOutEvent(self, event) -> None:
        unfinished = bool(self._pending or self._waiting_modifier)
        self.reset_capture()
        if unfinished:
            self.capture_cancelled.emit()
        super().focusOutEvent(event)

    def _vk(self, event: QKeyEvent) -> int:
        native = int(event.nativeVirtualKey())
        return native or int(event.key())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            event.accept()
            return
        vk = self._vk(event)
        if vk == VK_ESCAPE:
            self.reset_capture()
            self.capture_cancelled.emit()
            self.capture_message.emit("Ввод комбинации клавиш отменён.", "info")
            event.accept()
            return
        if vk == VK_BACK:
            self.reset_capture()
            self.pair_cleared.emit()
            event.accept()
            return

        modifiers = event.modifiers()
        ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        alt = bool(modifiers & Qt.KeyboardModifier.AltModifier)

        if vk in (VK_CONTROL, VK_SHIFT):
            self._waiting_modifier = True
            self.setText("Ctrl+…" if vk == VK_CONTROL else "Shift+…")
            event.accept()
            return
        if alt or vk == VK_MENU or vk in IGNORED_VKS:
            self.capture_message.emit("Эта клавиша недоступна для назначения.", "warning")
            event.accept()
            return
        if ctrl and shift:
            self.capture_message.emit(
                "Комбинация из Ctrl, Shift и третьей клавиши недопустима.", "warning"
            )
            event.accept()
            return

        pair = key_pair_from_vk(vk)
        if pair is None:
            self.capture_message.emit("Эта клавиша недоступна для назначения.", "warning")
            event.accept()
            return

        if ctrl or shift:
            result = make_modified_pair("ctrl" if ctrl else "shift", pair)
            self.reset_capture()
            self.pair_captured.emit(result.english, result.russian)
            event.accept()
            return

        self._pending.append(pair)
        english = "".join(value.english for value in self._pending)
        russian = "".join(value.russian for value in self._pending)
        self.setText(english if self.language == "en" else russian)
        if len(self._pending) == 1:
            self.capture_message.emit("Введите вторую клавишу.", "info")
        else:
            self.reset_capture()
            self.pair_captured.emit(english, russian)
        event.accept()


class CommandTableModel(QAbstractTableModel):
    HEADERS = ("Команда", "Горячие клавиши", "Пути")

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.records: list[CommandRecord] = []

    def set_records(self, records: list[CommandRecord]) -> None:
        self.beginResetModel()
        self.records = records
        self.endResetModel()

    def refresh(self) -> None:
        if self.records:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self.records) - 1, len(self.HEADERS) - 1),
                [],
            )

    def rowCount(self, parent: QModelIndex = INVALID_INDEX) -> int:
        return 0 if parent.isValid() else len(self.records)

    def columnCount(self, parent: QModelIndex = INVALID_INDEX) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        record = self.records[index.row()]
        values = (record.name, record.display_shortcuts, record.paths)
        if role == Qt.ItemDataRole.DisplayRole:
            return values[index.column()]
        if role == Qt.ItemDataRole.ToolTipRole:
            if record.locked and index.column() == 1:
                return "Системная комбинация клавиш Revit. Изменение недоступно."
            return values[index.column()] or "Нет данных"
        if role == Qt.ItemDataRole.UserRole:
            return record
        if role == Qt.ItemDataRole.ForegroundRole and record.locked:
            return QColor(COLORS["muted"])
        if role == Qt.ItemDataRole.BackgroundRole:
            if record.changed:
                return QColor(COLORS["blue_soft"])
            if record.locked:
                return QColor(COLORS["locked"])
        if role == Qt.ItemDataRole.FontRole and record.changed:
            font = QFont()
            font.setBold(True)
            return font
        if role == Qt.ItemDataRole.TextAlignmentRole and index.column() == 1:
            return int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        return None


class CommandFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.search_text = ""
        self.category = "Все"
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_search_text(self, text: str) -> None:
        self.search_text = text.strip().casefold()
        self.invalidateFilter()

    def set_category(self, category: str) -> None:
        self.category = category
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if not isinstance(model, CommandTableModel):
            return True
        record = model.records[source_row]
        if self.search_text and self.search_text not in record.name.casefold():
            return False
        if self.category == "Все":
            return True
        if self.category == "Все заданные":
            return record.assigned
        if self.category == "Все незаданные":
            return not record.assigned
        if self.category == "Без категории":
            return not record.categories
        return self.category in record.categories

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        lv = str(self.sourceModel().data(left, Qt.ItemDataRole.DisplayRole) or "")
        rv = str(self.sourceModel().data(right, Qt.ItemDataRole.DisplayRole) or "")
        return lv.casefold() < rv.casefold()


class ComboPopupStyle(QProxyStyle):
    """Disable the Windows full-height native combo-box popup."""

    def styleHint(self, hint, option=None, widget=None, return_data=None) -> int:
        if hint == QStyle.StyleHint.SH_ComboBox_Popup:
            return 0
        return super().styleHint(hint, option, widget, return_data)


class DownwardComboBox(QComboBox):
    """A ten-row popup anchored directly below the combo box."""

    VISIBLE_ITEMS = 10

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMaxVisibleItems(self.VISIBLE_ITEMS)
        self._popup_style = ComboPopupStyle()
        self._popup_style.setParent(self)
        self.setStyle(self._popup_style)
        self.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view().setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view().setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerItem)

    def showPopup(self) -> None:
        super().showPopup()
        view = self.view()
        popup = view.window()
        visible_rows = min(self.count(), self.VISIBLE_ITEMS)
        if visible_rows <= 0:
            return

        row_height = view.sizeHintForRow(0)
        if row_height <= 0:
            row_height = self.fontMetrics().height() + 10
        frame = max(1, view.frameWidth())
        popup_height = row_height * visible_rows + frame * 2 + 2
        popup_position = self.mapToGlobal(QPoint(0, self.height()))
        popup.setGeometry(
            popup_position.x(),
            popup_position.y(),
            self.width(),
            popup_height,
        )


class ExactElideDelegate(QStyledItemDelegate):
    """Elide table text only at the real visible edge of its column."""

    HORIZONTAL_PADDING = 8

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        text = (
            view_option.text.replace("\r", " ")
            .replace("\n", " ")
            .replace("\u2028", " ")
            .replace("\u2029", " ")
        )

        # Draw the background ourselves so the platform style cannot render a
        # second, wrapped copy of the model text.
        selected = bool(view_option.state & QStyle.StateFlag.State_Selected)
        if selected:
            background = view_option.palette.brush(QPalette.ColorRole.Highlight)
        elif view_option.backgroundBrush.style() != Qt.BrushStyle.NoBrush:
            background = view_option.backgroundBrush
        elif index.row() % 2:
            background = QColor(COLORS["surface_alt"])
        else:
            background = QColor(COLORS["surface"])
        painter.fillRect(option.rect, background)

        text_rect = option.rect.adjusted(
            self.HORIZONTAL_PADDING,
            0,
            -self.HORIZONTAL_PADDING,
            0,
        )
        if text_rect.width() <= 0 or not text:
            return

        painter.save()
        painter.setClipRect(text_rect)
        painter.setFont(view_option.font)
        role = (
            QPalette.ColorRole.HighlightedText
            if selected
            else QPalette.ColorRole.Text
        )
        painter.setPen(view_option.palette.color(role))
        visible_text = view_option.fontMetrics.elidedText(
            text,
            Qt.TextElideMode.ElideRight,
            text_rect.width(),
        )
        horizontal = (
            Qt.AlignmentFlag.AlignHCenter
            if index.column() == 1
            else Qt.AlignmentFlag.AlignLeft
        )
        text_width = view_option.fontMetrics.horizontalAdvance(visible_text)
        x = text_rect.left()
        if horizontal == Qt.AlignmentFlag.AlignHCenter:
            x += max(0, (text_rect.width() - text_width) // 2)
        baseline = (
            text_rect.top()
            + max(0, (text_rect.height() - view_option.fontMetrics.height()) // 2)
            + view_option.fontMetrics.ascent()
        )
        painter.drawText(x, baseline, visible_text)
        painter.restore()


class ClickableLabel(QLabel):
    clicked = Signal()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ToggleSwitch(QCheckBox):
    """Compact checkbox rendered as a familiar slider switch."""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setMinimumHeight(26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(self.sizeHint().width())

    def sizeHint(self) -> QSize:
        width = 50 + self.fontMetrics().horizontalAdvance(self.text()) + 8
        return QSize(width, 26)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track_x, track_y, track_w, track_h = 0, 3, 40, 20
        if not self.isEnabled():
            track = QColor("#D8DEE6")
        elif self.isChecked():
            track = QColor(COLORS["blue"])
        else:
            track = QColor("#B8C3D0")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(track_x, track_y, track_w, track_h, 10, 10)
        knob_x = 22 if self.isChecked() else 3
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(knob_x, 6, 14, 14)
        painter.setPen(QColor(COLORS["text"] if self.isEnabled() else COLORS["disabled"]))
        painter.drawText(
            50,
            0,
            max(0, self.width() - 50),
            26,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.text(),
        )


class StyledMessageDialog(QDialog):
    """Light, application-styled dialog independent of the Windows color theme."""

    def __init__(
        self,
        title: str,
        text: str,
        icon: str,
        buttons: list[tuple[str, str]],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.clicked_label = ""
        self._drag_position: QPoint | None = None
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(str(resource_path("icon.png"))))
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(520)

        frame = QFrame(objectName="messageFrame")
        frame.setStyleSheet(
            f"""
            QFrame#messageFrame {{
                background: {COLORS['surface']}; border: 1px solid #C7D0DC;
                border-radius: 9px;
            }}
            QLabel {{ border: none; background: transparent; }}
            QLabel#dialogTitle {{ color: {COLORS['text']}; font-weight: 600; }}
            QPushButton#dialogClose {{
                min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px;
                padding: 0; border-radius: 6px; background: transparent;
                color: {COLORS['muted']}; font-size: 14pt; font-weight: 400;
            }}
            QPushButton#dialogClose:hover {{ background: #E8EDF4; color: {COLORS['text']}; }}
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.addWidget(frame)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 10, 16, 16)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        app_icon = QLabel()
        app_icon.setPixmap(QIcon(str(resource_path("icon.png"))).pixmap(18, 18))
        title_label = QLabel(title, objectName="dialogTitle")
        close_button = QPushButton("×", objectName="dialogClose")
        close_button.setToolTip("Закрыть")
        close_button.clicked.connect(self.reject)
        title_row.addWidget(app_icon)
        title_row.addWidget(title_label, 1)
        title_row.addWidget(close_button)
        layout.addLayout(title_row)

        content_row = QHBoxLayout()
        content_row.setSpacing(14)
        symbols = {
            "warning": ("!", COLORS["orange"], "#FFF4DE"),
            "error": ("!", COLORS["red"], COLORS["red_soft"]),
            "question": ("?", COLORS["blue"], COLORS["blue_soft"]),
        }
        symbol, color, background = symbols.get(icon, ("i", COLORS["blue"], COLORS["blue_soft"]))
        icon_label = QLabel(symbol)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(30, 30)
        icon_label.setStyleSheet(
            f"background: {background}; color: {color}; border: 1px solid {color}; "
            "border-radius: 15px; font-size: 13pt; font-weight: 700;"
        )
        message = QLabel(text)
        message.setWordWrap(True)
        message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content_row.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
        content_row.addWidget(message, 1)
        layout.addLayout(content_row)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        for label, role in buttons:
            button = QPushButton(label)
            if role == "accept":
                button.setObjectName("primary")
            elif role == "destructive":
                button.setObjectName("danger")
            button.clicked.connect(lambda checked=False, value=label: self._finish(value))
            button_row.addWidget(button)
        layout.addLayout(button_row)

    def _finish(self, label: str) -> None:
        self.clicked_label = label
        self.accept()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        parent = self.parentWidget()
        if parent:
            center = parent.window().frameGeometry().center()
            self.move(center - self.rect().center())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 50:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_position = None
        super().mouseReleaseEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.document: ShortcutDocument | None = None
        self.selected_record: CommandRecord | None = None
        self.settings = QSettings("WaterFAQ", APP_NAME)
        self._building_filter = False
        self._build_ui()
        self._set_loaded_state(False)
        self._center_window()

    def _build_ui(self) -> None:
        window_title = "Revit Hotkey - Назначение горячих клавиш"
        self.setWindowTitle(window_title)
        self.setWindowIcon(QIcon(str(resource_path("icon.png"))))
        self.setMinimumSize(860, 780)
        self.resize(self.minimumSize())
        self.setStyleSheet(stylesheet())

        central = QWidget(objectName="central")
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(22, 18, 22, 12)
        outer.setSpacing(12)

        title = QLabel(window_title, objectName="appTitle")
        outer.addWidget(title)

        source_card = QFrame(objectName="card")
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(16, 13, 16, 13)
        source_layout.setSpacing(8)
        source_layout.addWidget(QLabel("Источник файла", objectName="sectionTitle"))
        source_buttons = QHBoxLayout()
        self.choose_file_button = QPushButton("Выбрать файл")
        self.choose_file_button.setToolTip("Выбрать файл горячих клавиш")
        self.choose_file_button.clicked.connect(self.choose_file)
        self.revit_button = QPushButton("Загрузить из Revit")
        self.revit_button.setToolTip(
            "Найти файлы горячих клавиш в установленных пользовательских профилях Revit."
        )
        self.revit_button.clicked.connect(self.show_revit_menu)
        self.open_folder_button = QPushButton("Открыть папку")
        self.open_folder_button.setToolTip("Открыть папку текущей версии Revit.")
        self.open_folder_button.clicked.connect(self.open_current_folder)
        source_buttons.addWidget(self.choose_file_button)
        source_buttons.addWidget(self.revit_button)
        source_buttons.addWidget(self.open_folder_button)
        source_buttons.addStretch(1)
        source_layout.addLayout(source_buttons)
        self.current_file_label = QLabel("Файл не загружен", objectName="muted")
        self.current_file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        source_layout.addWidget(self.current_file_label)
        self.source_info_label = QLabel("")
        self.source_info_label.setWordWrap(True)
        source_layout.addWidget(self.source_info_label)
        self.source_info_label.hide()
        outer.addWidget(source_card)

        filter_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по имени команды")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setToolTip("Поиск по атрибуту CommandName без учёта регистра.")
        self.search_edit.textChanged.connect(self._search_changed)
        self.category_combo = DownwardComboBox()
        self.category_combo.setMinimumWidth(230)
        self.category_combo.setToolTip(
            "Фильтр по категории из атрибута Paths. Команда может относиться к нескольким категориям."
        )
        self.category_combo.currentTextChanged.connect(self._category_changed)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.category_combo)
        outer.addLayout(filter_row)

        self.table_model = CommandTableModel(self)
        self.proxy_model = CommandFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.rowsInserted.connect(self._update_counts)
        self.proxy_model.rowsRemoved.connect(self._update_counts)
        self.proxy_model.modelReset.connect(self._update_counts)

        self.table = QTableView()
        self.table.setModel(self.proxy_model)
        self.table.setItemDelegate(ExactElideDelegate(self.table))
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(36)
        header = self.table.horizontalHeader()
        header.setSectionsMovable(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setToolTip("Нажмите на заголовок для сортировки. Ширину столбцов можно менять мышью.")
        self.table.selectionModel().selectionChanged.connect(self._selection_changed)

        empty = QLabel("Выберите XML-файл или загрузите горячие клавиши из Revit.")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setObjectName("muted")
        self.table_stack = QStackedWidget()
        self.table_stack.addWidget(empty)
        self.table_stack.addWidget(self.table)
        self.table_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        outer.addWidget(self.table_stack, 1)

        self.count_label = QLabel("Показано: 0 из 0 команд · Изменено: 0", objectName="muted")
        outer.addWidget(self.count_label)

        editor_card = QFrame(objectName="card")
        editor_layout = QVBoxLayout(editor_card)
        editor_layout.setContentsMargins(16, 12, 16, 13)
        editor_layout.setSpacing(8)
        editor_layout.addWidget(QLabel("Назначение комбинации клавиш", objectName="sectionTitle"))
        self.selected_label = QLabel("Выберите команду в таблице", objectName="muted")
        editor_layout.addWidget(self.selected_label)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        grid.addWidget(QLabel("Английская раскладка"), 0, 0)
        grid.addWidget(QLabel("Русская раскладка"), 0, 1)
        self.english_edit = KeyCaptureLineEdit("en")
        self.russian_edit = KeyCaptureLineEdit("ru")
        for edit in (self.english_edit, self.russian_edit):
            edit.pair_captured.connect(self._pair_captured)
            edit.pair_cleared.connect(self._pair_cleared)
            edit.capture_cancelled.connect(self._restore_editor)
            edit.capture_message.connect(self.show_status)
        grid.addWidget(self.english_edit, 1, 0)
        grid.addWidget(self.russian_edit, 1, 1)
        editor_layout.addLayout(grid)
        editor_actions = QHBoxLayout()
        self.both_layouts_check = ToggleSwitch("Назначать в обеих раскладках")
        self.both_layouts_check.setChecked(True)
        self.both_layouts_check.setToolTip(
            "Если включено, соответствующая комбинация во второй раскладке формируется автоматически.\n"
            "Для цифр и других одинаковых символов значение записывается только один раз."
        )
        self.both_layouts_check.toggled.connect(self._both_layouts_toggled)
        self.assign_button = QPushButton("Назначить", objectName="primary")
        self.assign_button.setToolTip("Назначить введённую комбинацию выбранной команде.")
        self.assign_button.clicked.connect(self.assign_shortcuts)
        self.delete_button = QPushButton("Удалить", objectName="danger")
        self.delete_button.setToolTip("Удалить обе назначенные раскладки у выбранной команды.")
        self.delete_button.clicked.connect(self.delete_shortcuts)
        editor_actions.addWidget(self.both_layouts_check)
        editor_actions.addStretch(1)
        editor_actions.addWidget(self.assign_button)
        editor_actions.addWidget(self.delete_button)
        editor_layout.addLayout(editor_actions)
        outer.addWidget(editor_card)

        save_row = QHBoxLayout()
        self.undo_button = QPushButton("Отменить изменения")
        self.undo_button.setToolTip("Вернуть все команды к состоянию на момент загрузки файла.")
        self.undo_button.clicked.connect(self.undo_changes)
        self.save_button = QPushButton("Сохранить", objectName="success")
        self.save_button.setToolTip("Сохранить изменения в текущий файл.")
        self.save_button.clicked.connect(self.save_document)
        self.save_as_button = QPushButton("Сохранить как")
        self.save_as_button.setToolTip("Сохранить XML в выбранное место.")
        self.save_as_button.clicked.connect(self.save_document_as)
        save_row.addWidget(self.undo_button)
        save_row.addStretch(1)
        save_row.addWidget(self.save_button)
        save_row.addWidget(self.save_as_button)
        outer.addLayout(save_row)

        footer = QHBoxLayout()
        version = QLabel(f"v{__version__}", objectName="footer")
        version.setToolTip("Версия программы")
        developer = ClickableLabel("by WaterFAQ", objectName="footer")
        developer.setToolTip("Открыть страницу обратной связи")
        developer.setCursor(Qt.CursorShape.PointingHandCursor)
        developer.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(PROJECT_ISSUES_URL))
        )
        developer.setStyleSheet(
            f"QLabel {{ color: {COLORS['muted']}; }} QLabel:hover {{ color: {COLORS['blue']}; }}"
        )
        footer.addWidget(version)
        footer.addStretch(1)
        footer.addWidget(developer)
        outer.addLayout(footer)

        saved_header = self.settings.value("table/header")
        if saved_header:
            header.restoreState(saved_header)
        else:
            self.table.setColumnWidth(0, 390)
            self.table.setColumnWidth(1, 220)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        apply_windows_frame_colors(self)

    def _center_window(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            self.move(geometry.center() - self.rect().center())

    def _set_loaded_state(self, loaded: bool) -> None:
        self.table_stack.setCurrentIndex(1 if loaded else 0)
        for widget in (
            self.search_edit,
            self.category_combo,
            self.save_button,
            self.save_as_button,
        ):
            widget.setEnabled(loaded)
        self.open_folder_button.setVisible(bool(loaded and self.document and self.document.is_revit_file))
        self._set_editor_enabled(False)
        self.undo_button.setEnabled(bool(loaded and self.document and self.document.dirty))

    def _set_editor_enabled(self, enabled: bool, locked: bool = False) -> None:
        active = enabled and not locked
        self.english_edit.setEnabled(active)
        self.both_layouts_check.setEnabled(active)
        self.russian_edit.setEnabled(active and self.both_layouts_check.isChecked())
        self.assign_button.setEnabled(active)
        self.delete_button.setEnabled(active)

    def show_status(self, message: str, kind: str = "info") -> None:
        colors = {
            "success": COLORS["green"],
            "error": COLORS["red"],
            "warning": COLORS["orange"],
            "info": COLORS["muted"],
        }
        self.source_info_label.setText(message)
        self.source_info_label.setStyleSheet(f"color: {colors.get(kind, COLORS['muted'])};")
        self.source_info_label.setVisible(bool(message))

    def choose_file(self) -> None:
        if not self._confirm_abandon_changes():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбор файла горячих клавиш Revit",
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation),
            "Файлы XML (*.xml);;Все файлы (*.*)",
        )
        if path:
            self.load_document(Path(path))

    def show_revit_menu(self) -> None:
        versions = discover_revit_files()
        if not versions:
            self.show_status(
                "Не найдено версий Revit с назначенными комбинациями клавиш.", "warning"
            )
            return
        menu = QMenu(self)
        for version, path in versions:
            action = menu.addAction(f"Revit {version}")
            action.setToolTip(str(path))
            action.triggered.connect(lambda checked=False, p=path: self._load_revit_path(p))
        menu.exec(self.revit_button.mapToGlobal(QPoint(0, self.revit_button.height())))

    def _load_revit_path(self, path: Path) -> None:
        if self._confirm_abandon_changes():
            self.load_document(path)

    def load_document(self, path: Path) -> None:
        try:
            document = ShortcutDocument.load(path)
        except ShortcutXmlError:
            self._message(
                "Ошибка загрузки",
                "Не удалось загрузить файл. Выбранный XML не является файлом горячих "
                "клавиш Revit или имеет повреждённую структуру.",
                "error",
                [("Закрыть", "accept")],
            )
            return
        self.document = document
        self.selected_record = None
        self.table_model.set_records(document.records)
        self._populate_categories()
        self.search_edit.clear()
        self.category_combo.setCurrentIndex(0)
        self.proxy_model.sort(-1)
        self.current_file_label.setText(
            f"Revit {document.revit_version} — {document.source_path.name}"
            if document.revit_version
            else str(document.source_path)
        )
        self.current_file_label.setToolTip(str(document.source_path))
        self.show_status("Файл успешно загружен.", "success")
        self._set_loaded_state(True)
        self._clear_editor()
        self._update_counts()

    def _populate_categories(self) -> None:
        if not self.document:
            return
        self._building_filter = True
        self.category_combo.clear()
        self.category_combo.addItems(["Все", "Все заданные", "Все незаданные"])
        self.category_combo.addItems(self.document.categories)
        if any(not record.categories for record in self.document.records):
            self.category_combo.addItem("Без категории")
        self._building_filter = False

    def _search_changed(self, text: str) -> None:
        self.proxy_model.set_search_text(text)
        self._after_filter_changed()

    def _category_changed(self, text: str) -> None:
        if self._building_filter:
            return
        self.proxy_model.set_category(text)
        self._after_filter_changed()

    def _after_filter_changed(self) -> None:
        self.table.clearSelection()
        self._clear_editor()
        self._update_counts()

    def _selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            self._clear_editor()
            return
        source_index = self.proxy_model.mapToSource(indexes[0])
        self.selected_record = self.table_model.records[source_index.row()]
        self._restore_editor()

    def _restore_editor(self) -> None:
        record = self.selected_record
        if not record:
            self._clear_editor()
            return
        self.english_edit.reset_capture()
        self.russian_edit.reset_capture()
        self.selected_label.setText(record.name)
        self.selected_label.setToolTip(record.command_id)
        if record.locked:
            self.english_edit.setText(record.system_shortcuts[0] if record.system_shortcuts else "")
            self.russian_edit.clear()
            self.both_layouts_check.setChecked(False)
            self._set_editor_enabled(True, locked=True)
            self.show_status("Системная комбинация клавиш Revit. Изменение недоступно.", "info")
            return
        parts = record.shortcut_parts
        self.both_layouts_check.blockSignals(True)
        self.both_layouts_check.setChecked(len(parts) >= 2 or not parts)
        self.both_layouts_check.blockSignals(False)
        self.english_edit.setText(parts[0] if parts else "")
        self.russian_edit.setText(parts[1] if len(parts) >= 2 else "")
        self._set_editor_enabled(True)

    def _clear_editor(self) -> None:
        self.selected_record = None
        self.selected_label.setText("Выберите команду в таблице")
        self.english_edit.clear()
        self.russian_edit.clear()
        self.english_edit.reset_capture()
        self.russian_edit.reset_capture()
        self.both_layouts_check.blockSignals(True)
        self.both_layouts_check.setChecked(True)
        self.both_layouts_check.blockSignals(False)
        self._set_editor_enabled(False)

    def _pair_captured(self, english: str, russian: str) -> None:
        self.english_edit.setText(english)
        if self.both_layouts_check.isChecked() and english != russian:
            self.russian_edit.setText(russian)
        else:
            self.russian_edit.clear()
        self.show_status("Комбинация клавиш введена. Нажмите «Назначить».", "info")

    def _pair_cleared(self) -> None:
        self.english_edit.clear()
        self.russian_edit.clear()
        self.show_status("Поля комбинации клавиш очищены.", "info")

    def _both_layouts_toggled(self, checked: bool) -> None:
        self.russian_edit.setEnabled(bool(checked and self.selected_record and not self.selected_record.locked))
        if checked:
            english = self.english_edit.text().strip()
            russian = self.russian_edit.text().strip()
            if english and not russian:
                converted = convert_combination(english, "ru")
                if converted != english:
                    self.russian_edit.setText(converted)
            elif russian and not english:
                self.english_edit.setText(convert_combination(russian, "en"))
        else:
            self.russian_edit.clear()
        self.english_edit.reset_capture()
        self.russian_edit.reset_capture()

    def assign_shortcuts(self) -> None:
        if not self.document or not self.selected_record or self.selected_record.locked:
            return
        english = self.english_edit.text().strip()
        russian = self.russian_edit.text().strip() if self.both_layouts_check.isChecked() else ""
        if not english and not russian:
            self.show_status("Введите комбинацию клавиш.", "warning")
            return
        combinations = [value for value in (english, russian) if value]
        for combination in combinations:
            owner = self.document.reserved_owner(combination)
            if owner:
                self._message(
                    "Комбинация клавиш недоступна",
                    f"Введённая комбинация клавиш {combination} зарезервирована системной "
                    f"командой Revit «{owner}». Назначение невозможно.",
                    "warning",
                    [("Закрыть", "accept")],
                )
                return

        conflicts: dict[CommandRecord, list[str]] = {}
        for combination in combinations:
            for record in self.document.conflicts(combination, self.selected_record):
                conflicts.setdefault(record, []).append(combination)
        if conflicts and not self._confirm_replace(conflicts):
            return
        for record, values in conflicts.items():
            for combination in values:
                self.document.remove_combination(record, combination)

        value = english
        if russian and russian != english:
            value = f"{english}#{russian}" if english else russian
        self.document.set_shortcuts(self.selected_record, value)
        self._refresh_after_change("Комбинация клавиш назначена.")

    def _confirm_replace(self, conflicts: dict[CommandRecord, list[str]]) -> bool:
        lines: list[str] = []
        for record, combinations in conflicts.items():
            values = ", ".join(combinations)
            lines.append(f"{values} — «{record.name}»")
        if len(lines) == 1:
            combination = next(iter(conflicts.values()))[0]
            command = next(iter(conflicts.keys())).name
            text = (
                f"Комбинация клавиш {combination} в данный момент назначена команде "
                f"«{command}».\n\nПри замене у этой команды она будет удалена."
            )
        else:
            text = (
                "Введённые комбинации клавиш уже назначены следующим командам:\n\n"
                + "\n".join(lines)
                + "\n\nПри замене у перечисленных команд они будут удалены."
            )
        result = self._message(
            "Комбинация клавиш уже назначена",
            text,
            "warning",
            [
                ("Заменить", "accept"),
                ("Отмена", "reject"),
            ],
        )
        return result == "Заменить"

    def delete_shortcuts(self) -> None:
        if not self.document or not self.selected_record or self.selected_record.locked:
            return
        self.document.set_shortcuts(self.selected_record, None)
        self.english_edit.clear()
        self.russian_edit.clear()
        self._refresh_after_change("Обе комбинации клавиш удалены.")

    def _refresh_after_change(self, message: str) -> None:
        self.table_model.refresh()
        self.proxy_model.invalidateFilter()
        self.undo_button.setEnabled(bool(self.document and self.document.dirty))
        self._update_counts()
        self.show_status(message, "success")

    def undo_changes(self) -> None:
        if not self.document or not self.document.dirty:
            return
        result = self._message(
            "Отмена изменений",
            "Отменить все изменения, внесённые после загрузки файла?",
            "question",
            [
                ("Отменить изменения", "accept"),
                ("Отмена", "reject"),
            ],
        )
        if result != "Отменить изменения":
            return
        self.document.reset_changes()
        self.table_model.refresh()
        self.proxy_model.invalidateFilter()
        self.undo_button.setEnabled(False)
        self._restore_editor()
        self._update_counts()
        self.show_status("Все изменения отменены.", "success")

    def save_document(self) -> bool:
        if not self.document:
            return False
        if not self.document.dirty:
            self.show_status("Изменений для сохранения нет.", "info")
            return True
        return self._save_to(self.document.source_path)

    def save_document_as(self) -> bool:
        if not self.document:
            return False
        initial = str(self.document.source_path.with_name("KeyboardShortcuts.xml"))
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранение файла горячих клавиш Revit",
            initial,
            "Файлы XML (*.xml);;Все файлы (*.*)",
        )
        if not path:
            return False
        if not Path(path).suffix:
            path += ".xml"
        return self._save_to(Path(path))

    def _save_to(self, path: Path) -> bool:
        if not self.document:
            return False
        if revit_version_for_path(path) and self._is_revit_running():
            result = self._message(
                "Revit запущен",
                f"Revit {revit_version_for_path(path)} сейчас запущен. После закрытия Revit "
                "файл горячих клавиш может быть перезаписан. Для надёжного сохранения "
                "рекомендуется сначала закрыть Revit.",
                "warning",
                [
                    ("Сохранить", "accept"),
                    ("Отмена", "reject"),
                ],
            )
            if result != "Сохранить":
                return False
        try:
            backup = self.document.save(path)
        except (OSError, ShortcutXmlError) as exc:
            self._message(
                "Ошибка сохранения",
                f"Не удалось сохранить файл.\n\n{exc}",
                "error",
                [("Закрыть", "accept")],
            )
            return False
        except Exception as exc:  # noqa: BLE001 - show unexpected save failures in Russian
            self._message(
                "Ошибка сохранения",
                f"Не удалось сохранить файл.\n\n{exc}",
                "error",
                [("Закрыть", "accept")],
            )
            return False
        self.current_file_label.setText(
            f"Revit {self.document.revit_version} — {self.document.source_path.name}"
            if self.document.revit_version
            else str(self.document.source_path)
        )
        self.current_file_label.setToolTip(str(self.document.source_path))
        self.open_folder_button.setVisible(self.document.is_revit_file)
        self.table_model.refresh()
        self.undo_button.setEnabled(False)
        self._update_counts()
        message = "Файл успешно сохранён."
        if self.document.is_revit_file:
            message += " Для применения изменений рекомендуется перезапустить соответствующую версию Revit."
        if backup:
            message += f" Резервная копия: {backup.name}."
        self.show_status(message, "success")
        return True

    def _confirm_abandon_changes(self) -> bool:
        if not self.document or not self.document.dirty:
            return True
        result = self._message(
            "Несохранённые изменения",
            "В текущем файле есть несохранённые изменения.",
            "warning",
            [
                ("Сохранить", "accept"),
                ("Не сохранять", "destructive"),
                ("Отмена", "reject"),
            ],
        )
        if result == "Сохранить":
            return self.save_document()
        return result == "Не сохранять"

    def _message(
        self,
        title: str,
        text: str,
        icon: str,
        buttons: list[tuple[str, str]],
    ) -> str:
        box = StyledMessageDialog(title, text, icon, buttons, self)
        box.exec()
        return box.clicked_label

    def _update_counts(self) -> None:
        total = len(self.document.records) if self.document else 0
        visible = self.proxy_model.rowCount() if self.document else 0
        changed = self.document.changed_count if self.document else 0
        self.count_label.setText(f"Показано: {visible} из {total} команд · Изменено: {changed}")

    def open_current_folder(self) -> None:
        if self.document and self.document.is_revit_file:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.document.source_path.parent)))

    @staticmethod
    def _is_revit_running() -> bool:
        if os.name != "nt":
            return False
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Revit.exe", "/NH"],
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=flags,
                check=False,
            )
            return "revit.exe" in result.stdout.casefold()
        except (OSError, subprocess.SubprocessError):
            return False

    def closeEvent(self, event) -> None:
        self.settings.setValue("table/header", self.table.horizontalHeader().saveState())
        if self._confirm_abandon_changes():
            event.accept()
        else:
            event.ignore()


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("WaterFAQ")
    app.setWindowIcon(QIcon(str(resource_path("icon.png"))))
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    return app.exec()
