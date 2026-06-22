import copy
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from shared.geometry.shapes import Edge
from shared.utils.enums import TrafficLightColor


class TrafficLight:
    """Theo dõi trạng thái màu của một cột đèn giao thông trong bbox cố định."""

    DEFAULT_HSV_RANGES = {
        TrafficLightColor.RED: [
            (
                np.array([0, 15, 20], dtype=np.uint8),
                np.array([20, 255, 255], dtype=np.uint8),
            ),
            (
                np.array([155, 15, 20], dtype=np.uint8),
                np.array([179, 255, 255], dtype=np.uint8),
            ),
        ],
        TrafficLightColor.YELLOW: [
            (
                np.array([21, 40, 40], dtype=np.uint8),
                np.array([40, 255, 255], dtype=np.uint8),
            )
        ],
        TrafficLightColor.GREEN: [
            (
                np.array([41, 30, 30], dtype=np.uint8),
                np.array([100, 255, 255], dtype=np.uint8),
            )
        ],
    }

    def __init__(
        self,
        light_id: str,
        bbox_rect: Tuple[int, int, int, int],
        stop_line: Edge,
        right_turn_line: Optional[Edge] = None,
        active_pixel_ratio: float = 0.10
    ):
        if not 0.0 <= active_pixel_ratio <= 1.0:
            raise ValueError("active_pixel_ratio phải nằm trong khoảng [0, 1].")

        self.light_id = light_id

        x, y, width, height = bbox_rect
        self.bbox = (
            int(x),
            int(y),
            int(x + width),
            int(y + height),
        )

        self.stop_line = stop_line
        self.right_turn_line = right_turn_line
        self.active_pixel_ratio = float(active_pixel_ratio)

        self.hsv_ranges = copy.deepcopy(self.DEFAULT_HSV_RANGES)
        self.current_color = TrafficLightColor.OFF

    @staticmethod
    def _create_range_mask(
        hsv_roi: np.ndarray,
        lower: np.ndarray,
        upper: np.ndarray,
    ) -> np.ndarray:
        lower = np.asarray(lower, dtype=np.uint8).reshape(3)
        upper = np.asarray(upper, dtype=np.uint8).reshape(3)

        h = hsv_roi[:, :, 0]
        s = hsv_roi[:, :, 1]
        v = hsv_roi[:, :, 2]

        condition = (
            (h >= int(lower[0]))
            & (h <= int(upper[0]))
            & (s >= int(lower[1]))
            & (s <= int(upper[1]))
            & (v >= int(lower[2]))
            & (v <= int(upper[2]))
        )

        return condition.astype(np.uint8) * 255

    def _create_color_mask(
        self,
        hsv_roi: np.ndarray,
        color: TrafficLightColor,
    ) -> np.ndarray:
        combined_mask = np.zeros(hsv_roi.shape[:2], dtype=np.uint8)

        for lower, upper in self.hsv_ranges[color]:
            range_mask = self._create_range_mask(hsv_roi, lower, upper)
            combined_mask = cv2.bitwise_or(combined_mask, range_mask)

        return combined_mask

    def update_state(self, frame: np.ndarray) -> TrafficLightColor:
        """Cập nhật màu đèn từ vùng ảnh được chỉ định bởi bbox."""
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            raise ValueError("frame không hợp lệ hoặc rỗng.")

        xmin, ymin, xmax, ymax = self.bbox
        h_img, w_img = frame.shape[:2]

        bbox_width = xmax - xmin
        bbox_height = ymax - ymin

        padding_x = max(2, int(round(bbox_width * 0.25)))
        padding_y = max(2, int(round(bbox_height * 0.10)))

        xmin = max(0, xmin - padding_x)
        ymin = max(0, ymin - padding_y)
        xmax = min(w_img, xmax + padding_x)
        ymax = min(h_img, ymax + padding_y)

        clipped_bbox = (xmin, ymin, xmax, ymax)

        if xmax <= xmin or ymax <= ymin:
            self.current_color = TrafficLightColor.OFF
            return self.current_color

        roi = frame[ymin:ymax, xmin:xmax]

        if roi.size == 0:
            self.current_color = TrafficLightColor.OFF
            return self.current_color

        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        total_pixels = hsv_roi.shape[0] * hsv_roi.shape[1]
        color_ratios: Dict[TrafficLightColor, float] = {}

        for color in self.hsv_ranges:
            mask = self._create_color_mask(hsv_roi, color)
            active_pixels = int(np.count_nonzero(mask))
            ratio = active_pixels / total_pixels if total_pixels else 0.0
            color_ratios[color] = ratio

        if not color_ratios:
            self.current_color = TrafficLightColor.OFF
            return self.current_color

        dominant_color, dominant_ratio = max(
            color_ratios.items(),
            key=lambda item: item[1],
        )

        if dominant_ratio >= self.active_pixel_ratio:
            self.current_color = dominant_color
        else:
            self.current_color = TrafficLightColor.OFF

        return self.current_color
