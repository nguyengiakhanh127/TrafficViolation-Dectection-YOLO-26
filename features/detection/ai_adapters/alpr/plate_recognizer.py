import cv2
import numpy as np
import logging
from typing import Tuple, Optional
import fast_plate_ocr
import re

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False

logger = logging.getLogger("ALPRService")

class LicensePlateRecognizer:
    """
    Hệ thống nhận diện biển số:
    - Giai đoạn 1: YOLO phát hiện và cắt khung chứa biển số từ ảnh cận cảnh xe.
    - Giai đoạn 2: Fast-Plate-OCR đọc ký tự từ ảnh biển số đã cắt.
    """
    def __init__(self, yolo_model_path: str):
        self.yolo_model_path = yolo_model_path
        self.plate_detector = None
        self.ocr_reader = None
        
        self._initialize_models()

    def _initialize_models(self) -> None:
        try:
            if HAS_YOLO:
                logger.info(f"Đang nạp mô hình phát hiện biển số (YOLO) từ: {self.yolo_model_path}")
                self.plate_detector = YOLO(self.yolo_model_path, task='detect')
            else:
                logger.error("Không tìm thấy thư viện Ultralytics")

            logger.info("Đang nạp mô hình đọc ký tự (fast-plate-ocr)...")
            self.ocr_reader = fast_plate_ocr.inference.plate_recognizer.LicensePlateRecognizer("global-plates-mobile-vit-v2-model")
            logger.info("Hệ thống ALPR (Fast-Plate-OCR) đã sẵn sàng.")
            
        except Exception as e:
            logger.error(f"Lỗi khởi tạo hệ thống ALPR: {e}")

    def recognize(self, vehicle_crop: np.ndarray) -> Tuple[str, Optional[np.ndarray]]:
        if vehicle_crop is None or self.plate_detector is None or self.ocr_reader is None:
            return "Không xác định", None

        try:
            # ==========================================
            # STAGE 1: PHÁT HIỆN BIỂN SỐ BẰNG YOLO
            # ==========================================
            results = self.plate_detector(vehicle_crop, verbose=False)[0]
            boxes = results.boxes
            
            if len(boxes) == 0:
                return "Không xác định", None

            best_box = max(boxes, key=lambda b: float(b.conf[0]))
            
            x1, y1, x2, y2 = map(int, best_box.xyxy[0].tolist())
            
            h, w = vehicle_crop.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            plate_crop = vehicle_crop[y1:y2, x1:x2]
            
            if plate_crop.size == 0:
                return "Không xác định", None

            # ==========================================
            # STAGE 2: ĐỌC VÀ LÀM SẠCH KÝ TỰ 
            # ==========================================
            gray_plate_crop = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
            ocr_result = self.ocr_reader.run(gray_plate_crop)
            
            if isinstance(ocr_result, list) and len(ocr_result) > 0:
                raw_text = "".join(ocr_result)
            elif isinstance(ocr_result, str):
                raw_text = ocr_result
            else:
                raw_text = str(ocr_result) if ocr_result else ""
            
            clean_text = re.sub(r'[^A-Za-z0-9]', '', raw_text).upper()
            
            if len(clean_text) < 3: 
                plate_text = "Không xác định"
            else:
                plate_text = clean_text
            
            # ==========================================
            # TRẢ VỀ KẾT QUẢ
            # ==========================================
            return plate_text, plate_crop

        except Exception as e:
            logger.error(f"Lỗi trong quá trình suy luận ALPR: {e}")
            return "Không xác định", None