import unittest

from revit_hotkey.keymap import (
    canonical_shortcut,
    convert_combination,
    key_pair_from_vk,
    make_modified_pair,
)


class KeymapTests(unittest.TestCase):
    def test_letters_are_mapped_by_physical_key(self):
        n = key_pair_from_vk(ord("N"))
        b = key_pair_from_vk(ord("B"))
        self.assertEqual(n.english + b.english, "NB")
        self.assertEqual(n.russian + b.russian, "ти")

    def test_digits_are_layout_independent(self):
        four = key_pair_from_vk(ord("4"))
        self.assertEqual(four.english, "4")
        self.assertEqual(four.russian, "4")
        self.assertTrue(four.layout_independent)

    def test_oem_key_is_mapped(self):
        slash = key_pair_from_vk(0xBF)
        self.assertEqual(slash.english, "/")
        self.assertEqual(slash.russian, ".")

    def test_modifier_uses_physical_key(self):
        pair = make_modified_pair("shift", key_pair_from_vk(ord("Q")))
        self.assertEqual(pair.english, "Shift+Q")
        self.assertEqual(pair.russian, "Shift+й")

    def test_canonical_form(self):
        self.assertEqual(canonical_shortcut("ctrl+q"), canonical_shortcut("Ctrl+Q"))
        self.assertEqual(canonical_shortcut("ТИ"), canonical_shortcut("ти"))

    def test_existing_combination_can_be_converted(self):
        self.assertEqual(convert_combination("NB", "ru"), "ти")
        self.assertEqual(convert_combination("ти", "en"), "NB")
        self.assertEqual(convert_combination("Ctrl+Q", "ru"), "Ctrl+й")
        self.assertEqual(convert_combination("54", "ru"), "54")


if __name__ == "__main__":
    unittest.main()
