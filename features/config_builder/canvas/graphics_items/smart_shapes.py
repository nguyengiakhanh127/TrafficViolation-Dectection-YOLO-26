from PyQt6.QtWidgets import (
    QGraphicsPolygonItem, QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsItem
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QBrush, QColor, QPolygonF

class PolygonEntity(QGraphicsPolygonItem):
    """
    Đối tượng đa giác bao trùm toàn bộ các Node và Edge.
    """
    def __init__(self, nodes, edges, entity_id, parent=None):
        super().__init__(parent)
        self.nodes = nodes
        self.edges = edges
        self.entity_id = entity_id
        
        self.setZValue(0)
        self.setPen(QPen(Qt.GlobalColor.transparent))
        
        self.default_brush = QBrush(Qt.GlobalColor.transparent)
        self.highlight_brush = QBrush(QColor(255, 255, 0, 80))
        
        self.setBrush(self.default_brush)
        self.update_shape()

    def update_shape(self):
        polygon = QPolygonF()
        for node in self.nodes:
            polygon.append(node.sceneBoundingRect().center())
        self.setPolygon(polygon)
        
    def set_highlight(self, is_highlighted: bool):
        self.setBrush(self.highlight_brush if is_highlighted else self.default_brush)
        
    def highlight_sub_edge(self, edge_index: int, is_highlighted: bool):
        if 0 <= edge_index < len(self.edges):
            self.edges[edge_index].set_highlight(is_highlighted)

class EdgeItem(QGraphicsLineItem):
    """Cạnh nối 2 đỉnh. Tự động thay đổi khi đỉnh bị kéo thả."""
    def __init__(self, start_node, end_node, parent=None):
        super().__init__(parent)
        self.start_node = start_node
        self.end_node = end_node

        self.default_pen = QPen(QColor(0, 255, 255), 2)
        self.highlight_pen = QPen(QColor(255, 255, 0), 4)

        self.setPen(QPen(QColor(0, 255, 255), 2))
        self.setZValue(1)
        self.update_position()

    def update_position(self):
        self.setLine(self.start_node.sceneBoundingRect().center().x(),
                     self.start_node.sceneBoundingRect().center().y(),
                     self.end_node.sceneBoundingRect().center().x(),
                     self.end_node.sceneBoundingRect().center().y())
                     
    def set_highlight(self, is_highlighted: bool):
        self.setPen(self.highlight_pen if is_highlighted else self.default_pen)
        self.setZValue(3 if is_highlighted else 1)

class NodeItem(QGraphicsEllipseItem):
    """Đỉnh đa giác. Có thể kéo thả, có thể tái sử dụng."""
    def __init__(self, x, y, parent=None):
        super().__init__(x - 5, y - 5, 10, 10, parent)
        self.setBrush(QBrush(QColor(255, 0, 0)))
        self.setPen(QPen(Qt.GlobalColor.transparent))
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(2)
        
        self.connected_edges = []
        self.parent_polygon: PolygonEntity = None

    def add_edge(self, edge: EdgeItem):
        self.connected_edges.append(edge)

    def remove_edge(self, edge: EdgeItem):
        if edge in self.connected_edges:
            self.connected_edges.remove(edge)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.connected_edges:
                edge.update_position()
            if self.parent_polygon:
                self.parent_polygon.update_shape()
        return super().itemChange(change, value)
    
class BboxEntity(QGraphicsRectItem):
    """Đối tượng hộp giới hạn dùng cho Đèn tín hiệu giao thông"""
    def __init__(self, rect, entity_id, parent=None):
        super().__init__(rect, parent)
        self.entity_id = entity_id
        
        self.default_pen = QPen(QColor(255, 0, 0), 2)
        self.highlight_pen = QPen(QColor(255, 255, 0), 4)
        
        self.default_brush = QBrush(QColor(255, 0, 0, 50))
        self.highlight_brush = QBrush(QColor(255, 0, 0, 120))
        
        self.setPen(self.default_pen)
        self.setBrush(self.default_brush)
    
    def set_highlight(self, is_highlighted: bool):
        self.setPen(self.highlight_pen if is_highlighted else self.default_pen)
        self.setBrush(self.highlight_brush if is_highlighted else self.default_brush)
        self.setZValue(3 if is_highlighted else 0)

class LineEntity(QGraphicsLineItem):
    """Đối tượng đường thẳng. Tự động co giãn khi đỉnh đầu mút bị kéo thả."""
    def __init__(self, start_node, end_node, entity_id, parent=None):
        super().__init__(parent)
        self.start_node = start_node
        self.end_node = end_node
        self.entity_id = entity_id
        
        self.default_pen = QPen(QColor(255, 165, 0), 2)
        self.highlight_pen = QPen(QColor(255, 255, 0), 4)
        
        self.setPen(self.default_pen)
        self.setZValue(1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        
        self.update_position()

    def update_position(self):
        self.setLine(self.start_node.sceneBoundingRect().center().x(),
                     self.start_node.sceneBoundingRect().center().y(),
                     self.end_node.sceneBoundingRect().center().x(),
                     self.end_node.sceneBoundingRect().center().y())
                     
    def set_highlight(self, is_highlighted: bool):
        self.setPen(self.highlight_pen if is_highlighted else self.default_pen)
        self.setZValue(3 if is_highlighted else 1)