class StatsRepository:
    def __init__(self, pool):
        self.pool = pool

    def get_violations_by_day(self, days: int) -> dict:
        """Thống kê vi phạm theo ngày (N ngày gần nhất)."""
        query = """
            SELECT DATE(thoi_gian_vi_pham) AS ngay, COUNT(id) AS so_luong
            FROM ho_so_vi_pham
            WHERE thoi_gian_vi_pham >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY DATE(thoi_gian_vi_pham)
            ORDER BY ngay ASC
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (days,))
            rows = cursor.fetchall()
            
            labels = []
            counts = []
            for row in rows:
                ngay_str = row['ngay'].strftime("%Y-%m-%d") if hasattr(row['ngay'], 'strftime') else str(row['ngay'])
                labels.append(ngay_str)
                counts.append(row['so_luong'])
                
            return {
                "labels": labels,
                "counts": counts
            }
        finally:
            conn.close()

    def get_violations_by_type(self) -> dict:
        """Phân loại vi phạm theo mã lỗi."""
        query = """
            SELECT COALESCE(ma_loi_vi_pham, 'Không rõ') AS loai, COUNT(id) AS so_luong
            FROM ho_so_vi_pham
            GROUP BY ma_loi_vi_pham
            ORDER BY so_luong DESC
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()
            
            return {
                "labels": [r['loai'] for r in rows],
                "counts": [r['so_luong'] for r in rows]
            }
        finally:
            conn.close()

    def get_violations_by_vehicle(self) -> dict:
        """Phân loại vi phạm theo loại phương tiện."""
        query = """
            SELECT COALESCE(loai_phuong_tien, 'Không rõ') AS loai, COUNT(id) AS so_luong
            FROM ho_so_vi_pham
            GROUP BY loai_phuong_tien
            ORDER BY so_luong DESC
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()
            
            return {
                "labels": [r['loai'] for r in rows],
                "counts": [r['so_luong'] for r in rows]
            }
        finally:
            conn.close()
