import csv
import math
from dataclasses import dataclass
from os import PathLike


GREEN = "exact"
ORANGE = "close"
RED = "different"


@dataclass
class Comparison:
    headers: list[str]
    left_rows: list[list[str | None]]
    right_rows: list[list[str | None]]
    statuses: list[list[str]]
    counts: dict[str, int]
    left_row_count: int
    right_row_count: int
    source_file1: str | None = None
    source_file2: str | None = None


def read_csv(path: str) -> tuple[list[str], list[list[str]]]:
    with open(path, "r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.reader(csv_file)
        try:
            headers = next(reader)
        except StopIteration as error:
            raise ValueError(f"{path}: the CSV file is empty.") from error

        rows = []
        for line_number, row in enumerate(reader, start=2):
            if not row:
                continue
            if len(row) > len(headers):
                raise ValueError(
                    f"{path}: row {line_number} has {len(row)} values, "
                    f"but the header has {len(headers)} columns."
                )
            rows.append(row + [""] * (len(headers) - len(row)))
    return headers, rows


def _is_blank_or_nan(value: str | None) -> bool:
    return value is None or not value.strip() or value.strip().lower() == "nan"


def _as_number(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


def compare_values(
    left: str | None, right: str | None, rtol: float, atol: float
) -> str:
    if _is_blank_or_nan(left) or _is_blank_or_nan(right):
        return RED

    left_number = _as_number(left)
    right_number = _as_number(right)
    if left_number is not None and right_number is not None:
        if left_number == 0 or right_number == 0:
            return RED
        if left_number == right_number:
            return GREEN
        if math.isclose(left_number, right_number, rel_tol=rtol, abs_tol=atol):
            return ORANGE
        return RED

    return GREEN if left == right else RED


def _sort_value(value: str) -> tuple[int, float | str]:
    number = _as_number(value)
    if number is not None:
        return 0, number
    return 1, value.casefold()


def compare_csv_files(
    file1: str,
    file2: str,
    ignore_columns: set[str] | None = None,
    sort_key: str | None = None,
    rtol: float = 1e-3,
    atol: float = 1e-5,
) -> Comparison:
    headers1, rows1 = read_csv(file1)
    headers2, rows2 = read_csv(file2)
    if headers1 != headers2:
        raise ValueError("The CSV files must have the same column names in the same order.")
    if not math.isfinite(rtol) or not math.isfinite(atol) or rtol < 0 or atol < 0:
        raise ValueError("Relative and absolute tolerances must be finite and non-negative.")

    if sort_key:
        if sort_key not in headers1:
            raise ValueError(f"Sort column {sort_key!r} was not found in the CSV headers.")
        sort_index = headers1.index(sort_key)
        rows1.sort(key=lambda row: _sort_value(row[sort_index]))
        rows2.sort(key=lambda row: _sort_value(row[sort_index]))

    ignored = ignore_columns or set()
    included_indexes = [
        index for index, header in enumerate(headers1) if header not in ignored
    ]
    included_headers = [headers1[index] for index in included_indexes]
    row_count = max(len(rows1), len(rows2))
    left_rows: list[list[str | None]] = []
    right_rows: list[list[str | None]] = []
    for row_index in range(row_count):
        left_row = rows1[row_index] if row_index < len(rows1) else None
        right_row = rows2[row_index] if row_index < len(rows2) else None
        left_rows.append(
            [left_row[index] for index in included_indexes]
            if left_row is not None
            else [None] * len(included_indexes)
        )
        right_rows.append(
            [right_row[index] for index in included_indexes]
            if right_row is not None
            else [None] * len(included_indexes)
        )

    counts = {GREEN: 0, ORANGE: 0, RED: 0}
    statuses = []
    for left_row, right_row in zip(left_rows, right_rows):
        row_statuses = [
            compare_values(left, right, rtol, atol)
            for left, right in zip(left_row, right_row)
        ]
        statuses.append(row_statuses)
        for status in row_statuses:
            counts[status] += 1
    return Comparison(
        included_headers, left_rows, right_rows, statuses, counts, len(rows1), len(rows2)
    )


def write_comparison_csv(
    result: Comparison,
    output_path: str | PathLike[str],
    source_file1: str | None = None,
    source_file2: str | None = None,
) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        if source_file1 is not None and source_file2 is not None:
            writer.writerow(["# CSV Compare Export", "1"])
            writer.writerow(["# Source File 1", source_file1])
            writer.writerow(["# Source File 2", source_file2])
        headers = ["Row"]
        for header in result.headers:
            headers.extend(
                (f"{header} [File 1]", f"{header} [File 2]", f"{header} [Status]")
            )
        writer.writerow(headers)

        for row_index, (left_row, right_row, statuses) in enumerate(
            zip(result.left_rows, result.right_rows, result.statuses), start=1
        ):
            row = [row_index]
            for left, right, status in zip(left_row, right_row, statuses):
                row.extend((left or "", right or "", status))
            writer.writerow(row)


def read_comparison_csv(path: str | PathLike[str]) -> Comparison:
    with open(path, "r", newline="", encoding="utf-8-sig") as comparison_file:
        reader = csv.reader(comparison_file)
        try:
            saved_headers = next(reader)
        except StopIteration as error:
            raise ValueError(f"{path}: the comparison file is empty.") from error

        source_file1 = None
        source_file2 = None
        if saved_headers == ["# CSV Compare Export", "1"]:
            try:
                file1_metadata = next(reader)
                file2_metadata = next(reader)
            except StopIteration as error:
                raise ValueError(
                    f"{path}: comparison source metadata is incomplete."
                ) from error
            if (
                len(file1_metadata) != 2
                or file1_metadata[0] != "# Source File 1"
                or len(file2_metadata) != 2
                or file2_metadata[0] != "# Source File 2"
            ):
                raise ValueError(f"{path}: comparison source metadata is invalid.")
            source_file1, source_file2 = file1_metadata[1], file2_metadata[1]
            try:
                saved_headers = next(reader)
            except StopIteration as error:
                raise ValueError(f"{path}: the comparison file has no result table.") from error

        if not saved_headers or saved_headers[0] != "Row":
            raise ValueError(
                "This is not a saved comparison CSV. Choose a file exported "
                "with Save Output."
            )
        value_headers = saved_headers[1:]
        if len(value_headers) % 3:
            raise ValueError("The saved comparison CSV has an invalid column layout.")

        headers = []
        for index in range(0, len(value_headers), 3):
            file1_header, file2_header, status_header = value_headers[index : index + 3]
            if not (
                file1_header.endswith(" [File 1]")
                and file2_header.endswith(" [File 2]")
                and status_header.endswith(" [Status]")
            ):
                raise ValueError("The saved comparison CSV has invalid column headers.")
            base_header = file1_header[: -len(" [File 1]")]
            if (
                file2_header[: -len(" [File 2]")] != base_header
                or status_header[: -len(" [Status]")] != base_header
            ):
                raise ValueError("The saved comparison CSV has inconsistent column names.")
            headers.append(base_header)

        left_rows: list[list[str]] = []
        right_rows: list[list[str]] = []
        statuses: list[list[str]] = []
        counts = {GREEN: 0, ORANGE: 0, RED: 0}
        for line_number, row in enumerate(reader, start=2):
            if len(row) != len(saved_headers):
                raise ValueError(
                    f"{path}: row {line_number} has an invalid number of columns."
                )
            left_row = []
            right_row = []
            row_statuses = []
            for index in range(1, len(row), 3):
                left, right, status = row[index : index + 3]
                if status not in counts:
                    raise ValueError(
                        f"{path}: row {line_number} has an unknown comparison status."
                    )
                left_row.append(left)
                right_row.append(right)
                row_statuses.append(status)
                counts[status] += 1
            left_rows.append(left_row)
            right_rows.append(right_row)
            statuses.append(row_statuses)

    row_count = len(statuses)
    return Comparison(
        headers=headers,
        left_rows=left_rows,
        right_rows=right_rows,
        statuses=statuses,
        counts=counts,
        left_row_count=row_count,
        right_row_count=row_count,
        source_file1=source_file1,
        source_file2=source_file2,
    )


def _display_value(value: str | None) -> str:
    if value is None:
        return "<missing>"
    return value.replace("\n", "\\n").replace("\r", "\\r")


def main() -> None:
    from ui.main_window import main as run_gui

    run_gui()


if __name__ == "__main__":
    main()
