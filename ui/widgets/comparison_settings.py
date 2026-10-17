from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ComparisonSettingsWidget(QWidget):
    compareRequested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.ignore_input = QLineEdit("date, version")
        self.ignore_input.setToolTip(
            "Columns excluded from comparison. Enter header names or 1-based "
            "column numbers, separated by commas."
        )
        self.sort_input = QLineEdit()
        self.sort_input.setToolTip(
            "Optional sort key applied to both files before comparing rows. "
            "Enter a header name or 1-based column number."
        )
        self.rtol_input = QLineEdit("0.001")
        self.rtol_input.setToolTip(
            "Relative tolerance for numeric values. Larger values allow a "
            "larger difference proportional to the compared values."
        )
        self.atol_input = QLineEdit("0.00001")
        self.atol_input.setToolTip(
            "Absolute tolerance for numeric values. This is a fixed minimum "
            "difference allowance."
        )
        self.compare_button = QPushButton("Compare")
        self.compare_button.setToolTip(
            "Compare the selected CSV files using the settings above."
        )
        self.compare_button.setDefault(True)
        self.compare_button.clicked.connect(self.compareRequested)

        form = QFormLayout()
        ignore_label = QLabel("Ignore columns (names or numbers):")
        ignore_label.setToolTip(self.ignore_input.toolTip())
        sort_label = QLabel("Sort column (name or number):")
        sort_label.setToolTip(self.sort_input.toolTip())
        form.addRow(ignore_label, self.ignore_input)
        form.addRow(sort_label, self.sort_input)

        tolerance_row = QHBoxLayout()
        rtol_label = QLabel("rtol:")
        rtol_label.setToolTip(self.rtol_input.toolTip())
        tolerance_row.addWidget(rtol_label)
        tolerance_row.addWidget(self.rtol_input)
        atol_label = QLabel("atol:")
        atol_label.setToolTip(self.atol_input.toolTip())
        tolerance_row.addWidget(atol_label)
        tolerance_row.addWidget(self.atol_input)
        tolerance_row.addWidget(self.compare_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(tolerance_row)

    def values(self) -> tuple[set[str], str | None, float, float]:
        ignored = {
            column.strip()
            for column in self.ignore_input.text().split(",")
            if column.strip()
        }
        sort_key = self.sort_input.text().strip() or None
        return ignored, sort_key, float(self.rtol_input.text()), float(
            self.atol_input.text()
        )
