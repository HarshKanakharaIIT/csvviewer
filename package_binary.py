import os
import platform
import stat
import tempfile
import zipfile
from pathlib import Path


def _platform_name() -> str:
    names = {
        "Linux": "Linux",
        "Windows": "Windows",
        "Darwin": "macOS",
    }
    try:
        return names[platform.system()]
    except KeyError as error:
        raise RuntimeError(f"Unsupported build platform: {platform.system()}") from error


def _architecture_name() -> str:
    names = {
        "AMD64": "x86_64",
        "x86_64": "x86_64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    machine = platform.machine()
    try:
        return names[machine]
    except KeyError as error:
        raise RuntimeError(f"Unsupported build architecture: {machine}") from error


def main() -> None:
    suffix = ".exe" if platform.system() == "Windows" else ""
    binary = Path("dist") / f"CSVCompare{suffix}"
    if not binary.is_file():
        raise FileNotFoundError(f"Packaged executable was not found: {binary}")

    archive = Path("dist") / (
        f"CSVCompare-{_platform_name()}-{_architecture_name()}.zip"
    )
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=archive.parent,
            prefix=f".{archive.stem}-",
            suffix=".zip",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        with zipfile.ZipFile(temporary_path, "w", zipfile.ZIP_DEFLATED) as package:
            binary_info = zipfile.ZipInfo(binary.name)
            binary_mode = stat.S_IFREG | (binary.stat().st_mode & 0o777)
            binary_info.external_attr = binary_mode << 16
            binary_info.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(binary_info, binary.read_bytes())
            package.write("README.md", "README.md")
        os.replace(temporary_path, archive)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise

    print(f"Created {binary}")
    print(f"Created {archive}")


if __name__ == "__main__":
    main()
