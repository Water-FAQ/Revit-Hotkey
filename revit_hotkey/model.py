"""XML model and safe persistence for Revit keyboard shortcuts."""

from __future__ import annotations

import io
import os
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .keymap import canonical_shortcut

REVIT_FOLDER_RE = re.compile(r"^Autodesk Revit (20\d{2})$")


@dataclass(frozen=True)
class SystemCommand:
    shortcuts: tuple[str, ...]


# Fixed Revit commands shown in the user's reference. They are not stored in
# the Shortcuts attribute and must remain read-only.
SYSTEM_COMMANDS: dict[str, SystemCommand] = {
    "ID_APP_EXIT": SystemCommand(("Alt+F4",)),
    "ID_REVIT_FILE_CLOSE": SystemCommand(("Ctrl+W",)),
    "ID_EDIT_COPY": SystemCommand(("Ctrl+C", "Ctrl+Insert")),
    "ID_EDIT_CUT": SystemCommand(("Ctrl+X", "Shift+Delete")),
    "ID_EDIT_PASTE": SystemCommand(("Ctrl+V",)),
    "ID_BUTTON_UNDO": SystemCommand(("Ctrl+Z", "Alt+Backspace")),
    "ID_BUTTON_REDO": SystemCommand(("Ctrl+Shift+Z", "Ctrl+Y")),
    "ID_FILE_NEW_CHOOSE_TEMPLATE": SystemCommand(("Ctrl+N",)),
    "ID_REVIT_FILE_OPEN": SystemCommand(("Ctrl+O",)),
    "ID_REVIT_FILE_PRINT": SystemCommand(("Ctrl+P",)),
    "ID_REVIT_FILE_SAVE": SystemCommand(("Ctrl+S",)),
    "ID_FIND_IN_PROJECT_BROWSER": SystemCommand(("Ctrl+F",)),
    "ID_HELP_FINDER": SystemCommand(("F1",)),
    "ID_CHECK_SPELLING": SystemCommand(("F7",)),
    "ID_SCHEDULE_VIEW_ZOOM_IN": SystemCommand(("Ctrl++",)),
    "ID_SCHEDULE_VIEW_ZOOM_OUT": SystemCommand(("Ctrl+-",)),
    "ID_SCHEDULE_VIEW_ZOOM_RESTORE": SystemCommand(("Ctrl+0",)),
}

RESERVED_COMBINATIONS: dict[str, str] = {
    "Alt+F4": "Выход из Revit",
    "Ctrl+W": "Закрыть",
    "Ctrl+C": "Копировать в буфер",
    "Ctrl+Insert": "Копировать в буфер",
    "Ctrl+X": "Вырезать в буфер",
    "Shift+Delete": "Вырезать в буфер",
    "Ctrl+V": "Вставить; Вставить из буфера",
    "Ctrl+Z": "Отменить",
    "Alt+Backspace": "Отменить",
    "Ctrl+Shift+Z": "Повторить",
    "Ctrl+Y": "Повторить",
    "Ctrl+N": "Создать; Проект",
    "Ctrl+O": "Открыть; Файл Revit",
    "Ctrl+P": "Печать",
    "Ctrl+S": "Сохранить",
    "Ctrl+F": "Поиск в Диспетчере проекта",
    "F1": "Справка",
    "F5": "Обновить",
    "F7": "Проверка орфографии",
    "F8": "Динамический вид",
    "Shift+W": "Динамический вид",
    "Ctrl+D": "Переключить на главную",
    "Ctrl++": "Увеличить масштаб спецификации",
    "Ctrl+-": "Уменьшить масштаб спецификации",
    "Ctrl+0": "Восстановление масштаба вида спецификации",
}


class ShortcutXmlError(ValueError):
    pass


