from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PyQt6.QtCore import Qt

from features.violation_reviewer.components.filter_panel import FilterPanel
from features.violation_reviewer.components.data_table import DataTableWidget
from features.violation_reviewer.components.evidence_viewer import EvidenceViewer

class ReviewerView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ReviewerView")

        self.filter_panel = FilterPanel()
        self.data_table = DataTableWidget()
        self.evidence_viewer = EvidenceViewer()
        
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        main_layout.addWidget(self.filter_panel)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.data_table)
        splitter.addWidget(self.evidence_viewer)

        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)

        main_layout.addWidget(splitter, stretch=1) 
