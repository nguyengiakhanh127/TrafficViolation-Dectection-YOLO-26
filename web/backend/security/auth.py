import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ── Config ───────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET", "traffic-ai-super-secret-key-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 giờ

# ── Tài khoản cứng (đọc từ .env, mặc định nếu chưa set) ──
USERS_DB = {
    os.getenv("ADMIN_USER", "admin"): {
        "username": os.getenv("ADMIN_USER", "admin"),
        "password": os.getenv("ADMIN_PASS", "admin123"),
        "role": "admin",
        "full_name": "Quản trị viên"
    },
    os.getenv("REVIEWER_USER", "reviewer"): {
        "username": os.getenv("REVIEWER_USER", "reviewer"),
        "password": os.getenv("REVIEWER_PASS", "review123"),
        "role": "reviewer",
        "full_name": "Kiểm duyệt viên"
    },
}

# ── Schemas ──────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# ── Helpers ──────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(username: str, password: str):
    user = USERS_DB.get(username)
    if not user:
        return None
    if user["password"] != password:
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        return TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception

def require_admin(current_user: TokenData = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền truy cập")
    return current_user
