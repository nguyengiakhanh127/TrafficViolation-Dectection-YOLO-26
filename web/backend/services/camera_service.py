from shared.database.database_service import CameraRepository, MySQLConnectionPool

class CameraService:
    def __init__(self, pool: MySQLConnectionPool):
        self._repo = CameraRepository(pool)

    def get_all_cameras(self) -> list:
        return self._repo.get_all()

    def add_camera(self, ten_camera: str, tuyen_vao: str, tuyen_ra: str) -> int:
        return self._repo.add(ten_camera, tuyen_vao, tuyen_ra)
