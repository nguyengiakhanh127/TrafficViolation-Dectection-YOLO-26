from shared.database.database_service import ViolationRepository, CameraRepository, MySQLConnectionPool
from web.backend.services.stats_repository import StatsRepository

class StatsService:
    def __init__(self, pool: MySQLConnectionPool):
        self._v_repo = ViolationRepository(pool)
        self._c_repo = CameraRepository(pool)
        self._stats = StatsRepository(pool)

    def get_overview(self) -> dict:
        total     = self._v_repo.get_total_count()
        pending   = self._v_repo.get_total_count({"trang_thai": 0})
        approved  = self._v_repo.get_total_count({"trang_thai": 1})
        rejected  = self._v_repo.get_total_count({"trang_thai": -1})
        cameras   = len(self._c_repo.get_all())
        return {
            "total_violations": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "total_cameras": cameras,
        }

    def get_violations_by_day(self, days: int) -> dict:
        return self._stats.get_violations_by_day(days)

    def get_violations_by_type(self) -> dict:
        return self._stats.get_violations_by_type()

    def get_violations_by_vehicle(self) -> dict:
        return self._stats.get_violations_by_vehicle()
