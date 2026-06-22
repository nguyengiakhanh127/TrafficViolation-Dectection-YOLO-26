from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional
from web.backend.services.violation_service import ViolationService
from web.backend.security.auth import get_current_user, TokenData

router = APIRouter()

def get_service(request: Request):
    return ViolationService(request.app.state.db.db_pool)

class StatusUpdate(BaseModel):
    trang_thai: int  # 1 = duyệt, -1 = từ chối, 0 = chờ

class LicensePlateUpdate(BaseModel):
    bien_so: str

@router.get("")
async def list_violations(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    bien_so: Optional[str] = None,
    ma_loi: Optional[str] = None,
    loai_xe: Optional[str] = None,
    trang_thai: Optional[int] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Danh sách vi phạm với filter & phân trang."""
    filters = {}
    if bien_so:    filters["bien_so"] = bien_so
    if ma_loi:     filters["ma_loi"] = ma_loi
    if loai_xe:    filters["loai_xe"] = loaixe = loai_xe
    if trang_thai is not None: filters["trang_thai"] = trang_thai
    try:
        data = get_service(request).get_list(limit=limit, offset=offset, filters=filters)
        total = get_service(request).get_total_count(filters=filters)
        return {"data": data, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/count")
async def count_violations(
    request: Request,
    trang_thai: Optional[int] = None,
    current_user: TokenData = Depends(get_current_user)
):
    filters = {}
    if trang_thai is not None:
        filters["trang_thai"] = trang_thai
    return {"count": get_service(request).get_total_count(filters=filters)}

@router.get("/{record_id}/evidence")
async def get_evidence_files(
    request: Request,
    record_id: int,
    current_user: TokenData = Depends(get_current_user)
):
    """Trả về danh sách file bằng chứng (ảnh, video) của một vi phạm."""
    try:
        res = get_service(request).get_evidence_files(record_id)
        if res is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi")
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{record_id}/status")
async def update_status(
    request: Request,
    record_id: int,
    body: StatusUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Duyệt hoặc từ chối vi phạm — Admin & Reviewer."""
    success = get_service(request).update_status(record_id, body.trang_thai)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi")
    return {"success": True, "record_id": record_id, "trang_thai": body.trang_thai}

@router.patch("/{record_id}/license-plate")
async def update_license_plate(
    request: Request,
    record_id: int,
    body: LicensePlateUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Cập nhật biển số thủ công."""
    success = get_service(request).update_license_plate(record_id, body.bien_so)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi")
    return {"success": True, "bien_so": body.bien_so}

@router.delete("/{record_id}")
async def delete_violation(
    request: Request,
    record_id: int,
    current_user: TokenData = Depends(get_current_user)
):
    """Xóa bản ghi vi phạm."""
    success = get_service(request).delete(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi")
    return {"success": True, "record_id": record_id}
