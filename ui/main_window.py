import csv
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from comparison_history import (
    ComparisonHistory,
    comparison_from_entry,
    create_history_entry,
)
from csv_compare import (
    Comparison,
    GREEN,
    ORANGE,
    RED,
    compare_csv_files,
    read_comparison_csv,
    read_csv,
    write_comparison_csv,
)
from ui.app_icon import application_icon
from ui.widgets import (
    ComparisonSettingsWidget,
    CsvFilePicker,
    HistoryPanel,
    ResultsTableWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV Comparison")
        self.setWindowIcon(application_icon())
        self.resize(1100, 700)

        self.file1_picker = CsvFilePicker("File 1:")
        self.file2_picker = CsvFilePicker("File 2:")
        self.settings = ComparisonSettingsWidget()
        self.history = HistoryPanel()
        self.results = ResultsTableWidget()
        self.history_store = ComparisonHistory()
        self.save_button = QPushButton("Save Output...")
        self.save_button.setToolTip(
            "Save the current comparison as CSV, including both values and "
            "each cell's match status."
        )
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_output)
        self.comparison: Comparison | None = None
        self.status = QLabel("Choose two CSV files to compare.")
        self.status.setToolTip(
            "Shows the comparison totals or explains why a comparison/save failed."
        )

        legend = QLabel(
            '<span style="color:#187a2f">Green: exact match</span> &nbsp; '
            '<span style="color:#a85b00">Orange: within tolerance</span> &nbsp; '
            '<span style="color:#b00020">'
            "Red: different, blank, NaN, zero, or missing row</span>"
        )
        legend.setTextFormat(Qt.TextFormat.RichText)
        legend.setToolTip(
            "Green is exact, orange is within tolerance, and red indicates a "
            "difference, blank, NaN, zero, or missing row."
        )

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self.file1_picker)
        layout.addWidget(self.file2_picker)
        layout.addWidget(self.history)
        settings_row = QHBoxLayout()
        settings_row.addWidget(self.settings, 1)
        settings_row.addWidget(self.save_button)
        layout.addLayout(settings_row)
        layout.addWidget(legend)
        layout.addWidget(self.results, 1)
        layout.addWidget(self.status)
        self.setCentralWidget(content)
        self.settings.compareRequested.connect(self.compare)
        self.history.saveNewRequested.connect(self.save_new_comparison)
        self.history.loadRequested.connect(self.load_saved_file)
        self.history.loadEntryRequested.connect(self.load_saved_comparison)
        self.history.refreshRequested.connect(self.refresh_saved_comparison)
        self.history.updateRequested.connect(self.update_saved_comparison)
        self.history.deleteRequested.connect(self.delete_saved_comparison)
        self.history.reloadRequested.connect(self._refresh_history)
        self._refresh_history()

    def compare(self) -> None:
        self.comparison = None
        self.save_button.setEnabled(False)
        try:
            if not self.file1_picker.path or not self.file2_picker.path:
                raise ValueError("Select both CSV files before comparing.")

            ignored, sort_key, rtol, atol = self.settings.values()
            headers, _ = read_csv(self.file1_picker.path)
            ignored = _resolve_ignored_columns(ignored, headers)
            sort_key = _resolve_sort_key(sort_key, headers)
            result = compare_csv_files(
                self.file1_picker.path,
                self.file2_picker.path,
                ignored,
                sort_key,
                rtol,
                atol,
            )
            self.results.show_result(result)
            self.comparison = result
            self.save_button.setEnabled(True)
            self.status.setText(_summary(result))
        except (OSError, UnicodeError, ValueError, csv.Error) as error:
            self.status.setText(f"Comparison failed: {error}")
            self.results.show_error(str(error))

    def save_new_comparison(self) -> None:
        self.compare()
        if self.comparison is None:
            return
        name, accepted = QInputDialog.getText(
            self, "Save comparison", "Name this comparison:"
        )
        if not accepted:
            return
        name = name.strip()
        if not name:
            self.status.setText("Comparison name cannot be empty.")
            return
        try:
            entry = self._current_history_entry(name)
            saved = self.history_store.create(entry)
            self._refresh_history()
            self.history.select_id(saved["id"])
            self.status.setText(f"Saved comparison '{name}'.")
        except (OSError, ValueError) as error:
            self.status.setText(f"Could not save comparison: {error}")

    def load_saved_comparison(self, entry_id: str) -> None:
        if not entry_id:
            self.status.setText("No saved comparisons yet. Run a comparison, then select Save New.")
            return
        try:
            entry = self.history_store.get(entry_id)
            self._restore_entry_settings(entry)
            self.comparison = comparison_from_entry(entry)
            self.results.show_result(self.comparison)
            self.save_button.setEnabled(True)
            self.history.select_id(entry_id)
            self.status.setText(
                f"Loaded saved snapshot '{entry['name']}'. Use Refresh Sources "
                "to reread the CSV files."
            )
        except (KeyError, OSError, ValueError) as error:
            self.status.setText(f"Could not load saved comparison: {error}")
            self._refresh_history()

    def load_saved_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load saved comparison",
            "",
            "Comparison CSV files (*.csv);;All files (*)",
        )
        if not file_path:
            return
        try:
            result = read_comparison_csv(file_path)
            self.comparison = result
            if result.source_file1 is not None:
                self.file1_picker.path_input.setText(result.source_file1)
            if result.source_file2 is not None:
                self.file2_picker.path_input.setText(result.source_file2)
            self.results.show_result(result)
            self.save_button.setEnabled(True)
            source_note = (
                " Source file paths were restored."
                if result.source_file1 is not None and result.source_file2 is not None
                else " This older export has no source paths; choose the files manually."
            )
            self.status.setText(f"Loaded saved comparison from {file_path}.{source_note}")
        except (OSError, UnicodeError, ValueError, csv.Error) as error:
            self.status.setText(f"Could not load saved comparison: {error}")
            self.results.show_error(str(error))

    def refresh_saved_comparison(self, entry_id: str) -> None:
        if not entry_id:
            self.status.setText("Select a saved comparison before refreshing its source files.")
            return
        try:
            entry = self.history_store.get(entry_id)
            self._restore_entry_settings(entry)
            self.history.select_id(entry_id)
            self.compare()
            if self.comparison is not None:
                self.status.setText(
                    f"Refreshed '{entry['name']}' from its source CSV files. "
                    "Use Update Saved to persist this refreshed snapshot."
                )
        except (KeyError, OSError, ValueError) as error:
            self.status.setText(f"Could not refresh saved comparison: {error}")

    def update_saved_comparison(self, entry_id: str) -> None:
        if not entry_id:
            self.status.setText("Select a saved comparison before updating it.")
            return
        self.compare()
        if self.comparison is None:
            return
        try:
            existing = self.history_store.get(entry_id)
            updated = self.history_store.update(
                entry_id, self._current_history_entry(existing["name"])
            )
            self._refresh_history()
            self.history.select_id(updated["id"])
            self.status.setText(f"Updated saved comparison '{updated['name']}'.")
        except (KeyError, OSError, ValueError) as error:
            self.status.setText(f"Could not update saved comparison: {error}")

    def delete_saved_comparison(self, entry_id: str) -> None:
        if not entry_id:
            self.status.setText("Select a saved comparison before deleting it.")
            return
        try:
            entry = self.history_store.get(entry_id)
            answer = QMessageBox.question(
                self,
                "Delete saved comparison",
                f"Delete '{entry['name']}' from comparison history?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.history_store.delete(entry_id)
            if self.history.selected_id == entry_id:
                self.comparison = None
                self.save_button.setEnabled(False)
                self.results.show_error("")
            self._refresh_history()
            self.status.setText(f"Deleted saved comparison '{entry['name']}'.")
        except (KeyError, OSError, ValueError) as error:
            self.status.setText(f"Could not delete saved comparison: {error}")
            self._refresh_history()

    def _current_history_entry(self, name: str) -> dict:
        ignored, sort_key, rtol, atol = self.settings.values()
        headers, _ = read_csv(self.file1_picker.path)
        ignored = _resolve_ignored_columns(ignored, headers)
        sort_key = _resolve_sort_key(sort_key, headers)
        return create_history_entry(
            name,
            self.file1_picker.path,
            self.file2_picker.path,
            ignored,
            sort_key,
            rtol,
            atol,
            self.comparison,
        )

    def _restore_entry_settings(self, entry: dict) -> None:
        self.file1_picker.path_input.setText(entry["file1"])
        self.file2_picker.path_input.setText(entry["file2"])
        self.settings.ignore_input.setText(", ".join(entry["ignore_columns"]))
        self.settings.sort_input.setText(entry["sort_key"] or "")
        self.settings.rtol_input.setText(str(entry["rtol"]))
        self.settings.atol_input.setText(str(entry["atol"]))

    def _refresh_history(self) -> None:
        try:
            self.history.set_entries(self.history_store.list_entries())
        except (OSError, ValueError) as error:
            self.status.setText(f"Could not read comparison history: {error}")

    def save_output(self) -> None:
        if self.comparison is None:
            self.status.setText("Run a comparison before saving output.")
            return

        left_stem = Path(self.file1_picker.path).stem or "file1"
        right_stem = Path(self.file2_picker.path).stem or "file2"
        suggested_name = f"{left_stem}_vs_{right_stem}_comparison.csv"
        initial_path = str(Path(self.file1_picker.path).parent / suggested_name)
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save comparison output",
            initial_path,
            "CSV files (*.csv);;All files (*)",
        )
        if not output_path:
            return

        if not Path(output_path).suffix:
            output_path += ".csv"
        try:
            write_comparison_csv(
                self.comparison,
                output_path,
                self.file1_picker.path,
                self.file2_picker.path,
            )
            self.status.setText(f"Comparison output saved to {output_path}")
        except (OSError, csv.Error) as error:
            self.status.setText(f"Could not save comparison output: {error}")


def _resolve_ignored_columns(columns: set[str], headers: list[str]) -> set[str]:
    resolved = set()
    for column in columns:
        if column.isdigit():
            index = int(column) - 1
            if index < 0 or index >= len(headers):
                raise ValueError(f"Ignored column number {column} is out of range.")
            resolved.add(headers[index])
        else:
            resolved.add(column)
    return resolved


def _resolve_sort_key(sort_key: str | None, headers: list[str]) -> str | None:
    if sort_key and sort_key.isdigit():
        index = int(sort_key) - 1
        if index < 0 or index >= len(headers):
            raise ValueError("Sort column number is out of range.")
        return headers[index]
    return sort_key


def _summary(result: Comparison) -> str:
    row_note = (
        f" Row counts differ ({result.left_row_count} vs {result.right_row_count})."
        if result.left_row_count != result.right_row_count
        else ""
    )
    return (
        f"Compared {min(result.left_row_count, result.right_row_count)} paired rows; "
        f"{result.counts[GREEN]} exact, {result.counts[ORANGE]} within tolerance, "
        f"{result.counts[RED]} different.{row_note}"
    )


def main() -> None:
    app = QApplication(sys.argv)
    app.setWindowIcon(application_icon())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
