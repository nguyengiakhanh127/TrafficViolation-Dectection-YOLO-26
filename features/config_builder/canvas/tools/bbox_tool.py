import uuid
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent, QPen, QColor
from features.config_builder.canvas.tools.base_tool import BaseTool
from features.config_builder.canvas.graphics_items.smart_shapes import BboxEntity

class BboxTool(BaseTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.drawing_bbox = None
        self.bbox_start_pos = None

    def activate(self):
        self.canvas.viewport().setCursor(Qt.CursorShape.CrossCursor)

    def mousePressEvent(self, event: QMouseEvent, scene_pos):
        if event.button() != Qt.MouseButton.LeftButton: return

        self.bbox_start_pos = scene_pos
        
        if self.drawing_bbox is not None:
            self.scene.removeItem(self.drawing_bbox)

        self.drawing_bbox = self.scene.addRect(
            scene_pos.x(), scene_pos.y(), 0, 0, 
            QPen(QColor(255, 0, 0), 2)
        )

    def mouseMoveEvent(self, event: QMouseEvent, scene_pos):
        if self.bbox_start_pos and self.drawing_bbox:
            x = min(self.bbox_start_pos.x(), scene_pos.x())
            y = min(self.bbox_start_pos.y(), scene_pos.y())
            w = abs(scene_pos.x() - self.bbox_start_pos.x())
            h = abs(scene_pos.y() - self.bbox_start_pos.y())
            self.drawing_bbox.setRect(x, y, w, h)

    def mouseReleaseEvent(self, event: QMouseEvent, scene_pos):
        if event.button() != Qt.MouseButton.LeftButton: return
        
        if self.drawing_bbox and self.bbox_start_pos:
            rect = self.drawing_bbox.rect()
            
            if rect.width() > 5 and rect.height() > 5:
                entity_id = f"LIGHT_{str(uuid.uuid4())[:8].upper()}"
                
                bbox_entity = BboxEntity(rect, entity_id)
                self.scene.addItem(bbox_entity)
                
                print(f"[DRAW] Đã tạo Bbox Đèn ID: {entity_id}")
                
                self.canvas.bbox_completed.emit((entity_id, bbox_entity))

            self.cancel_drawing()
            
            self.canvas.set_mode("NONE")

    def cancel_drawing(self):
        if self.drawing_bbox:
            self.scene.removeItem(self.drawing_bbox)
            self.drawing_bbox = None
        self.bbox_start_pos = None