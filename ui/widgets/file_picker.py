from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class CsvFilePicker(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Choose a CSV file")
        self.path_input.setToolTip("Path to the CSV file to include in the comparison.")
        self.setToolTip(f"Select the {label.rstrip(':')} CSV file.")
        file_label = QLabel(label)
        file_label.setToolTip(f"CSV input for {label.rstrip(':')}.")
        browse_button = QPushButton("Browse...")
        browse_button.setToolTip("Browse your computer and choose a CSV file.")
        browse_button.clicked.connect(self._browse)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(file_label)
        layout.addWidget(self.path_input, 1)
        layout.addWidget(browse_button)

    @property
    def path(self) -> str:
        return self.path_input.text().strip()

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a CSV file", "", "CSV files (*.csv);;All files (*)"
        )
        if path:
            self.path_input.setText(path)
