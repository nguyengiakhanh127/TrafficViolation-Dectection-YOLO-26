import os
import re
from shared.utils.paths import EVIDENCE_DIR
from shared.database.database_service import ViolationRepository, MySQLConnectionPool

class ViolationService:
    def __init__(self, pool: MySQLConnectionPool):
        self._repo = ViolationRepository(pool)

    def get_list(self, limit: int, offset: int, filters: dict) -> list:
        return self._repo.get_list(limit=limit, offset=offset, filters=filters)

    def get_total_count(self, filters: dict) -> int:
        return self._repo.get_total_count(filters=filters)

    def update_status(self, record_id: int, trang_thai: int) -> bool:
        return self._repo.update_status(record_id, trang_thai)

    def update_license_plate(self, record_id: int, bien_so: str) -> bool:
        return self._repo.update_license_plate(record_id, bien_so)

    def delete(self, record_id: int) -> bool:
        return self._repo.delete(record_id)

    def get_evidence_files(self, record_id: int) -> dict:
        """Logic quét thư mục bằng chứng — tách từ router gốc."""
        raw_path = self._repo.get_evidence_path(record_id)
        if raw_path is None:
            return None

        if not raw_path:
            return {"files": [], "folder": ""}

        # Chuẩn hoá và làm sạch raw_path
        raw_path_clean = raw_path.replace("\\", "/")
        
        # Nếu database lưu đường dẫn tuyệt đối chứa EVIDENCE_DIR
        evidence_dir_clean = EVIDENCE_DIR.replace("\\", "/")
        if raw_path_clean.lower().startswith(evidence_dir_clean.lower()):
            clean_rel = raw_path_clean[len(evidence_dir_clean):].lstrip("/")
        else:
            # Dự phòng: Bỏ prefix 'evidence/' hoặc 'Evidence/' nếu có
            clean_rel = re.sub(r'^[Ee]vidence[/\\]', '', raw_path.replace("\\", "/"))
            
        folder_abs = os.path.join(EVIDENCE_DIR, clean_rel.replace("/", os.sep))

        if not os.path.isdir(folder_abs):
            return {"files": [], "folder": clean_rel, "error": "Thu muc bang chung khong ton tai"}

        files = []
        for fname in sorted(os.listdir(folder_abs)):
            fpath = os.path.join(folder_abs, fname)
            if os.path.isfile(fpath):
                ext = fname.lower().rsplit(".", 1)[-1]
                ftype = "image" if ext in ("jpg", "jpeg", "png") else "video" if ext == "mp4" else "other"
                
                # Chuẩn hoá clean_rel dùng / để tạo đường dẫn URL tĩnh
                url_rel = clean_rel.replace("\\", "/")
                # Encode từng phần để tránh lỗi ký tự đặc biệt hoặc dấu cách, giữ nguyên các dấu /
                encoded_segments = [p.replace(" ", "%20") for p in url_rel.split("/") if p]
                url = "/evidence/" + "/".join(encoded_segments) + "/" + fname.replace(" ", "%20")
                files.append({"name": fname, "type": ftype, "url": url})

        return {"files": files, "folder": clean_rel}
