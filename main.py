"""Entry point for Revit Hotkey."""

from __future__ import annotations

import ctypes
import os

from revit_hotkey.app import run


def set_windows_app_id() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "WaterFAQ.RevitHotkey.1.0.0"
        )
    except (AttributeError, OSError):
        pass


if __name__ == "__main__":
    set_windows_app_id()
    raise SystemExit(run())