@dataclass(eq=False)
class CommandRecord:
    element: ET.Element
    name: str
    command_id: str
    paths: str
    categories: tuple[str, ...]
    original_shortcuts: str | None
    current_shortcuts: str | None
    system_shortcuts: tuple[str, ...] = field(default_factory=tuple)

    @property
    def locked(self) -> bool:
        return bool(self.system_shortcuts)

    @property
    def assigned(self) -> bool:
        return bool(self.system_shortcuts or (self.current_shortcuts or "").strip())

    @property
    def changed(self) -> bool:
        return (self.original_shortcuts or "") != (self.current_shortcuts or "")

    @property
    def shortcut_parts(self) -> list[str]:
        return split_shortcuts(self.current_shortcuts)

    @property
    def display_shortcuts(self) -> str:
        values = self.system_shortcuts if self.locked else tuple(self.shortcut_parts)
        return "   ".join(values)


def split_shortcuts(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split("#") if part.strip()]


def categories_from_paths(paths: str) -> tuple[str, ...]:
    categories: list[str] = []
    for path in paths.split(";"):
        path = path.strip()
        if not path:
            continue
        category = path.split(">", 1)[0].strip()
        if category and category not in categories:
            categories.append(category)
    return tuple(categories)


def revit_version_for_path(path: str | Path) -> str | None:
    path = Path(path)
    if path.name.casefold() != "keyboardshortcuts.xml":
        return None
    match = REVIT_FOLDER_RE.match(path.parent.name)
    if not match:
        return None
    try:
        if path.parent.parent.name.casefold() != "revit":
            return None
        if path.parent.parent.parent.name.casefold() != "autodesk":
            return None
    except IndexError:
        return None
    return match.group(1)


