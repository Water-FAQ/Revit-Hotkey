"""Physical-key conversion for English and Russian keyboard layouts."""

from __future__ import annotations

from dataclasses import dataclass

# Windows virtual-key codes. Letter VK codes are layout independent and are
# therefore preferable to event.text(), which follows the active Windows layout.
VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_DELETE = 0x2E


EN_OEM = {
    0xBA: ";",
    0xBB: "=",
    0xBC: ",",
    0xBD: "-",
    0xBE: ".",
    0xBF: "/",
    0xC0: "`",
    0xDB: "[",
    0xDC: "\\",
    0xDD: "]",
    0xDE: "'",
    0xE2: "\\",
}

RU_LETTERS = {
    **dict(zip(map(ord, "QWERTYUIOP"), "йцукенгшщз")),
    **dict(zip(map(ord, "ASDFGHJKL"), "фывапролд")),
    **dict(zip(map(ord, "ZXCVBNM"), "ячсмить")),
}

RU_OEM = {
    0xBA: "ж",
    0xBB: "=",
    0xBC: "б",
    0xBD: "-",
    0xBE: "ю",
    0xBF: ".",
    0xC0: "ё",
    0xDB: "х",
    0xDC: "\\",
    0xDD: "ъ",
    0xDE: "э",
    0xE2: "\\",
}

IGNORED_VKS = {
    VK_TAB,
    VK_RETURN,
    VK_MENU,
    VK_SPACE,
    VK_DELETE,
    0x14,  # Caps Lock
    0x21,  # Page Up
    0x22,  # Page Down
    0x23,  # End
    0x24,  # Home
    0x25,  # Left
    0x26,  # Up
    0x27,  # Right
    0x28,  # Down
    0x2C,  # Print Screen
    0x2D,  # Insert
    0x5B,  # Left Windows
    0x5C,  # Right Windows
    0x5D,  # Menu
    0x90,  # Num Lock
    0x91,  # Scroll Lock
}


@dataclass(frozen=True)
class KeyPair:
    english: str
    russian: str

    @property
    def layout_independent(self) -> bool:
        return self.english == self.russian


def key_pair_from_vk(vk: int) -> KeyPair | None:
    """Return characters at the same physical key in EN and RU layouts."""
    if 0x41 <= vk <= 0x5A:
        return KeyPair(chr(vk), RU_LETTERS[vk])
    if 0x30 <= vk <= 0x39:
        value = chr(vk)
        return KeyPair(value, value)
    if 0x60 <= vk <= 0x69:  # numeric keypad
        value = str(vk - 0x60)
        return KeyPair(value, value)
    if vk in EN_OEM:
        return KeyPair(EN_OEM[vk], RU_OEM[vk])
    if vk == 0x6A:
        return KeyPair("*", "*")
    if vk == 0x6B:
        return KeyPair("+", "+")
    if vk == 0x6D:
        return KeyPair("-", "-")
    if vk == 0x6E:
        return KeyPair(".", ".")
    if vk == 0x6F:
        return KeyPair("/", "/")
    return None


def make_modified_pair(modifier: str, pair: KeyPair) -> KeyPair:
    prefix = "Ctrl" if modifier.lower() == "ctrl" else "Shift"
    return KeyPair(f"{prefix}+{pair.english}", f"{prefix}+{pair.russian}")


def canonical_shortcut(value: str) -> str:
    """Normalize a combination for conflict and reservation comparisons."""
    value = value.strip()
    if not value:
        return ""
    parts = value.split("+")
    normalized: list[str] = []
    for part in parts:
        lowered = part.strip().lower()
        if lowered in {"ctrl", "control"}:
            normalized.append("CTRL")
        elif lowered == "shift":
            normalized.append("SHIFT")
        elif len(part.strip()) == 1 and part.strip().isascii():
            normalized.append(part.strip().upper())
        else:
            normalized.append(part.strip().casefold())
    return "+".join(normalized)


def convert_combination(value: str, target: str) -> str:
    """Convert a displayed combination to the same physical keys in EN or RU."""
    value = value.strip()
    if not value:
        return ""
    prefix = ""
    body = value
    if "+" in value:
        possible_prefix, body = value.rsplit("+", 1)
        if possible_prefix.casefold() in {"ctrl", "control", "shift"}:
            prefix = "Ctrl+" if possible_prefix.casefold() in {"ctrl", "control"} else "Shift+"
        else:
            body = value

    pairs = [key_pair_from_vk(vk) for vk in list(range(0x30, 0x3A)) + list(range(0x41, 0x5B)) + list(EN_OEM)]
    pairs = [pair for pair in pairs if pair]
    en_to_ru = {pair.english.upper(): pair.russian for pair in pairs}
    ru_to_en = {pair.russian.casefold(): pair.english.upper() for pair in pairs}
    converted: list[str] = []
    for character in body:
        if target == "ru":
            converted.append(en_to_ru.get(character.upper(), character.casefold()))
        else:
            converted.append(ru_to_en.get(character.casefold(), character.upper()))
    return prefix + "".join(converted)
