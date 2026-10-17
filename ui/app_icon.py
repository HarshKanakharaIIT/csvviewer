import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def application_icon() -> QIcon:
    if getattr(sys, "frozen", False):
        asset_root = Path(sys._MEIPASS)
    else:
        asset_root = Path(__file__).resolve().parent.parent
    return QIcon(str(asset_root / "assets" / "csvviewer.svg"))