class ShortcutDocument:
    def __init__(self, source_path: Path, tree: ET.ElementTree, newline: bytes):
        self.source_path = source_path
        self.tree = tree
        self.newline = newline
        self.records: list[CommandRecord] = []
        self._build_records()

    @classmethod
    def load(cls, path: str | Path) -> ShortcutDocument:
        source = Path(path)
        try:
            raw = source.read_bytes()
        except OSError as exc:
            raise ShortcutXmlError(f"Не удалось прочитать файл: {exc}") from exc
        newline = b"\r\n" if b"\r\n" in raw else b"\n"
        try:
            tree = ET.ElementTree(ET.fromstring(raw))
        except (ET.ParseError, ValueError) as exc:
            raise ShortcutXmlError("XML имеет повреждённую структуру.") from exc
        root = tree.getroot()
        if root.tag != "Shortcuts":
            raise ShortcutXmlError("Корневой элемент XML должен называться Shortcuts.")
        items = list(root)
        if not items or any(item.tag != "ShortcutItem" for item in items):
            raise ShortcutXmlError("Файл не содержит список ShortcutItem.")
        if any(not item.get("CommandName") or not item.get("CommandId") for item in items):
            raise ShortcutXmlError("В одной или нескольких командах отсутствуют обязательные атрибуты.")
        return cls(source.resolve(), tree, newline)

    def _build_records(self) -> None:
        for element in self.tree.getroot():
            command_id = element.get("CommandId", "")
            value = element.get("Shortcuts")
            paths = element.get("Paths", "")
            system = SYSTEM_COMMANDS.get(command_id)
            self.records.append(
                CommandRecord(
                    element=element,
                    name=element.get("CommandName", ""),
                    command_id=command_id,
                    paths=paths,
                    categories=categories_from_paths(paths),
                    original_shortcuts=value,
                    current_shortcuts=value,
                    system_shortcuts=system.shortcuts if system else (),
                )
            )

    @property
    def dirty(self) -> bool:
        return any(record.changed for record in self.records)

    @property
    def changed_count(self) -> int:
        return sum(record.changed for record in self.records)

    @property
    def revit_version(self) -> str | None:
        return revit_version_for_path(self.source_path)

    @property
    def is_revit_file(self) -> bool:
        return self.revit_version is not None

    @property
    def categories(self) -> list[str]:
        values = {category for record in self.records for category in record.categories}
        return sorted(values, key=str.casefold)

    def set_shortcuts(self, record: CommandRecord, value: str | None) -> None:
        if record.locked:
            raise ValueError("Системная команда Revit недоступна для изменения.")
        cleaned = value.strip() if value else None
        record.current_shortcuts = cleaned or None

    def reset_changes(self) -> None:
        for record in self.records:
            record.current_shortcuts = record.original_shortcuts

    def conflicts(self, combination: str, target: CommandRecord) -> list[CommandRecord]:
        wanted = canonical_shortcut(combination)
        if not wanted:
            return []
        return [
            record
            for record in self.records
            if record is not target
            and not record.locked
            and any(canonical_shortcut(part) == wanted for part in record.shortcut_parts)
        ]

    def reserved_owner(self, combination: str) -> str | None:
        wanted = canonical_shortcut(combination)
        for record in self.records:
            if record.locked and any(
                canonical_shortcut(value) == wanted for value in record.system_shortcuts
            ):
                return record.name.strip()
        for reserved, owner in RESERVED_COMBINATIONS.items():
            if canonical_shortcut(reserved) == wanted:
                return owner
        return None

    def remove_combination(self, record: CommandRecord, combination: str) -> None:
        wanted = canonical_shortcut(combination)
        remaining = [
            part for part in record.shortcut_parts if canonical_shortcut(part) != wanted
        ]
        self.set_shortcuts(record, "#".join(remaining) or None)

    def _apply_to_tree(self) -> None:
        for record in self.records:
            if record.locked:
                continue
            if record.current_shortcuts:
                record.element.set("Shortcuts", record.current_shortcuts)
            else:
                record.element.attrib.pop("Shortcuts", None)

    def _serialized(self) -> bytes:
        self._apply_to_tree()
        buffer = io.BytesIO()
        self.tree.write(
            buffer,
            encoding="utf-8",
            xml_declaration=False,
            short_empty_elements=True,
        )
        data = buffer.getvalue()
        if self.newline == b"\r\n":
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        return data

    def save(self, target: str | Path | None = None) -> Path | None:
        destination = Path(target).resolve() if target else self.source_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup_path: Path | None = None
        if destination.exists() and revit_version_for_path(destination):
            stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")  # noqa: DTZ005
            backup_path = destination.with_name(f"KeyboardShortcuts - {stamp}.xml")
            counter = 2
            while backup_path.exists():
                backup_path = destination.with_name(
                    f"KeyboardShortcuts - {stamp} ({counter}).xml"
                )
                counter += 1
            shutil.copy2(destination, backup_path)

        data = self._serialized()
        temporary: Path | None = None
        try:
            handle, temporary_name = tempfile.mkstemp(
                prefix="KeyboardShortcuts_", suffix=".tmp", dir=destination.parent
            )
            temporary = Path(temporary_name)
            with os.fdopen(handle, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            validation_tree = ET.parse(temporary)
            if validation_tree.getroot().tag != "Shortcuts":
                raise ShortcutXmlError("Проверка сохранённого XML завершилась ошибкой.")
            os.replace(temporary, destination)
        except Exception:
            if temporary and temporary.exists():
                temporary.unlink(missing_ok=True)
            raise

        self.source_path = destination
        for record in self.records:
            record.original_shortcuts = record.current_shortcuts
        return backup_path


def discover_revit_files(appdata: str | Path | None = None) -> list[tuple[str, Path]]:
    base = Path(appdata or os.environ.get("APPDATA", ""))
    revit_root = base / "Autodesk" / "Revit"
    found: list[tuple[str, Path]] = []
    if not revit_root.is_dir():
        return found
    for folder in revit_root.iterdir():
        match = REVIT_FOLDER_RE.match(folder.name)
        if not match:
            continue
        candidate = folder / "KeyboardShortcuts.xml"
        if not candidate.is_file():
            continue
        try:
            root = ET.parse(candidate).getroot()
            has_assigned = any((item.get("Shortcuts") or "").strip() for item in root)
        except (OSError, ET.ParseError):
            continue
        if has_assigned:
            found.append((match.group(1), candidate.resolve()))
    return sorted(found, key=lambda item: item[0], reverse=True)
