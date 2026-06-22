import os
import json
from PyQt6.QtCore import QObject, pyqtSlot, QTimer
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtGui import QIcon
import numpy as np
import cv2

from core.vehicle import VehicleManager
from core.engine import ViolationRuleEngine
from core.engine import (
    WrongWayRule, LineCrossingRule, WrongLaneRule, 
    RedLightRunningRule
)
from core.records import ViolationRecordManager
from core.lane import LaneManager, ZoneManager

from features.detection.ai_adapters.yaml_mapper import YAML_ClassMapper
from features.detection.ai_adapters.alpr.plate_recognizer import LicensePlateRecognizer
from features.violation.evidence_writer import VideoRingBuffer
from features.violation.evidence_generator import EvidenceGenerator
from features.detection.detection_service import DetectionService
from features.violation.violation_service import ViolationService

from features.config_builder.services.ai_vision_thread import AIVisionThread
from features.config_builder.services.workspace_manager import WorkspaceManager
from features.config_builder.services.config_compiler import ConfigCompiler
from shared.gui.shared_components.event_broker import app_broker

from features.config_builder.panels.lane_config_widget import LaneConfigWidget
from features.config_builder.panels.zone_config_widget import ZoneConfigWidget
from features.config_builder.panels.light_config_widget import LightConfigWidget
from features.config_builder.panels.lane_rule_config_widget import LaneRuleConfigWidget

from shared.utils import paths
from shared.utils.enums import TrafficVehicleType
import logging

logger = logging.getLogger("BuilderController")

