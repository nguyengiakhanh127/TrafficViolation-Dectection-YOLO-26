from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty, QEvent

class CollapsibleSidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SideBar")
        
        self.min_width = 55   
        self.max_width = 200  
        
        self.setFixedWidth(self.min_width) #

        self.animation = QPropertyAnimation(self, b"sidebarWidth")
        self.animation.setDuration(200) 
        self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)

    # =========================================================================
    # ĐỊNH NGHĨA THUỘC TÍNH TÙY CHỈNH ĐỂ PYQT6 CÓ THỂ ANIMATE CHIỀU RỘNG
    # =========================================================================
    @pyqtProperty(int)
    def sidebarWidth(self):
        return self.width()

    @sidebarWidth.setter
    def sidebarWidth(self, width):
        self.setFixedWidth(width)

    # =========================================================================
    # BẮT SỰ KIỆN CHUỘT (HOVER EVENTS)
    # =========================================================================
    def enterEvent(self, event):
        """Khi người dùng rê chuột vào Sidebar -> Mở rộng"""
        self.animation.stop()
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(self.max_width)
        self.animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Khi người dùng đưa chuột ra khỏi Sidebar -> Tự động thu nhỏ"""
        self.animation.stop()
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(self.min_width)
        self.animation.start()
        super().leaveEvent(event)