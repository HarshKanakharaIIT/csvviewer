import tempfile
import unittest
import os
from unittest.mock import patch
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from comparison_history import (
    ComparisonHistory,
    comparison_from_entry,
    create_history_entry,
    _default_history_path,
)
from csv_compare import (
    Comparison,
    GREEN,
    ORANGE,
    RED,
    compare_csv_files,
    compare_values,
    read_comparison_csv,
    write_comparison_csv,
)
from ui.main_window import MainWindow


class CompareValuesTests(unittest.TestCase):
    def test_color_categories(self):
        self.assertEqual(compare_values("12", "12.0", 1e-3, 1e-5), GREEN)
        self.assertEqual(compare_values("12", "12.001", 1e-3, 1e-5), ORANGE)
        self.assertEqual(compare_values("12", "14", 1e-3, 1e-5), RED)
        self.assertEqual(compare_values("", "text", 1e-3, 1e-5), RED)
        self.assertEqual(compare_values("NaN", "NaN", 1e-3, 1e-5), RED)
        self.assertEqual(compare_values("0", "0", 1e-3, 1e-5), RED)
        self.assertEqual(compare_values("text", "text", 1e-3, 1e-5), GREEN)


class CompareFilesTests(unittest.TestCase):
    def test_sorting_ignoring_and_row_count_difference(self):
        with tempfile.TemporaryDirectory() as directory:
            left = Path(directory) / "left.csv"
            right = Path(directory) / "right.csv"
            left.write_text("id,value,date\nb,2,old\na,1,old\n", encoding="utf-8")
            right.write_text(
                "id,value,date\na,1.000001,new\nb,2, new\nc,3,new\n",
                encoding="utf-8",
            )
            result = compare_csv_files(
                str(left), str(right), {"date"}, "id", rtol=0, atol=0.00001
            )

        self.assertEqual(result.headers, ["id", "value"])
        self.assertEqual(result.left_rows[0], ["a", "1"])
        self.assertEqual(result.statuses[0], [GREEN, ORANGE])
        self.assertEqual(result.left_rows[-1], [None, None])
        self.assertEqual(result.counts[RED], 2)

    def test_rejects_different_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            left = Path(directory) / "left.csv"
            right = Path(directory) / "right.csv"
            left.write_text("a,b\n1,2\n", encoding="utf-8")
            right.write_text("b,a\n2,1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "same column names"):
                compare_csv_files(str(left), str(right))

    def test_writes_comparison_output_with_cell_statuses(self):
        with tempfile.TemporaryDirectory() as directory:
            left = Path(directory) / "left.csv"
            right = Path(directory) / "right.csv"
            output = Path(directory) / "comparison.csv"
            left.write_text("value\n1\n2\n", encoding="utf-8")
            right.write_text("value\n1.000001\n3\n", encoding="utf-8")
            result = compare_csv_files(
                str(left), str(right), ignore_columns=set(), rtol=0, atol=0.00001
            )

            write_comparison_csv(result, output, str(left), str(right))
            lines = output.read_text(encoding="utf-8").splitlines()

        self.assertEqual(lines[0], "# CSV Compare Export,1")
        self.assertEqual(lines[1], f"# Source File 1,{left}")
        self.assertEqual(lines[2], f"# Source File 2,{right}")
        self.assertEqual(
            lines[3], "Row,value [File 1],value [File 2],value [Status]"
        )
        self.assertEqual(lines[4], "1,1,1.000001,close")
        self.assertEqual(lines[5], "2,2,3,different")

    def test_reads_exported_comparison_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            left = Path(directory) / "left.csv"
            right = Path(directory) / "right.csv"
            output = Path(directory) / "comparison.csv"
            left.write_text("value,label\n1,same\n2,old\n", encoding="utf-8")
            right.write_text(
                "value,label\n1.000001,same\n3,new\n", encoding="utf-8"
            )
            result = compare_csv_files(
                str(left), str(right), set(), rtol=0, atol=0.00001
            )
            write_comparison_csv(result, output, str(left), str(right))

            loaded = read_comparison_csv(output)

        self.assertEqual(loaded.headers, ["value", "label"])
        self.assertEqual(loaded.left_rows, [["1", "same"], ["2", "old"]])
        self.assertEqual(loaded.right_rows, [["1.000001", "same"], ["3", "new"]])
        self.assertEqual(loaded.statuses, [[ORANGE, GREEN], [RED, RED]])
        self.assertEqual(loaded.counts, {GREEN: 1, ORANGE: 1, RED: 2})
        self.assertEqual(loaded.source_file1, str(left))
        self.assertEqual(loaded.source_file2, str(right))

    def test_rejects_regular_csv_as_saved_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            source.write_text("value\n1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not a saved comparison"):
                read_comparison_csv(source)


class ComparisonHistoryTests(unittest.TestCase):
    def test_history_path_includes_history_directory(self):
        self.assertEqual(
            _default_history_path(),
            Path(__file__).resolve().parent
            / "history"
            / "comparison_history.json",
        )

    def test_frozen_history_paths_are_platform_specific(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("comparison_history.sys.frozen", True, create=True):
                with (
                    patch("comparison_history.sys.platform", "win32"),
                    patch.dict(os.environ, {"LOCALAPPDATA": str(root)}),
                ):
                    self.assertEqual(
                        _default_history_path(),
                        root / "csvviewer" / "history" / "comparison_history.json",
                    )

                with (
                    patch("comparison_history.sys.platform", "darwin"),
                    patch("comparison_history.Path.home", return_value=root),
                ):
                    self.assertEqual(
                        _default_history_path(),
                        root
                        / "Library"
                        / "Application Support"
                        / "csvviewer"
                        / "history"
                        / "comparison_history.json",
                    )

                with (
                    patch("comparison_history.sys.platform", "linux"),
                    patch.dict(os.environ, {"XDG_DATA_HOME": str(root)}),
                ):
                    self.assertEqual(
                        _default_history_path(),
                        root / "csvviewer" / "history" / "comparison_history.json",
                    )

    def test_create_read_update_delete_snapshot(self):
        comparison = Comparison(
            headers=["value"],
            left_rows=[["1"]],
            right_rows=[["1.000001"]],
            statuses=[[ORANGE]],
            counts={GREEN: 0, ORANGE: 1, RED: 0},
            left_row_count=1,
            right_row_count=1,
        )
        entry_data = create_history_entry(
            "Example",
            "left.csv",
            "right.csv",
            {"date"},
            "id",
            0.001,
            0.00001,
            comparison,
        )

        with tempfile.TemporaryDirectory() as directory:
            store = ComparisonHistory(Path(directory) / "history.json")
            created = store.create(entry_data)
            self.assertEqual(store.get(created["id"])["name"], "Example")
            self.assertEqual(
                comparison_from_entry(store.get(created["id"])).statuses,
                [[ORANGE]],
            )

            updated = store.update(created["id"], {**entry_data, "name": "Renamed"})
            self.assertEqual(updated["created_at"], created["created_at"])
            self.assertEqual(store.get(created["id"])["name"], "Renamed")

            store.delete(created["id"])
            self.assertEqual(store.list_entries(), [])
            with self.assertRaises(KeyError):
                store.get(created["id"])

    def test_migrates_legacy_history_into_history_folder(self):
        comparison = Comparison(
            headers=["value"],
            left_rows=[["1"]],
            right_rows=[["1"]],
            statuses=[[GREEN]],
            counts={GREEN: 1, ORANGE: 0, RED: 0},
            left_row_count=1,
            right_row_count=1,
        )
        entry_data = create_history_entry(
            "Legacy",
            "left.csv",
            "right.csv",
            set(),
            None,
            0.001,
            0.00001,
            comparison,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / ".csv_compare_history.json"
            destination = root / "history" / "comparison_history.json"
            ComparisonHistory(legacy).create(entry_data)

            store = ComparisonHistory(destination, legacy)

            self.assertFalse(legacy.exists())
            self.assertTrue(destination.is_file())
            self.assertEqual(store.list_entries()[0]["name"], "Legacy")

    def test_history_ui_create_load_refresh_update_delete(self):
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left.csv"
            right = root / "right.csv"
            left.write_text("value\n1\n", encoding="utf-8")
            right.write_text("value\n1\n", encoding="utf-8")

            window = MainWindow()
            window.history_store = ComparisonHistory(root / "history.json")
            window.history.set_entries([])
            self.assertTrue(window.history.load_button.isEnabled())
            self.assertTrue(window.history.refresh_button.isEnabled())
            self.assertTrue(window.history.update_button.isEnabled())
            self.assertTrue(window.history.delete_button.isEnabled())
            self.assertTrue(window.history.save_button.isEnabled())
            with patch("ui.main_window.QFileDialog.getOpenFileName", return_value=("", "")):
                window.history.load_button.click()
            window.history.reload_button.click()
            window.file1_picker.path_input.setText(str(left))
            window.file2_picker.path_input.setText(str(right))
            window.settings.ignore_input.setText("")
            window.compare()

            entry_data = create_history_entry(
                "Initial",
                str(left),
                str(right),
                set(),
                None,
                0.001,
                0.00001,
                window.comparison,
            )
            saved = window.history_store.create(entry_data)
            window._refresh_history()
            window.history.select_id(saved["id"])

            loaded_ids = []
            window.history.loadEntryRequested.connect(loaded_ids.append)
            window.history.entries.activated.emit(window.history.entries.currentIndex())
            self.assertEqual(loaded_ids, [saved["id"]])

            window.history.entries.activated.emit(window.history.entries.currentIndex())
            self.assertIn("Loaded saved snapshot", window.status.text())
            window.history.refresh_button.click()
            self.assertIn("Refreshed", window.status.text())
            window.history.update_button.click()
            self.assertIn("Updated saved comparison", window.status.text())

            with patch(
                "ui.main_window.QMessageBox.question",
                return_value=QMessageBox.StandardButton.Yes,
            ):
                window.history.delete_button.click()
            self.assertEqual(window.history_store.list_entries(), [])
            window.close()
            app.processEvents()

    def test_load_saved_button_imports_exported_comparison(self):
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source1 = root / "left.csv"
            source2 = root / "right.csv"
            saved_csv = root / "saved_comparison.csv"
            source1.write_text("value\n1\n", encoding="utf-8")
            source2.write_text("value\n1.000001\n", encoding="utf-8")
            comparison = compare_csv_files(
                str(source1), str(source2), set(), rtol=0, atol=0.00001
            )
            write_comparison_csv(comparison, saved_csv, str(source1), str(source2))

            window = MainWindow()
            with patch(
                "ui.main_window.QFileDialog.getOpenFileName",
                return_value=(str(saved_csv), "CSV files (*.csv)"),
            ):
                window.history.load_button.click()

            self.assertEqual(window.comparison.statuses, [[ORANGE]])
            self.assertEqual(window.results.table.rowCount(), 1)
            self.assertTrue(window.save_button.isEnabled())
            self.assertEqual(window.file1_picker.path, str(source1))
            self.assertEqual(window.file2_picker.path, str(source2))
            self.assertIn("Loaded saved comparison", window.status.text())
            window.close()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
