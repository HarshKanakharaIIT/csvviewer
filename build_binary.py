import os
import platform
import subprocess
from pathlib import Path

from PyInstaller.__main__ import run


def _render_icon_png(icon: Path, destination: Path) -> None:
    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    image = QImage(1024, 1024, QImage.Format.Format_ARGB32)
    image.fill(0)
    renderer = QSvgRenderer(QByteArray(icon.read_bytes()))
    if not renderer.isValid():
        raise ValueError(f"Application icon is not a valid SVG: {icon}")
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    if not image.save(str(destination), "PNG"):
        raise OSError(f"Could not render application icon to {destination}")


def _native_icon_args(icon: Path) -> list[str]:
    system = platform.system()
    if system not in {"Windows", "Darwin"}:
        return []

    build_dir = Path("build")
    build_dir.mkdir(parents=True, exist_ok=True)
    png_path = build_dir / "csvviewer-icon.png"
    _render_icon_png(icon, png_path)

    from PIL import Image

    image = Image.open(png_path).convert("RGBA")
    if system == "Windows":
        ico_path = build_dir / "csvviewer.ico"
        image.save(
            ico_path,
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
        return ["--icon", str(ico_path.resolve())]

    iconset = build_dir / "csvviewer.iconset"
    iconset.mkdir(exist_ok=True)
    for size in (16, 32, 128, 256, 512):
        image.resize((size, size), Image.Resampling.LANCZOS).save(
            iconset / f"icon_{size}x{size}.png"
        )
        image.resize((size * 2, size * 2), Image.Resampling.LANCZOS).save(
            iconset / f"icon_{size}x{size}@2x.png"
        )

    icns_path = build_dir / "csvviewer.icns"
    subprocess.run(
        ["iconutil", "-c", "icns", "--output", str(icns_path), str(iconset)],
        check=True,
    )
    return ["--icon", str(icns_path.resolve())]


def main() -> None:
    icon = Path("assets/csvviewer.svg")
    if not icon.is_file():
        raise FileNotFoundError(f"Application icon was not found: {icon}")

    args = [
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "CSVCompare",
        "--distpath",
        "dist",
        "--workpath",
        "build/pyinstaller",
        "--specpath",
        "build",
        "--add-data",
        f"{icon.resolve()}{os.pathsep}assets",
    ]
    args.extend(_native_icon_args(icon))
    args.append("csv_compare.py")
    run(args)


if __name__ == "__main__":
    main()
