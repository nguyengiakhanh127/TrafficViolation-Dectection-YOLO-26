from fastapi import APIRouter, Depends, HTTPException, Request
from web.backend.services.stats_service import StatsService
from web.backend.security.auth import get_current_user, TokenData

router = APIRouter()

def get_service(request: Request):
    return StatsService(request.app.state.db.db_pool)

@router.get("/overview")
async def get_overview(request: Request, current_user: TokenData = Depends(get_current_user)):
    """Thống kê tổng quan cho dashboard."""
    try:
        return get_service(request).get_overview()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/by-day")
async def get_by_day(
    request: Request,
    days: int = 7,
    current_user: TokenData = Depends(get_current_user)
):
    """Vi phạm theo ngày — N ngày gần nhất."""
    try:
        return get_service(request).get_violations_by_day(days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/by-type")
async def get_by_type(request: Request, current_user: TokenData = Depends(get_current_user)):
    """Phân loại vi phạm theo mã lỗi."""
    try:
        return get_service(request).get_violations_by_type()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/by-vehicle")
async def get_by_vehicle(request: Request, current_user: TokenData = Depends(get_current_user)):
    """Phân loại vi phạm theo loại phương tiện."""
    try:
        return get_service(request).get_violations_by_vehicle()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
