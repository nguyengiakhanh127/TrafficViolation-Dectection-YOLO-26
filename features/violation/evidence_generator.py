import cv2
import numpy as np
import os
import logging
import threading
from queue import Queue, Full
from typing import List, Tuple, Optional
from dataclasses import dataclass

from shared.geometry.primitives import Vertex

logger = logging.getLogger("EvidenceGen")

@dataclass
class ImageExportTask:
    filepath: str
    image_data: np.ndarray

class EvidenceGenerator:
    """
    Trình sinh bằng chứng.
    """
    def __init__(self, queue_size: int = 100):
        self._export_queue: Queue[ImageExportTask] = Queue(maxsize=queue_size)
        self._is_running: bool = True
        
        self._worker_thread = threading.Thread(
            target=self._async_export_worker,
            name="ImageExportWorker",
            daemon=True
        )
        self._worker_thread.start()

    def shutdown(self) -> None:
        self._is_running = False
        self._export_queue.put(None)
        self._worker_thread.join(timeout=2.0)
        logger.info("Luồng xuất ảnh đã đóng an toàn.")

    def _async_export_worker(self) -> None:
        while self._is_running:
            task = self._export_queue.get()
            if task is None: 
                break 
                
            try:
                cv2.imwrite(task.filepath, task.image_data)
            except Exception as e:
                logger.error(f"Lỗi ghi ảnh bằng chứng ({task.filepath}): {e}")
            finally:
                self._export_queue.task_done()

    @staticmethod
    def draw_violation_highlight(
        base_image: np.ndarray, 
        target_bbox: Tuple[int, int, int, int], 
        trajectory: List[Vertex]
    ) -> Optional[np.ndarray]:
        if base_image is None or target_bbox is None:
            return None
            
        img = base_image.copy()
        x1, y1, x2, y2 = target_bbox
        
        h, w = img.shape[:2]
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(w, int(x2)), min(h, int(y2))
        
        color_bbox = (0, 255, 0)
        cv2.rectangle(img, (x1, y1), (x2, y2), color_bbox, 2)
        
        color_target = (0, 0, 255)
        cv2.circle(img, (x2, y1), 8, color_target, -1)
        
        if trajectory and len(trajectory) >= 2:
            pts = np.array([[int(v.x), int(v.y)] for v in trajectory], np.int32)
            pts = pts.reshape((-1, 1, 2))
            
            cv2.polylines(img, [pts], isClosed=False, color=color_target, thickness=2)
            
            for pt in trajectory:
                cv2.circle(img, (int(pt.x), int(pt.y)), 4, color_target, -1)
                
        return img

    @staticmethod
    def crop_vehicle(base_image: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        if base_image is None or bbox is None:
            return None
            
        x1, y1, x2, y2 = bbox
        h, w = base_image.shape[:2]
        
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(w, int(x2)), min(h, int(y2))
        
        return base_image[y1:y2, x1:x2]

    def export_evidence_images(
        self,
        vehicle, 
        violation_code: str, 
        img_dir: str, 
        timestamp_str: str
    ) -> None:
        """
        Trích xuất và kết xuất hình ảnh bằng chứng theo đúng 3 tiêu chuẩn đầu tiên:
        1. Ảnh gốc tại thời điểm vi phạm.
        2. Ảnh tại thời điểm xe mới xuất hiện trong khung hình (Có vẽ hộp giới hạn và vệt di chuyển).
        3. Ảnh tại thời điểm xảy ra vi phạm (Có vẽ hộp giới hạn và vệt di chuyển).
        """
        try:
            f_frame = vehicle.get_first_frame()
            f_bbox = vehicle.first_bbox
            l_frame = vehicle.get_violation_frame(violation_code)
            l_bbox = vehicle.violation_bboxes.get(violation_code)
            
            trajectory = list(vehicle.coordinate.trajectory) if vehicle.coordinate else []
            tasks: List[ImageExportTask] = []
            
            if l_frame is not None:
                tasks.append(ImageExportTask(
                    os.path.join(img_dir, f"{timestamp_str}_1_original.jpg"), 
                    l_frame.copy()
                ))
            
            if f_frame is not None and f_bbox is not None:
                img_scene_in = self.draw_violation_highlight(f_frame, f_bbox, trajectory)
                if img_scene_in is not None:
                    tasks.append(ImageExportTask(
                        os.path.join(img_dir, f"{timestamp_str}_2_scene_in.jpg"), 
                        img_scene_in
                    ))
                    
            if l_frame is not None and l_bbox is not None:
                img_scene_out = self.draw_violation_highlight(l_frame, l_bbox, trajectory)
                if img_scene_out is not None:
                    tasks.append(ImageExportTask(
                        os.path.join(img_dir, f"{timestamp_str}_3_scene_out.jpg"), 
                        img_scene_out
                    ))
            
            for task in tasks:
                try:
                    self._export_queue.put_nowait(task)
                except Full:
                    logger.warning(f"Hàng đợi ghi ảnh đầy, bỏ qua ảnh: {task.filepath}")
                    
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn bị ảnh bằng chứng: {e}")

    @staticmethod
    def extract_crop_for_ocr(vehicle, violation_code: str) -> Optional[np.ndarray]:
        """
        Trích xuất vùng ảnh nhỏ chứa phương tiện phục vụ cho hệ thống đọc biển số (ALPR).
        """
        l_frame = vehicle.get_violation_frame(violation_code)
        l_bbox = vehicle.violation_bboxes.get(violation_code)
        
        if l_frame is not None and l_bbox is not None:
            return EvidenceGenerator.crop_vehicle(l_frame, l_bbox)
        return None