import os
import numpy as np
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap, QPainter, QWheelEvent, QMouseEvent, QTransform, QImage, QBrush, QColor

from features.config_builder.services.ai_overlay_manager import AIOverlayManager

from features.config_builder.canvas.tools.polygon_tool import PolygonTool
from features.config_builder.canvas.tools.bbox_tool import BboxTool
from features.config_builder.canvas.tools.line_tool import LineTool
 
from features.config_builder.canvas.graphics_items.smart_shapes import PolygonEntity, BboxEntity, LineEntity 

class ConfigCanvas(QGraphicsView):

    zoom_level_changed = pyqtSignal(int)
    polygon_completed = pyqtSignal(tuple) 
    bbox_completed = pyqtSignal(tuple)
    line_completed = pyqtSignal(tuple)
    item_deleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setBackgroundBrush(QBrush(QColor(20, 20, 22))) 

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        
        self.image_item: QGraphicsPixmapItem = None
        self.current_zoom = 100
        self.all_nodes = [] 
        
        self.ai_manager = AIOverlayManager(self.scene)

        self.tools = {
            "DRAW_POLYGON": PolygonTool(self),
            "DRAW_BBOX": BboxTool(self), 
            "DRAW_LINE": LineTool(self)    
        }
        self.active_tool = None

    def load_image(self, filepath: str):
        if not os.path.exists(filepath): return
        pixmap = QPixmap(filepath)
        if self.image_item: self.scene.removeItem(self.image_item)
            
        self.image_item = self.scene.addPixmap(pixmap)
        self.image_item.setZValue(-1)
        self.scene.setSceneRect(self.image_item.boundingRect())
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def set_mode(self, mode: str):
        if self.active_tool:
            self.active_tool.deactivate()

        self.active_tool = self.tools.get(mode)

        if self.active_tool:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.active_tool.activate()
        elif mode == "ZOOM":
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.viewport().unsetCursor() 
        else: # "NONE"
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.image_item: return
        scene_pos = self.mapToScene(event.pos())
        
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            fake_event = QMouseEvent(event.type(), event.pos(), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, event.modifiers())
            super().mousePressEvent(fake_event)
            return

        if event.button() == Qt.MouseButton.LeftButton and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            super().mousePressEvent(event)
            return
        
        if self.active_tool:
            self.active_tool.mousePressEvent(event, scene_pos)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        super().mouseMoveEvent(event)
        scene_pos = self.mapToScene(event.pos())
        if self.active_tool:
            self.active_tool.mouseMoveEvent(event, scene_pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            fake_event = QMouseEvent(event.type(), event.pos(), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, event.modifiers())
            super().mouseReleaseEvent(fake_event)
            return

        scene_pos = self.mapToScene(event.pos())
        if self.active_tool:
            self.active_tool.mouseReleaseEvent(event, scene_pos)
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            selected_items = self.scene.selectedItems()
            for item in selected_items:
                if isinstance(item, LineEntity):
                    entity_id = item.entity_id
                    item.start_node.remove_edge(item)
                    item.end_node.remove_edge(item)
                    for node in [item.start_node, item.end_node]:
                        if not node.connected_edges:
                            self.scene.removeItem(node)
                            if node in self.all_nodes: self.all_nodes.remove(node)
                    self.scene.removeItem(item)
                    self.item_deleted.emit(entity_id) 

                if isinstance(item, PolygonEntity):
                    entity_id = item.entity_id
                    for edge in item.edges:
                        self.scene.removeItem(edge)
                    for node in item.nodes:
                        self.scene.removeItem(node)
                        if node in self.all_nodes: self.all_nodes.remove(node)
                    self.scene.removeItem(item)
                    self.item_deleted.emit(entity_id)

                if isinstance(item, BboxEntity):
                    entity_id = item.entity_id
                    self.scene.removeItem(item)
                    self.item_deleted.emit(entity_id)
            return

        if self.active_tool:
            self.active_tool.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if self.active_tool: return 
        zoom_step = 10 
        if event.angleDelta().y() > 0: self.current_zoom = min(500, self.current_zoom + zoom_step)
        else: self.current_zoom = max(10, self.current_zoom - zoom_step)
        self.set_zoom(self.current_zoom)
        self.zoom_level_changed.emit(self.current_zoom)
        event.accept()

    def set_zoom(self, zoom_percent: int):
        self.current_zoom = zoom_percent
        scale_factor = zoom_percent / 100.0
        transform = QTransform()
        transform.scale(scale_factor, scale_factor)
        self.setTransform(transform)          

    def set_frame(self, frame_np: np.ndarray, vehicles_list: list = None):
        if frame_np is None:
            self.ai_manager.clear_all()
            return
        
        if vehicles_list is None:
            vehicles_list = []
        
        frame_rgb = frame_np[:, :, ::-1] 
        h, w, ch = frame_rgb.shape
        q_image = QImage(frame_rgb.tobytes(), w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)

        if self.image_item is None:
            self.image_item = self.scene.addPixmap(pixmap)
            self.image_item.setZValue(-1)
            self.scene.setSceneRect(self.image_item.boundingRect())
        else:
            self.image_item.setPixmap(pixmap)
        
        if self.active_tool is None:
            self.ai_manager.sync_ai_visuals(vehicles_list)
        else:
            self.ai_manager.clear_all()

    @pyqtSlot()
    def recenter_and_fit(self):
        if self.image_item is None: return
        self.resetTransform()
        img_rect = self.image_item.boundingRect()
        self.scene.setSceneRect(img_rect)
        self.fitInView(img_rect, Qt.AspectRatioMode.KeepAspectRatio)
        self.current_zoom = int(self.transform().m11() * 100)
        self.zoom_level_changed.emit(self.current_zoom)

    def _cancel_drawing(self):
        if self.active_tool:
            self.active_tool.cancel_drawing()