from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from web.backend.services.camera_service import CameraService
from web.backend.security.auth import get_current_user, require_admin, TokenData

router = APIRouter()

def get_service(request: Request):
    return CameraService(request.app.state.db.db_pool)

class CameraCreate(BaseModel):
    ten_camera: str
    tuyen_vao: Optional[str] = ""
    tuyen_ra: Optional[str] = ""

@router.get("")
async def list_cameras(request: Request, current_user: TokenData = Depends(get_current_user)):
    """Lấy danh sách tất cả camera — Admin & Reviewer đều xem được."""
    try:
        return get_service(request).get_all_cameras()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", status_code=201)
async def create_camera(request: Request, body: CameraCreate, current_user: TokenData = Depends(require_admin)):
    """Thêm camera mới — chỉ Admin."""
    try:
        new_id = get_service(request).add_camera(body.ten_camera, body.tuyen_vao, body.tuyen_ra)
        return {"id": new_id, "ten_camera": body.ten_camera}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
