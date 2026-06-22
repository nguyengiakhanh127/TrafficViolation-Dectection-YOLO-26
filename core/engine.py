import logging
from typing import List, Optional
from datetime import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from shared.utils.enums import TrafficVehicleType, ViolationType, TrafficZoneType, TrafficLightColor
from shared.geometry.spatial_math import SpatialMath 
from core.lane import (
    TrafficLane, 
    TrafficZone,
    get_distance_to_start, 
    is_vehicle_inside, 
    is_vehicle_allowed
)
from core.rules import ViolationRegistry
from core.vehicle import Vehicle
from core.trafficlight import TrafficLight

logger = logging.getLogger("RuleEngine")
logger.setLevel(logging.INFO)

# ==========================================
# 1. MODELS & CONTEXT (Dữ liệu & Bối cảnh)
# ==========================================

class ViolationEvent:
    def __init__(self, vehicle_id: int, violation_type: ViolationType):
        self.vehicle_id = vehicle_id
        self.violation_type = violation_type
        self.error_name: str = ViolationRegistry.get_code(violation_type)
        self.description: str = ViolationRegistry.get_description(violation_type)

    def __repr__(self):
        return f"[VIOLATION] Xe {self.vehicle_id} - Lỗi: {self.error_name} ({self.description})"

@dataclass
class InspectionContext:
    """Đóng gói toàn bộ bối cảnh không gian và thời gian tại thời điểm kiểm tra"""
    lane: Optional[TrafficLane] = None
    zones: List[TrafficZone] = field(default_factory=list)
    current_time: datetime = field(default_factory=datetime.now)
    traffic_lights: List['TrafficLight'] = field(default_factory=list)


# ==========================================
# 2. BASE RULE (Lớp trừu tượng nền tảng)
# ==========================================

class BaseViolationRule(ABC):
    """Lớp nền tảng cho mọi thuật toán bắt lỗi vi phạm"""
    @abstractmethod
    def evaluate(self, vehicle: Vehicle, context: InspectionContext) -> Optional[ViolationEvent]:
        pass

    def _register_violation(self, vehicle: Vehicle, violation_type: ViolationType) -> Optional[ViolationEvent]:
        """Hàm tiện ích giúp ghi nhận vi phạm để tránh bắt trùng lặp liên tục"""
        if violation_type not in vehicle.active_violations:
            vehicle.active_violations.add(violation_type)
            return ViolationEvent(vehicle.id, violation_type)
        return None


# ==========================================
# 3. CONCRETE RULES (Các luật cụ thể)
# ==========================================

class WrongWayRule(BaseViolationRule):
    def evaluate(self, vehicle: Vehicle, context: InspectionContext) -> Optional[ViolationEvent]:
        if not vehicle.is_moving(threshold=2.0) or not context.lane:
            return None
        if not vehicle.previous_position:
            return None
            
        d_current = get_distance_to_start(context.lane, vehicle.current_position)
        d_prev = get_distance_to_start(context.lane, vehicle.previous_position)
        
        is_distance_decreasing = (d_current - d_prev) < -0.2
        is_vector_opposed = vehicle.direction.dot_product(context.lane.lane_direction) < 0
        
        if is_distance_decreasing and is_vector_opposed:
            return self._register_violation(vehicle, ViolationType.WRONG_WAY)
        return None

