import numpy as np
import math
from shared.geometry.primitives import Vertex, Vector2D
from shared.geometry.shapes import Edge

class SpatialMath:
    @staticmethod
    def calculate_distance(v1: Vertex, v2: Vertex) -> float:
        return math.hypot(v1.x - v2.x, v1.y - v2.y)
    
    @staticmethod
    def get_relative_position(point: Vertex, edge: 'Edge') -> float:
       return float(edge.weights[0] * point.x + edge.weights[1] * point.y + edge.bias)
    
    @staticmethod
    def get_midpoint(edge: Edge) -> Vertex:
        mid_x = (edge.p1.x + edge.p2.x) / 2.0
        mid_y = (edge.p1.y + edge.p2.y) / 2.0
        return Vertex(mid_x, mid_y)

    @staticmethod
    def get_normalized_vector(p1: Vertex, p2: Vertex) -> Vector2D:
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        norm = max(math.hypot(dx, dy), 1e-6)
        return Vector2D(dx=dx / norm, dy=dy / norm)
    
    @staticmethod
    def _ccw(a: Vertex, b: Vertex, c: Vertex) -> float:
       return (c.y - a.y) * (b.x - a.x) - (b.y - a.y) * (c.x - a.x)

    @staticmethod
    def do_segments_intersect(a: Vertex, b: Vertex, c: Vertex, d: Vertex) -> bool:
        ccw_acd = SpatialMath._ccw(a, c, d)
        ccw_bcd = SpatialMath._ccw(b, c, d)
        ccw_abc = SpatialMath._ccw(a, b, c)
        ccw_abd = SpatialMath._ccw(a, b, d)
        
        return (ccw_acd * ccw_bcd < 0) and (ccw_abc * ccw_abd < 0)
