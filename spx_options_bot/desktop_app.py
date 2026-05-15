from __future__ import annotations

import ctypes
import sys
import traceback
from pathlib import Path

from spx_options_bot.web_gui import main


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def _show_error(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, "SPXBot Fehler", 0x10)
    except Exception:
        print(message)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_path = _app_dir() / "SPXBot_error.log"
        log_path.write_text(traceback.format_exc(), encoding="utf-8")
        _show_error(
            "SPXBot konnte nicht gestartet werden.\n\n"
            f"Details wurden gespeichert in:\n{log_path}"
        )
        raise