class LineCrossingRule(BaseViolationRule):
    def evaluate(self, vehicle: Vehicle, context: InspectionContext) -> Optional[ViolationEvent]:
        if not vehicle.is_moving(threshold=2.0) or not context.lane:
            return None
        if not vehicle.previous_routing_point:
            return None

        has_footprint = vehicle.footprint_left is not None

        for edge in context.lane.solid_edges:
            if has_footprint:
                crossed = self._check_with_footprint(vehicle, edge)
            else:
                crossed = self._check_with_routing_point(vehicle, edge)

            if crossed:
                return self._register_violation(vehicle, ViolationType.LINE_CROSSING)

        return None

    def _check_with_footprint(self, vehicle: Vehicle, edge) -> bool:
        """Kiểm tra giao cắt bằng quỹ đạo bánh trái, phải, và gầm xe."""
        if not vehicle.previous_footprint_left or not vehicle.previous_footprint_right:
            return False

        crossed_left = SpatialMath.do_segments_intersect(
            vehicle.previous_footprint_left, vehicle.footprint_left, edge.p1, edge.p2
        )
        crossed_right = SpatialMath.do_segments_intersect(
            vehicle.previous_footprint_right, vehicle.footprint_right, edge.p1, edge.p2
        )
        straddling = SpatialMath.do_segments_intersect(
            vehicle.footprint_left, vehicle.footprint_right, edge.p1, edge.p2
        )
        return crossed_left or crossed_right or straddling

    def _check_with_routing_point(self, vehicle: Vehicle, edge) -> bool:
        """Kiểm tra giao cắt bằng quỹ đạo điểm tiếp xúc mặt đường."""
        return SpatialMath.do_segments_intersect(
            vehicle.previous_routing_point, vehicle.routing_point, edge.p1, edge.p2
        )

class WrongLaneRule(BaseViolationRule):
    def evaluate(self, vehicle: Vehicle, context: InspectionContext) -> Optional[ViolationEvent]:
        if not context.lane:
            return None

        is_inside_lane = is_vehicle_inside(context.lane, vehicle.routing_point)
        is_wrong_lane = not is_vehicle_allowed(context.lane, vehicle.vehicle_type)

        if is_inside_lane and is_wrong_lane:
            return self._register_violation(vehicle, ViolationType.WRONG_LANE)
        return None

class IllegalParkingRule(BaseViolationRule):
    def __init__(self, source_fps: int = 24, allowed_time_second: int = 300):
        self.source_fps = source_fps
        self.allowed_time_second = allowed_time_second

    def evaluate(self, vehicle: Vehicle, context: InspectionContext) -> Optional[ViolationEvent]:
        if vehicle.is_moving(threshold=1.0) or not context.zones:
            return None

        if vehicle.stationary_frames < self.allowed_time_second * self.source_fps:
            return None

        for zone in context.zones:
            if zone.zone_type == TrafficZoneType.NO_PARKING and zone.is_currently_active(context.current_time):
                return self._register_violation(vehicle, ViolationType.ILLEGAL_PARKING)
        return None

class PedestrianStopRule(BaseViolationRule):
    def __init__(self, source_fps: int = 24, allowed_time_second: int = 300):
        self.source_fps = source_fps
        self.allowed_time_second = allowed_time_second

    def evaluate(self, vehicle: Vehicle, context: InspectionContext) -> Optional[ViolationEvent]:
        if vehicle.is_moving(threshold=1.0) or not context.zones:
            return None

        if vehicle.stationary_frames < self.allowed_time_second * self.source_fps:
            return None

        for zone in context.zones:
            if zone.zone_type == TrafficZoneType.PEDESTRIAN_CROSSING:
                return self._register_violation(vehicle, ViolationType.PEDESTRIAN_CROSSING_STOP)
        return None

