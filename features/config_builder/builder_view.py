from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout

from features.config_builder.canvas.canvas_widget import ConfigCanvas
from features.config_builder.canvas.canvas_toolbar import CanvasToolbar
from features.config_builder.panels.properties_panel import PropertiesPanel
from features.config_builder.builder_controller import BuilderController

class ConfigBuilderView(QWidget):
    def __init__(self, db_service, parent=None):
        super().__init__(parent)
        self.db_service = db_service
        self._setup_ui()
        self._init_controller()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.canvas = ConfigCanvas()
        self.toolbar = CanvasToolbar()
        
        self.toolbar.mode_changed.connect(self.canvas.set_mode)
        self.toolbar.zoom_changed.connect(self.canvas.set_zoom)
        self.canvas.zoom_level_changed.connect(self.toolbar.update_zoom_from_canvas)
        self.toolbar.request_fit_view.connect(self.canvas.recenter_and_fit)

        left_layout.addWidget(self.canvas, stretch=1)
        left_layout.addWidget(self.toolbar)
        
        self.panel = PropertiesPanel()
        
        main_layout.addWidget(left_col, stretch=1)
        main_layout.addWidget(self.panel)

    def _init_controller(self):
        self.controller = BuilderController(
            self.canvas, 
            self.panel, 
            self.toolbar, 
            self.db_service 
        )

    def load_test_image(self, filepath: str):
        self.canvas.load_image(filepath)
        
    def get_toolbar(self):
        return self.toolbar
