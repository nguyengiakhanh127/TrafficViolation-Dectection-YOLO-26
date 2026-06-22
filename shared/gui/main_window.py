import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ==============================================================================

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QStackedWidget, QButtonGroup, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QCursor, QCloseEvent

from shared.gui.shared_components.collapsible_sidebar import CollapsibleSidebar
from shared.gui.shared_components.custom_titlebar import CustomTitleBar
from shared.utils import paths
from shared.database.database_service import DatabaseService

from features.config_builder.builder_view import ConfigBuilderView
from features.violation_reviewer.reviewer_view import ReviewerView
from features.violation_reviewer.reviewer_controller import ReviewerController

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Hệ thống phát hiện vi phạm giao thông AI")
        self.resize(1280, 720)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.db_service = DatabaseService(port=3306)

        self._setup_ui()
        self._load_stylesheet()

    def _setup_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setObjectName("MainWrapper")
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        self.main_layout.addWidget(self.title_bar)

        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        
        self._setup_sidebar()
        self._setup_workspace()

        self.main_layout.addLayout(self.body_layout)

    def _setup_sidebar(self):
        self.sidebar_widget = CollapsibleSidebar(self)
        
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(0, 20, 0, 0)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.tab_group = QButtonGroup(self)

        self.btn_tab_config = self._create_sidebar_btn("   Cấu hình", "settings.png")
        self.btn_tab_config.setChecked(True)
        self.tab_group.addButton(self.btn_tab_config, 0)

        self.btn_tab_review = self._create_sidebar_btn("   Sự kiện", "review.png") 
        self.tab_group.addButton(self.btn_tab_review, 1)

        sidebar_layout.addWidget(self.btn_tab_config)
        sidebar_layout.addWidget(self.btn_tab_review)

        self.body_layout.addWidget(self.sidebar_widget)

    def _create_sidebar_btn(self, text: str, icon_name: str) -> QPushButton:
        btn = QPushButton(text)
        icon_path = os.path.join(paths.ICONS_DIR, icon_name)
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
        btn.setIconSize(QSize(22, 22))
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setCheckable(True)
        return btn

    def _setup_workspace(self):
        self.stacked_workspace = QStackedWidget()
        
        self.page_config = ConfigBuilderView(self.db_service)
        self.page_config.get_toolbar().toggle_fullscreen.connect(self._toggle_fullscreen)

        self.page_reviewer = ReviewerView()
        self.reviewer_controller = ReviewerController(self.page_reviewer, self.db_service)

        self.stacked_workspace.addWidget(self.page_config)
        self.stacked_workspace.addWidget(self.page_reviewer)

        self.tab_group.idToggled.connect(self._change_tab)
        
        self.body_layout.addWidget(self.stacked_workspace, stretch=1)

    def _change_tab(self, tab_id, checked):
        if checked:
            self.stacked_workspace.setCurrentIndex(tab_id)

    def _toggle_fullscreen(self):
        self.is_focus_mode = getattr(self, 'is_focus_mode', False)
        
        if not self.is_focus_mode:
            self.title_bar.hide()
            self.sidebar_widget.hide()
            self.page_config.panel.hide() 
            self.showMaximized()
            self.is_focus_mode = True
        else:
            self.title_bar.show()
            self.sidebar_widget.show()
            self.page_config.panel.show()
            self.showNormal()
            self.is_focus_mode = False

    def _load_stylesheet(self):
        qss_path = os.path.join(current_dir, "app_style.qss")
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Không thể tải CSS: {e}")

    def closeEvent(self, event: QCloseEvent):
        """
        Bắt sự kiện khi người dùng bấm dấu X hoặc ấn tắt phần mềm.
        Đảm bảo dọn dẹp các Thread ngầm và lưu nốt bằng chứng xuống đĩa.
        """
        if hasattr(self.page_config, 'controller'):
            video_thread = self.page_config.controller.video_thread
            if video_thread and video_thread.is_playing:
                reply = QMessageBox.question(
                    self, 'Cảnh báo',
                    "Hệ thống AI đang giám sát. Bạn có chắc chắn muốn thoát?\n",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self._shutdown_services(video_thread)
                    event.accept()
                else:
                    event.ignore()
                return

        self._shutdown_services(None)
        event.accept()

    def _shutdown_services(self, video_thread):
        print("Hệ thống: đang tiến hành dọn dẹp hệ thống trước khi thoát...")
        
        if video_thread:
            video_thread.stop()
            video_thread.wait()
            
        if hasattr(self.page_config, 'controller'):
            violation_service = self.page_config.controller.violation_service
            if hasattr(violation_service, 'video_buffer'):
                violation_service.video_buffer.clear()
            
            if hasattr(violation_service, 'evidence_generator'):
                violation_service.evidence_generator.shutdown()
                
        print("Hệ thống: Ứng dụng đã được đóng an toàn.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