class RedLightRunningRule(BaseViolationRule):
    def __init__(
        self,
        escape_distance_px: float = 150.0,
        right_turn_exempt_types: Optional[List[TrafficVehicleType]] = None
    ):
        self.escape_distance_px = escape_distance_px
        self.right_turn_exempt_types = right_turn_exempt_types or [
            TrafficVehicleType.MOTORCYCLE
        ]

    def evaluate(self, vehicle: Vehicle, context: InspectionContext) -> Optional[ViolationEvent]:
        if not context.traffic_lights or not context.lane:
            return None
        if vehicle.violation_state.has(ViolationType.RED_LINE):
            return None
        if not vehicle.previous_routing_point:
            return None

        for light in context.traffic_lights:
            # Pha 2: Xe đang ở trạng thái chờ xác nhận
            if vehicle.violation_state.is_pending(ViolationType.RED_LINE):
                return self._handle_pending_phase(vehicle, light)

            # Pha 1: Kiểm tra xe có vượt vạch dừng khi đèn đỏ không
            event = self._handle_crossing_phase(vehicle, light)
            if event is not None:
                return event

        return None

    # --------------------------------------------------
    # Pha 1: Phát hiện vượt vạch dừng khi đèn đỏ
    # --------------------------------------------------

    def _handle_crossing_phase(self, vehicle: Vehicle, light: 'TrafficLight') -> Optional[ViolationEvent]:
        """Pha 1: Kiểm tra xe có cắt qua stop_line khi đèn đỏ không."""
        if light.current_color != TrafficLightColor.RED:
            return None

        if not self._is_crossing_line(vehicle, light.stop_line):
            return None

        # Xe vượt vạch khi đèn đỏ
        if light.right_turn_line:
            # Có vạch rẽ phải → chuyển sang Pha 2 (pending)
            vehicle.violation_state.add_pending(
                ViolationType.RED_LINE, vehicle.routing_point
            )
            return None
        else:
            # Không có vạch rẽ phải → vi phạm ngay
            return self._register_violation(vehicle, ViolationType.RED_LINE)

    # --------------------------------------------------
    # Pha 2: Quan sát sau vượt vạch
    # --------------------------------------------------

    def _handle_pending_phase(self, vehicle: Vehicle, light: 'TrafficLight') -> Optional[ViolationEvent]:
        """Pha 2: Xe đã vượt vạch, theo dõi xem rẽ phải hay đi thẳng."""
        # Kiểm tra rẽ phải trước (ưu tiên miễn trừ)
        exemption_result = self._check_right_turn_exemption(vehicle, light)
        if exemption_result is not None:
            return exemption_result

        # Kiểm tra khoảng cách thoát
        return self._check_escape_distance(vehicle)

    def _check_right_turn_exemption(self, vehicle: Vehicle, light: 'TrafficLight') -> Optional[ViolationEvent]:
        """Kiểm tra xe có đang rẽ phải hợp lệ không."""
        if not self._is_crossing_line(vehicle, light.right_turn_line):
            return None  # Chưa cắt vạch rẽ phải, chưa kết luận được

        vehicle.violation_state.remove_pending(ViolationType.RED_LINE)

        if vehicle.vehicle_type in self.right_turn_exempt_types:
            return None  # Miễn trừ: xe máy rẽ phải hợp lệ
        else:
            return self._register_violation(vehicle, ViolationType.RED_LINE)

    # --------------------------------------------------
    # Pha 3: Xác nhận vi phạm qua khoảng cách
    # --------------------------------------------------

    def _check_escape_distance(self, vehicle: Vehicle) -> Optional[ViolationEvent]:
        """Pha 3: Xác nhận vi phạm nếu xe đi xa quá ngưỡng từ vị trí vượt vạch."""
        origin = vehicle.violation_state.pending_origins.get(ViolationType.RED_LINE)
        if not origin:
            return None

        dist = SpatialMath.calculate_distance(origin, vehicle.routing_point)
        if dist > self.escape_distance_px:
            vehicle.violation_state.remove_pending(ViolationType.RED_LINE)
            return self._register_violation(vehicle, ViolationType.RED_LINE)

        return None

    # --------------------------------------------------
    # Tiện ích: Phát hiện giao cắt đoạn thẳng
    # --------------------------------------------------

    @staticmethod
    def _is_crossing_line(vehicle: Vehicle, line) -> bool:
        """Kiểm tra xe có cắt qua một đường thẳng (Edge) giữa frame trước và frame hiện tại."""
        return SpatialMath.do_segments_intersect(
            vehicle.previous_routing_point, vehicle.routing_point,
            line.p1, line.p2
        )

# ==========================================
# 4. ENGINE (Bộ máy thực thi)
# ==========================================

class ViolationRuleEngine:
    def __init__(self):
        self._rules: List[BaseViolationRule] = []

    def add_rule(self, rule: BaseViolationRule):
        """Đăng ký một luật vi phạm vào Engine"""
        self._rules.append(rule)

    def remove_rule(self, rule_class: type):
        """Xóa một luật khỏi Engine dựa trên class"""
        self._rules = [r for r in self._rules if not isinstance(r, rule_class)]

    def inspect_vehicle(self, vehicle: Vehicle, context: InspectionContext) -> List[ViolationEvent]:
        """Đánh giá phương tiện dựa trên tất cả các luật đã đăng ký"""
        violations = []
        for rule in self._rules:
            event = rule.evaluate(vehicle, context)
            if event:
                violations.append(event)
        return violations