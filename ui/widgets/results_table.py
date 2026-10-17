from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from csv_compare import Comparison, GREEN, ORANGE, RED


class ResultsTableWidget(QWidget):
    _COLORS = {
        GREEN: QColor("#dff2e1"),
        ORANGE: QColor("#ffedcc"),
        RED: QColor("#f8d7da"),
    }

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.setWordWrap(False)
        self.table.setSortingEnabled(False)
        self.table.setToolTip(
            "Side-by-side CSV values. Hover a cell to see its comparison status."
        )
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setToolTip("Details about a comparison or save error.")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.error_label)
        layout.addWidget(self.table, 1)
        self.show_error("")

    def show_result(self, result: Comparison) -> None:
        headers = ["Row"]
        for header in result.headers:
            headers.extend((f"{header} [File 1]", f"{header} [File 2]"))

        self.error_label.hide()
        self.table.show()
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(result.statuses))
        for column, header in enumerate(headers):
            header_item = self.table.horizontalHeaderItem(column)
            if header_item is not None:
                header_item.setToolTip(f"Comparison result column: {header}")

        status_hints = {
            GREEN: "Exact match.",
            ORANGE: "Numeric values match within the configured tolerance.",
            RED: "Values differ, contain a blank/NaN/zero, or a row is missing.",
        }
        for row_index, (left_row, right_row, statuses) in enumerate(
            zip(result.left_rows, result.right_rows, result.statuses)
        ):
            row_item = QTableWidgetItem(str(row_index + 1))
            row_item.setToolTip(f"Compared row {row_index + 1}.")
            self.table.setItem(row_index, 0, row_item)
            for column_index, (left, right, status) in enumerate(
                zip(left_row, right_row, statuses)
            ):
                color = self._COLORS[status]
                for offset, value in enumerate((left, right)):
                    item = QTableWidgetItem(_display_value(value))
                    item.setBackground(color)
                    item.setToolTip(
                        f"{status_hints[status]} "
                        f"File {'1' if offset == 0 else '2'} value: "
                        f"{_display_value(value)}"
                    )
                    self.table.setItem(
                        row_index, 1 + column_index * 2 + offset, item
                    )

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    def show_error(self, message: str) -> None:
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.error_label.setText(message)
        self.error_label.setVisible(bool(message))
        self.table.setVisible(not message)


def _display_value(value: str | None) -> str:
    if value is None:
        return "<missing>"
    return value.replace("\n", "\\n").replace("\r", "\\r")
