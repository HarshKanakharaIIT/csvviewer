from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QWidget


class HistoryPanel(QWidget):
    saveNewRequested = Signal()
    loadRequested = Signal()
    loadEntryRequested = Signal(str)
    refreshRequested = Signal(str)
    updateRequested = Signal(str)
    deleteRequested = Signal(str)
    reloadRequested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.entries = QComboBox()
        self.entries.setToolTip("Choose a saved comparison to load, refresh, update, or delete.")
        self.entries.setMinimumContentsLength(24)
        self.entries.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )

        self.save_button = QPushButton("Save New")
        self.save_button.setToolTip("Save the current comparison as a new history entry.")
        self.reload_button = QPushButton("Reload List")
        self.reload_button.setToolTip(
            "Reload saved comparisons from the local history file."
        )
        self.load_button = QPushButton("Load Saved")
        self.load_button.setToolTip(
            "Choose a comparison CSV previously exported with Save Output."
        )
        self.load_button.clicked.connect(self.loadRequested)
        self.refresh_button = QPushButton("Refresh Sources")
        self.refresh_button.setToolTip(
            "Reread the selected entry's CSV files and show a fresh comparison."
        )
        self.update_button = QPushButton("Update Saved")
        self.update_button.setToolTip(
            "Compare the current inputs/settings and replace the selected history entry."
        )
        self.delete_button = QPushButton("Delete")
        self.delete_button.setToolTip("Permanently delete the selected history entry.")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.entries, 1)
        layout.addWidget(self.save_button)
        layout.addWidget(self.reload_button)
        layout.addWidget(self.load_button)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.update_button)
        layout.addWidget(self.delete_button)

        self.save_button.clicked.connect(self.saveNewRequested)
        self.reload_button.clicked.connect(self.reloadRequested)
        self.refresh_button.clicked.connect(self._emit_selected(self.refreshRequested))
        self.update_button.clicked.connect(self._emit_selected(self.updateRequested))
        self.delete_button.clicked.connect(self._emit_selected(self.deleteRequested))
        self.entries.activated.connect(self._load_activated)
        self.entries.currentIndexChanged.connect(self._update_buttons)
        self._update_buttons()

    @property
    def selected_id(self) -> str | None:
        entry_id = self.entries.currentData()
        return str(entry_id) if entry_id else None

    def set_entries(self, entries: list[dict]) -> None:
        selected_id = self.selected_id
        self.entries.blockSignals(True)
        self.entries.clear()
        for entry in entries:
            self.entries.addItem(entry["name"], entry["id"])
        if not entries:
            self.entries.addItem("No saved comparisons", None)
        if selected_id:
            selected_index = self.entries.findData(selected_id)
            if selected_index >= 0:
                self.entries.setCurrentIndex(selected_index)
        self.entries.blockSignals(False)
        self._update_buttons()

    def select_id(self, entry_id: str | None) -> None:
        if entry_id:
            index = self.entries.findData(entry_id)
            if index >= 0:
                self.entries.setCurrentIndex(index)
        self._update_buttons()

    def _emit_selected(self, signal: Signal):
        def emit() -> None:
            entry_id = self.selected_id
            signal.emit(entry_id or "")

        return emit

    def _load_activated(self, _index: int) -> None:
        entry_id = self.selected_id
        if entry_id:
            self.loadEntryRequested.emit(entry_id)

    def _update_buttons(self, *_args) -> None:
        self.save_button.setEnabled(True)
        self.reload_button.setEnabled(True)
        self.load_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.update_button.setEnabled(True)
        self.delete_button.setEnabled(True)
