from PyQt6.QtCore import QObject, pyqtSlot, Qt
from PyQt6.QtWidgets import QMessageBox

import math
import logging

from shared.gui.shared_components.event_broker import app_broker
from shared.database.database_service import DatabaseService

logger = logging.getLogger("ReviewerController")

class ReviewerController(QObject):
    """
    Trình điều khiển màn hình Quản lý & Xét duyệt Vi phạm (Reviewer).
    Quản lý phân trang, lọc dữ liệu và tương tác an toàn với Cơ sở dữ liệu.
    """
    def __init__(self, view, db_service: DatabaseService):
        super().__init__()
        self.view = view
        self.db = db_service
        
        self.current_page = 1
        self.items_per_page = 20
        self.current_filters = {} 

        self._wire_signals()
        
        self._load_camera_filter()

        self._fetch_and_update_table()

    def _wire_signals(self) -> None:
        app_broker.request_search_violations.connect(self.handle_search)
        app_broker.submit_approval_decision.connect(self.handle_approval_decision)
        app_broker.request_print_ticket.connect(self.handle_print_ticket)

        self.view.data_table.btn_prev.clicked.connect(self.handle_prev_page)
        self.view.data_table.btn_next.clicked.connect(self.handle_next_page)

    @pyqtSlot(dict)
    def handle_search(self, filters: dict) -> None:
        """Xử lý sự kiện khi người dùng bấm nút Tìm kiếm trên Filter Panel"""
        logger.info(f"Yêu cầu lọc dữ liệu: {filters}")
        self.current_filters = filters
        self.current_page = 1 
        self._fetch_and_update_table()

    def handle_prev_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self._fetch_and_update_table()

    def handle_next_page(self) -> None:
        self.current_page += 1
        self._fetch_and_update_table()

    def _fetch_and_update_table(self) -> None:
        """Kéo dữ liệu từ DB và đẩy lên giao diện an toàn"""
        total_records = self.db.violations.get_total_count(self.current_filters)
        total_pages = math.ceil(total_records / self.items_per_page)

        if total_pages > 0 and self.current_page > total_pages:
            self.current_page = total_pages
        elif total_pages == 0:
            self.current_page = 1

        if total_records == 0:
            data_list = []
        else:
            offset = max(0, (self.current_page - 1) * self.items_per_page)
            data_list = self.db.violations.get_list(
                limit=self.items_per_page, 
                offset=offset, 
                filters=self.current_filters
            )

        self.view.data_table.load_data(data_list, self.current_page, total_pages)

    @pyqtSlot(int, int)
    def handle_approval_decision(self, record_id: int, new_status: int) -> None:
        """Xử lý Duyệt (1) hoặc Từ chối (-1) biên bản vi phạm"""
        if not record_id: 
            return
        
        success = self.db.violations.update_status(record_id, new_status)
        
        if success:
            self._fetch_and_update_table()
            self.view.evidence_viewer.lbl_image_display.setText("Xử lý thành công! Vui lòng chọn bản ghi tiếp theo.")
            self.view.evidence_viewer.btn_approve.hide()
            self.view.evidence_viewer.btn_reject.hide()
            
            if new_status == 1: 
                self.view.evidence_viewer.btn_print.show()
                msg = "Đã DUYỆT biên bản!"
            else:              
                self.view.evidence_viewer.btn_print.hide()
                msg = "Đã HỦY BỎ bản ghi!"
                
            logger.info(f"{msg} (ID: {record_id})")
        else:
            QMessageBox.warning(self.view, "Lỗi", "Không thể cập nhật trạng thái vào Cơ sở dữ liệu.")

    @pyqtSlot(int)
    def handle_print_ticket(self, record_id: int) -> None:
        if not record_id: 
            return

        record_data = None
        for item in self.view.data_table.table.selectedItems():
            if item.column() == 0:
                record_data = item.data(Qt.ItemDataRole.UserRole)
                break
                
        if not record_data: return

        from core.rules import ViolationRegistry, VehicleRegistry
        from shared.utils.enums import TrafficVehicleType, ViolationType
        from features.violation.ticket_generator import TicketGenerator
        from PyQt6.QtWidgets import QFileDialog
        import os, subprocess, platform

        ui_error = record_data.get('ma_loi_vi_pham')
        for v_type in ViolationType:
            if ViolationRegistry.get_code(v_type) == ui_error:
                ui_error = ViolationRegistry.get_name(v_type)
                break

        raw_vehicle = record_data.get('loai_phuong_tien', '')
        try: ui_vehicle = VehicleRegistry.get_name(TrafficVehicleType[raw_vehicle])
        except: ui_vehicle = raw_vehicle

        raw_time = record_data.get('thoi_gian_vi_pham')
        time_format_vn = raw_time.strftime("%H giờ %M phút, ngày %d tháng %m năm %Y")
        time_str_file = raw_time.strftime("%Hh%Mm%Ss")
        
        raw_plate = record_data.get('bien_so_xe', '').strip()
        if not raw_plate or raw_plate.lower() in ["chưa rõ", "không xác định", "unknown"]:
            plate = "-"
        else:
            plate = raw_plate

        tuyen_vao = record_data.get('tuyen_duong_vao', '')
        tuyen_ra = record_data.get('tuyen_duong_ra', '')
        
        if tuyen_vao and tuyen_ra:
            dia_diem = f"{tuyen_vao} - {tuyen_ra}"
        else:
            dia_diem = record_data.get('ten_camera', 'Không xác định')
        
        print_data = {
            'bien_so_xe': plate,
            'thoi_gian_vi_pham_vn': time_format_vn,
            'time_str': time_str_file,
            'dia_diem': dia_diem,
            'loi_vi_pham': ui_error
        }

        default_name = f"BienBan_{plate}_{raw_time.strftime('%Y%m%d')}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(
            self.view, "Lưu Biên Bản PDF", default_name, "PDF Files (*.pdf)"
        )

        if save_path:
            evidence_dir = record_data.get('duong_dan_bang_chung', '')
            
            success = TicketGenerator.generate_pdf(print_data, evidence_dir, save_path)
            
            if success:
                if platform.system() == 'Darwin':      
                    subprocess.call(('open', save_path))
                elif platform.system() == 'Windows':    
                    os.startfile(save_path)
                else:                                  
                    subprocess.call(('xdg-open', save_path))
            else:
                QMessageBox.critical(self.view, "Lỗi", "Không thể tạo file PDF.")
    

    def _load_camera_filter(self) -> None:
        """Lấy danh mục Camera từ CSDL và đẩy xuống View (FilterPanel)"""
        try:
            cameras = self.db.cameras.get_all()
            self.view.filter_panel.load_cameras(cameras)
        except Exception as e:
            logger.error(f"Lỗi khi nạp danh sách camera: {e}")         
