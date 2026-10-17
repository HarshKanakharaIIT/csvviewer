import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from csv_compare import Comparison, GREEN, ORANGE, RED


class ComparisonHistory:
    def __init__(
        self, path: Path | None = None, legacy_path: Path | None = None
    ):
        if path is None:
            self.path = _default_history_path()
            legacy_path = legacy_path or _legacy_history_path()
        else:
            self.path = Path(path)

        if legacy_path is not None:
            self._migrate_legacy_file(Path(legacy_path))

    def list_entries(self) -> list[dict[str, Any]]:
        return self._read_entries()

    def get(self, entry_id: str) -> dict[str, Any]:
        for entry in self._read_entries():
            if entry["id"] == entry_id:
                return entry
        raise KeyError("The saved comparison no longer exists.")

    def create(self, entry: dict[str, Any]) -> dict[str, Any]:
        entries = self._read_entries()
        now = _timestamp()
        saved = {**entry, "id": str(uuid.uuid4()), "created_at": now, "updated_at": now}
        entries.append(saved)
        self._write_entries(entries)
        return saved

    def update(self, entry_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        entries = self._read_entries()
        for index, existing in enumerate(entries):
            if existing["id"] == entry_id:
                updated = {
                    **entry,
                    "id": entry_id,
                    "created_at": existing["created_at"],
                    "updated_at": _timestamp(),
                }
                entries[index] = updated
                self._write_entries(entries)
                return updated
        raise KeyError("The saved comparison no longer exists.")

    def delete(self, entry_id: str) -> None:
        entries = self._read_entries()
        remaining = [entry for entry in entries if entry["id"] != entry_id]
        if len(remaining) == len(entries):
            raise KeyError("The saved comparison no longer exists.")
        self._write_entries(remaining)

    def _read_entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as history_file:
                data = json.load(history_file)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Could not read comparison history: {error}") from error

        if (
            not isinstance(data, dict)
            or data.get("version") != 1
            or not isinstance(data.get("comparisons"), list)
        ):
            raise ValueError("Comparison history has an unsupported or invalid format.")
        for entry in data["comparisons"]:
            _validate_entry(entry)
        return data["comparisons"]

    def _migrate_legacy_file(self, legacy_path: Path) -> None:
        if self.path.exists() or not legacy_path.is_file():
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(legacy_path, self.path)
        except OSError as error:
            raise OSError(
                f"Could not move saved comparison history from {legacy_path} "
                f"to {self.path}: {error}"
            ) from error

    def _write_entries(self, entries: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as history_file:
                temporary_path = Path(history_file.name)
                json.dump(
                    {"version": 1, "comparisons": entries},
                    history_file,
                    indent=2,
                    ensure_ascii=False,
                )
                history_file.write("\n")
                history_file.flush()
                os.fsync(history_file.fileno())
            os.replace(temporary_path, self.path)
        except OSError as error:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise OSError(f"Could not write comparison history: {error}") from error


def create_history_entry(
    name: str,
    file1: str,
    file2: str,
    ignore_columns: set[str],
    sort_key: str | None,
    rtol: float,
    atol: float,
    result: Comparison,
) -> dict[str, Any]:
    return {
        "name": name,
        "file1": file1,
        "file2": file2,
        "ignore_columns": sorted(ignore_columns),
        "sort_key": sort_key,
        "rtol": rtol,
        "atol": atol,
        "result": {
            "headers": result.headers,
            "left_rows": result.left_rows,
            "right_rows": result.right_rows,
            "statuses": result.statuses,
            "counts": result.counts,
            "left_row_count": result.left_row_count,
            "right_row_count": result.right_row_count,
        },
    }


def comparison_from_entry(entry: dict[str, Any]) -> Comparison:
    _validate_entry(entry)
    result = entry["result"]
    return Comparison(
        headers=result["headers"],
        left_rows=result["left_rows"],
        right_rows=result["right_rows"],
        statuses=result["statuses"],
        counts=result["counts"],
        left_row_count=result["left_row_count"],
        right_row_count=result["right_row_count"],
    )


def _validate_entry(entry: Any) -> None:
    required = {
        "id",
        "name",
        "created_at",
        "updated_at",
        "file1",
        "file2",
        "ignore_columns",
        "sort_key",
        "rtol",
        "atol",
        "result",
    }
    if not isinstance(entry, dict) or not required.issubset(entry):
        raise ValueError("Comparison history contains an invalid entry.")
    result = entry["result"]
    if not isinstance(result, dict):
        raise ValueError("Comparison history contains an invalid result snapshot.")
    result_required = {
        "headers",
        "left_rows",
        "right_rows",
        "statuses",
        "counts",
        "left_row_count",
        "right_row_count",
    }
    if not result_required.issubset(result):
        raise ValueError("Comparison history contains an incomplete result snapshot.")

    headers = result["headers"]
    left_rows = result["left_rows"]
    right_rows = result["right_rows"]
    statuses = result["statuses"]
    if not all(isinstance(value, list) for value in (headers, left_rows, right_rows, statuses)):
        raise ValueError("Comparison history contains invalid result rows.")
    if not (len(left_rows) == len(right_rows) == len(statuses)):
        raise ValueError("Comparison history contains mismatched result rows.")
    if any(
        not isinstance(row, list) or len(row) != len(headers)
        for rows in (left_rows, right_rows, statuses)
        for row in rows
    ):
        raise ValueError("Comparison history contains rows with invalid column counts.")
    if any(status not in {GREEN, ORANGE, RED} for row in statuses for status in row):
        raise ValueError("Comparison history contains an unknown cell status.")
    counts = result["counts"]
    if not isinstance(counts, dict) or any(
        not isinstance(counts.get(status), int) for status in (GREEN, ORANGE, RED)
    ):
        raise ValueError("Comparison history contains invalid comparison counts.")


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_history_path() -> Path:
    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            data_home = Path(
                os.environ.get(
                    "LOCALAPPDATA", Path.home() / "AppData" / "Local"
                )
            )
        elif sys.platform == "darwin":
            data_home = Path.home() / "Library" / "Application Support"
        else:
            data_home = Path(
                os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
            )
        return data_home / "csvviewer" / "history" / "comparison_history.json"
    return Path(__file__).resolve().parent / "history" / "comparison_history.json"


def _legacy_history_path() -> Path | None:
    if getattr(sys, "frozen", False):
        return None
    return Path(__file__).resolve().parent / ".csv_compare_history.json"