class BuilderController(QObject):
    """
    Trình điều khiển trung tâm cho Config Builder.
    Quản lý luồng AI, tương tác UI, đọc/ghi tệp JSON và liên kết với Cơ sở dữ liệu.
    """
    def __init__(self, canvas, panel, toolbar, db_service): 
        super().__init__()
        self.canvas = canvas
        self.panel = panel
        self.toolbar = toolbar
        self.db_service = db_service
        
        self.workspace_mgr = WorkspaceManager(panel, canvas)
        
        self._init_backend_services()
        
        self.compiler = ConfigCompiler(
            self.panel, 
            self.workspace_mgr, 
            self.lane_manager, 
            self.zone_manager,
            self.traffic_lights
        )

        self._load_cameras_to_ui()
        self._wire_signals()

    def _init_backend_services(self) -> None:
        self.vehicle_manager = VehicleManager()
        
        self.rule_engine = ViolationRuleEngine()
        self.rule_engine.add_rule(RedLightRunningRule())

        self.record_manager = ViolationRecordManager()
        self.video_buffer = VideoRingBuffer() 
        self.evidence_generator = EvidenceGenerator()
        
        self.lane_manager = LaneManager(lanes=[])
        self.zone_manager = ZoneManager(zones=[])
        self.traffic_lights = [] 

        self.class_mapper = YAML_ClassMapper(paths.YAML)
        
        self.alpr_service = LicensePlateRecognizer(yolo_model_path=paths.LICENSE_PLATE_DETECTION_OPENVINO_MODEL)
        self.detection_service = DetectionService(self.class_mapper, self.vehicle_manager)
        
        self.violation_service = ViolationService(
            rule_engine=self.rule_engine, 
            record_manager=self.record_manager, 
            video_buffer=self.video_buffer,
            lane_manager=self.lane_manager, 
            zone_manager=self.zone_manager, 
            evidence_generator=self.evidence_generator, 
            db_service=self.db_service,
            alpr_service=self.alpr_service 
        )

        self.video_thread = AIVisionThread(
            detection_service=self.detection_service, 
            violation_service=self.violation_service, 
            traffic_lights=self.traffic_lights,
            model_path=paths.VEHICLE_DETECTION_OPENVINO_MODEL
        )

    def _wire_signals(self) -> None:
        self.panel.media_load_requested.connect(self.handle_load_media)
        self.panel.play_pause_requested.connect(self.handle_play_pause)
        self.panel.seek_requested.connect(self.video_thread.seek_frame)
        self.panel.start_ai_requested.connect(self.handle_start_ai)

        self.panel.reset_requested.connect(self.handle_reset_workspace)
        self.panel.export_requested.connect(self.handle_export_json)
        self.panel.import_requested.connect(self.handle_import_config)
        
        self.video_thread.video_info_ready.connect(self.handle_video_info)
        self.video_thread.frame_processed.connect(self.handle_new_frame)
        self.video_thread.playback_finished.connect(self.handle_playback_finished)

        app_broker.toggle_db_logging.connect(self.handle_toggle_db)
        
        self.toolbar.overlay_config_changed.connect(
            self._apply_overlay_config
        )

    # =========================================================================
    # QUẢN LÝ MEDIA & AI
    # =========================================================================
    
    @pyqtSlot(str)
    def handle_load_media(self, filepath: str) -> None:
        self.video_thread.stop()
        self.video_thread.ai_enabled = False 
        self.video_thread.load_video(filepath)
        self.video_thread.start()
        
        QTimer.singleShot(50, self.canvas.recenter_and_fit)

    @pyqtSlot()
    def handle_play_pause(self) -> None:
        if not self.video_thread.cap or not self.video_thread.cap.isOpened(): 
            return
        self.video_thread.toggle_pause()
        if self.video_thread.is_paused:
            self.panel.btn_play.setIcon(QIcon(os.path.join(paths.ICONS_DIR, "pause.png")))
        else:
            self.panel.btn_play.setIcon(QIcon(os.path.join(paths.ICONS_DIR, "play.png")))

    @pyqtSlot(np.ndarray, list, object)
    def handle_new_frame(self, frame: np.ndarray, vehicles_list: list, tracked_detections: object) -> None:
        if frame is None:
            return

        self.canvas.set_frame(frame, vehicles_list)
        
        if self.video_thread.cap:
            current_frame_idx = int(self.video_thread.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.panel.update_video_progress(current_frame_idx)

    def _apply_overlay_config(self, config) -> None:
        """Đồng bộ cấu hình từ Toolbar Popup xuống AIOverlayManager."""
        ai_mgr = self.canvas.ai_manager
        ai_mgr.visual_filters["show_trails"] = config.show_trails
        ai_mgr.visual_filters["show_violators_only"] = config.show_violators_only
        ai_mgr.violation_colors = config.violation_colors

        # Chuyển đổi visible_classes dict sang format của AIOverlayManager
        ai_mgr.visual_filters["show_cars"] = any(
            config.visible_classes.get(vt, True)
            for vt in [TrafficVehicleType.CAR, TrafficVehicleType.TRUCK, TrafficVehicleType.BUS]
        )
        ai_mgr.visual_filters["show_motorcycles"] = config.visible_classes.get(
            TrafficVehicleType.MOTORCYCLE, True
        )
            
    @pyqtSlot(float, int)
    def handle_video_info(self, fps: float, total_frames: int) -> None:
        self.video_buffer.update_fps(fps)
        self.panel.update_video_info(fps, total_frames)

    @pyqtSlot()
    def handle_playback_finished(self) -> None:
        self.panel.btn_play.setIcon(QIcon(os.path.join(paths.ICONS_DIR, "play.png")))

    @pyqtSlot()
    def handle_start_ai(self) -> None:
        camera_id = self.panel.combo_cam_select.currentData()
        if not camera_id:
            QMessageBox.critical(self.canvas, "Lỗi", "Vui lòng chọn Camera trước khi chạy hệ thống giám sát!")
            return

        success = self.compiler.compile()
        if not success: 
            return 
        
        camera_name = self.panel.combo_cam_select.currentText()
        self.record_manager.camera_name = camera_name 
        self.violation_service.current_camera_id = camera_id
           
        current_frame_idx = 0
        if self.video_thread.cap and self.video_thread.cap.isOpened():
            current_frame_idx = int(self.video_thread.cap.get(cv2.CAP_PROP_POS_FRAMES))

        self.video_thread.stop()
        self.video_thread.ai_enabled = True
        self.video_thread.load_video(self.video_thread.video_path)
        self.video_thread.seek_frame(current_frame_idx)
        self.video_thread.start()
        
        self.panel.btn_play.setIcon(QIcon(os.path.join(paths.ICONS_DIR, "pause.png")))
        QMessageBox.information(self.canvas, "AI Ready", f"Hệ thống giám sát '{camera_name}' đã khởi động!")
    
    @pyqtSlot()
    def handle_reset_workspace(self) -> None:
        is_cleared = self.workspace_mgr.reset_workspace()
        if is_cleared:
            self.video_thread.stop()
            self.video_thread.video_path = ""
            self.panel.btn_play.setIcon(QIcon(os.path.join(paths.ICONS_DIR, "play.png")))
            self.panel.update_video_info(0, 0)
            self.panel.update_video_progress(0)

    @pyqtSlot(bool)
    def handle_toggle_db(self, is_enabled: bool) -> None:
        self.violation_service.enable_db_logging = is_enabled

    # =========================================================================
    # QUẢN LÝ DỮ LIỆU CẤU HÌNH (JSON & DATABASE)
    # =========================================================================

    def _load_cameras_to_ui(self, select_id: int = None) -> None:
        self.panel.combo_cam_select.blockSignals(True)
        self.panel.combo_cam_select.clear()
        
        cameras = self.db_service.cameras.get_all()
        if not cameras:
            self.panel.combo_cam_select.addItem("--- Chưa có Camera nào ---", userData=None)
        else:
            for cam in cameras:
                self.panel.combo_cam_select.addItem(cam['ten_camera'], userData=cam['id'])
                
            if select_id:
                index = self.panel.combo_cam_select.findData(select_id)
                if index >= 0:
                    self.panel.combo_cam_select.setCurrentIndex(index)
                    
        self.panel.combo_cam_select.blockSignals(False)

    @pyqtSlot()
    def handle_export_json(self) -> None:
        camera_id = self.panel.combo_cam_select.currentData()
        camera_name = self.panel.combo_cam_select.currentText()
        
        if not camera_id:
            QMessageBox.critical(self.canvas, "Lỗi", "Vui lòng chọn Camera trước khi Xuất JSON.")
            return
        
        success = self.compiler.compile()
        if not success: return 

        config_data = {"lanes": [], "zones": [], "traffic_lights": []}

        for lane in self.lane_manager.lanes:
            config_data["lanes"].append({
                "id": lane.lane_id,
                "allowed_vehicles": [v.name for v in lane.lane_rule.allowed_vehicles],
                "edges": [{"p1": [e.p1.x, e.p1.y], "p2": [e.p2.x, e.p2.y], "type": e.line_type.name} for e in lane.edges]
            })

        for zone in self.zone_manager.zones:
            config_data["zones"].append({
                "id": zone.zone_id,
                "type": zone.zone_type.name,
                "prohibited_hours": list(zone.prohibited_hours) if zone.prohibited_hours else None,
                "prohibited_days": zone.prohibited_days,
                "vertices": [[v.x, v.y] for v in zone.polygon.vertices]
            })

        for light in self.traffic_lights:
            light_dict = {
                "id": light.light_id,
                "bbox": [light.bbox[0], light.bbox[1], light.bbox[2], light.bbox[3]], 
                "stop_line": {"p1": [light.stop_line.p1.x, light.stop_line.p1.y], "p2": [light.stop_line.p2.x, light.stop_line.p2.y]},
            }
            if light.right_turn_line:
                light_dict["right_turn_line"] = {"p1": [light.right_turn_line.p1.x, light.right_turn_line.p1.y], "p2": [light.right_turn_line.p2.x, light.right_turn_line.p2.y]}
            else:
                light_dict["right_turn_line"] = None
                
            config_data["traffic_lights"].append(light_dict)

        default_dir = os.path.join(paths.PROJECT_ROOT, "data", "configs")
        os.makedirs(default_dir, exist_ok=True) 

        safe_cam_name = camera_name.replace(" ", "_")
        default_filename = f"config_{safe_cam_name}.json"

        filepath, _ = QFileDialog.getSaveFileName(
            self.canvas, "Lưu Cấu Hình AI", 
            os.path.join(default_dir, default_filename), 
            "JSON Files (*.json);;All Files (*)" 
        )

        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=4)

                self.db_service.cameras.update_config_path(camera_id, filepath)
                msg = f"Đã xuất cấu hình và liên kết với Camera ID: {camera_id}!"
                QMessageBox.information(self.canvas, "Thành công", msg)
            except Exception as e:
                QMessageBox.critical(self.canvas, "Lỗi", f"Không thể lưu file: {str(e)}")

    @pyqtSlot(int)
    def handle_import_config(self, camera_id: int):
        cameras = self.db_service.cameras.get_all()
        cam_info = next((c for c in cameras if c['id'] == camera_id), None)
        
        if not cam_info or not cam_info.get('duong_dan_cau_hinh'):
            QMessageBox.warning(self.canvas, "Trống", "Camera này chưa được lưu cấu hình nào!")
            return
            
        filepath = cam_info['duong_dan_cau_hinh']
        if not os.path.exists(filepath):
            QMessageBox.critical(self.canvas, "Lỗi", f"Không tìm thấy tệp JSON tại: {filepath}")
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self.canvas, "Lỗi file", f"Tệp JSON bị hỏng: {e}")
            return

        self.workspace_mgr.decompile_graphics(json_data)
        
        self.panel._clear_all_cards()
        self._decompile_ui_cards(json_data)
        
        self.canvas.recenter_and_fit()
        
        is_rois_on = self.toolbar.current_overlay_config.show_rois
        app_broker.request_toggle_rois_visibility.emit(is_rois_on)
        
        QMessageBox.information(self.canvas, "Hoàn tất", "Đã tải cấu hình thành công!")

    def _decompile_ui_cards(self, json_data: dict):
        """Khôi phục các Thẻ Cấu Hình trên Right Panel"""
        registry = self.workspace_mgr.object_registry
        
        registry_data_for_ui = {
            "POLYGONS": list(registry["POLYGONS"].keys()),
            "BBOXES": list(registry["BBOXES"].keys()),
            "LINES": list(registry["LINES"].keys()),
            "RULES": [] 
        }
        
        lane_rule_mapping = {}

        for lane_data in json_data.get("lanes", []):
            allowed_names = lane_data.get("allowed_vehicles", [])
            lane_id = lane_data.get("id", "Unknown")
            
            rule_card = LaneRuleConfigWidget()
            
            allowed_enums = set()
            for name in allowed_names:
                try: 
                    enum_val = TrafficVehicleType[name]
                    allowed_enums.add(enum_val)
                    
                    menu = rule_card.btn_vehicles.menu()
                    for action in menu.actions():
                        checkbox = action.defaultWidget()
                        if checkbox.text() == enum_val.value:
                            checkbox.setChecked(True)
                except KeyError: 
                    pass
            
            auto_rule_id = rule_card.input_id.text()
            lane_rule_mapping[lane_id] = auto_rule_id
            self.workspace_mgr.object_registry["RULES"][auto_rule_id] = set(rule_card.allowed_vehicles)
            
            rule_card.request_delete.connect(self.panel._remove_card)
            self.panel.object_list_layout.addWidget(rule_card)
        
        registry_data_for_ui["RULES"] = list(registry["RULES"].keys())
        self.workspace_mgr.broadcast_registry()

        for lane_data in json_data.get("lanes", []):
            card = LaneConfigWidget()
            card.update_registry_list(registry_data_for_ui)
            
            lane_id = lane_data.get("id", "")
            card.input_id.setText(lane_id)
            
            rule_id_to_select = lane_rule_mapping.get(lane_id)
            if rule_id_to_select:
                rule_idx = card.combo_rule_ref.findText(rule_id_to_select)
                if rule_idx >= 0: 
                    card.combo_rule_ref.setCurrentIndex(rule_idx)
            
            poly_id = lane_data.get("_mapped_poly_id")
            if poly_id:
                card.current_obj_id = poly_id
                poly_idx = card.combo_ref.findText(poly_id)
                if poly_idx >= 0: card.combo_ref.setCurrentIndex(poly_idx)
                
                card.build_sub_edges_ui(len(lane_data.get("edges", [])))
                for i, edge_info in enumerate(lane_data.get("edges", [])):
                    type_str = edge_info.get("type", "SOLID")
                    idx = card.sub_edge_combos[i].findData(type_str)
                    if idx >= 0: card.sub_edge_combos[i].setCurrentIndex(idx)
                    
            card.request_delete.connect(self.panel._remove_card)
            self.panel.object_list_layout.addWidget(card)

        for zone_data in json_data.get("zones", []):
            card = ZoneConfigWidget()
            card.update_registry_list(registry_data_for_ui)
            
            card.input_id.setText(zone_data.get("id", ""))
            
            type_idx = card.combo_type.findData(zone_data.get("type", "FORBIDDEN_AREA"))
            if type_idx >= 0: card.combo_type.setCurrentIndex(type_idx)
            
            hours = zone_data.get("prohibited_hours")
            if hours and len(hours) == 2:
                card.spin_start_hour.setValue(hours[0])
                card.spin_end_hour.setValue(hours[1])
            
            days = zone_data.get("prohibited_days")
            if days == "EVEN": card.combo_days.setCurrentIndex(1)
            elif days == "ODD": card.combo_days.setCurrentIndex(2)
            else: card.combo_days.setCurrentIndex(0)
            
            poly_id = zone_data.get("_mapped_poly_id")
            if poly_id:
                card.current_obj_id = poly_id
                poly_idx = card.combo_ref.findText(poly_id)
                if poly_idx >= 0: card.combo_ref.setCurrentIndex(poly_idx)
                
            card.request_delete.connect(self.panel._remove_card)
            self.panel.object_list_layout.addWidget(card)

        for light_data in json_data.get("traffic_lights", []):
            card = LightConfigWidget()
            card.update_registry_list(registry_data_for_ui)
            
            card.input_id.setText(light_data.get("id", ""))
            
            bbox_id = light_data.get("_mapped_bbox_id")
            if bbox_id:
                card.current_bbox_id = bbox_id
                idx = card.combo_bbox.findText(bbox_id)
                if idx >= 0: card.combo_bbox.setCurrentIndex(idx)
                
            stop_id = light_data.get("_mapped_stop_id")
            if stop_id:
                card.current_stop_id = stop_id
                idx = card.combo_stop.findText(stop_id)
                if idx >= 0: card.combo_stop.setCurrentIndex(idx)

            right_id = light_data.get("_mapped_right_id")
            if right_id:
                card.current_right_id = right_id
                idx = card.combo_right.findText(right_id)
                if idx >= 0: card.combo_right.setCurrentIndex(idx)

            card.request_delete.connect(self.panel._remove_card)
            self.panel.object_list_layout.addWidget(card)
            
        self.panel.config_box.update_content_height()