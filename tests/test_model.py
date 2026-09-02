import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from revit_hotkey.model import (
    ShortcutDocument,
    ShortcutXmlError,
    categories_from_paths,
    discover_revit_files,
    revit_version_for_path,
)

SAMPLE = """<Shortcuts>\r
  <ShortcutItem CommandName="Проем" CommandId="ID_OPENING" Shortcuts="45" Paths="Архитектура&gt;Проемы; Контекстные вкладки&gt;Изменить" />\r
  <ShortcutItem CommandName="Свойства" CommandId="ID_PROPERTIES" Shortcuts="LH#др" Paths="Вид&gt;Окна" />\r
  <ShortcutItem CommandName="Без пути" CommandId="ID_NO_PATH" />\r
  <ShortcutItem CommandName="Сохранить" CommandId="ID_REVIT_FILE_SAVE" Paths="Меню приложения" />\r
</Shortcuts>\r
"""


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "sample.xml"
        self.path.write_text(SAMPLE, encoding="utf-8", newline="")

    def tearDown(self):
        self.temp.cleanup()

    def test_load_and_categories(self):
        doc = ShortcutDocument.load(self.path)
        self.assertEqual(len(doc.records), 4)
        self.assertEqual(
            categories_from_paths("Архитектура>Проемы; Вид>Окна"),
            ("Архитектура", "Вид"),
        )
        self.assertIn("Архитектура", doc.categories)
        self.assertTrue(doc.records[-1].locked)
        self.assertEqual(doc.records[-1].display_shortcuts, "Ctrl+S")

    def test_invalid_xml_is_rejected(self):
        bad = self.root / "bad.xml"
        bad.write_text("<Wrong />", encoding="utf-8")
        with self.assertRaises(ShortcutXmlError):
            ShortcutDocument.load(bad)

    def test_conflict_replacement_removes_only_matching_part(self):
        doc = ShortcutDocument.load(self.path)
        opening, properties = doc.records[:2]
        doc.set_shortcuts(opening, "LH#45")
        conflicts = doc.conflicts("LH", properties)
        self.assertEqual(conflicts, [opening])
        doc.remove_combination(opening, "LH")
        self.assertEqual(opening.current_shortcuts, "45")

    def test_system_reservation(self):
        doc = ShortcutDocument.load(self.path)
        owner = doc.reserved_owner("ctrl+s")
        self.assertEqual(owner, "Сохранить")
        self.assertEqual(doc.reserved_owner("Shift+W"), "Динамический вид")

    def test_delete_removes_attribute_and_save_is_valid(self):
        doc = ShortcutDocument.load(self.path)
        doc.set_shortcuts(doc.records[0], None)
        target = self.root / "result.xml"
        doc.save(target)
        root = ET.parse(target).getroot()
        self.assertNotIn("Shortcuts", root[0].attrib)
        self.assertFalse(doc.dirty)

    def test_backup_for_revit_file(self):
        folder = self.root / "Autodesk" / "Revit" / "Autodesk Revit 2025"
        folder.mkdir(parents=True)
        target = folder / "KeyboardShortcuts.xml"
        target.write_text(SAMPLE, encoding="utf-8", newline="")
        doc = ShortcutDocument.load(target)
        doc.set_shortcuts(doc.records[0], "67")
        backup = doc.save()
        self.assertIsNotNone(backup)
        self.assertTrue(backup.exists())
        self.assertTrue(backup.name.startswith("KeyboardShortcuts - "))
        self.assertEqual(revit_version_for_path(target), "2025")

    def test_discovery_uses_assigned_files_and_newest_first(self):
        appdata = self.root / "Roaming"
        for version, assigned in (("2024", True), ("2026", True), ("2025", False)):
            folder = appdata / "Autodesk" / "Revit" / f"Autodesk Revit {version}"
            folder.mkdir(parents=True)
            xml = (
                '<Shortcuts><ShortcutItem CommandName="A" CommandId="A" Shortcuts="AA" /></Shortcuts>'
                if assigned
                else '<Shortcuts><ShortcutItem CommandName="A" CommandId="A" /></Shortcuts>'
            )
            (folder / "KeyboardShortcuts.xml").write_text(xml, encoding="utf-8")
        found = discover_revit_files(appdata)
        self.assertEqual([version for version, _ in found], ["2026", "2024"])


if __name__ == "__main__":
    unittest.main()
