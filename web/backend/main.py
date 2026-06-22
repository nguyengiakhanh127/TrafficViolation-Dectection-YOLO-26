import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from web.backend.security.auth_router import router as auth_router
from web.backend.routes.cameras import router as cameras_router
from web.backend.routes.violations import router as violations_router
from web.backend.routes.stats import router as stats_router
from shared.utils.paths import EVIDENCE_DIR
from shared.database.database_service import DatabaseService

import logging
logger = logging.getLogger("traffic-ai")

# Khởi tạo DB khi server khởi động
try:
    db_service = DatabaseService(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database=os.getenv("DB_NAME", "traffic_ai_db"),
    )
    logger.info("✅ Kết nối MySQL thành công")
except Exception as e:
    logger.warning(f"⚠️ Không thể kết nối MySQL: {e}")
    db_service = None

app = FastAPI(title="Traffic AI Dashboard API", version="1.0.0")
app.state.db = db_service

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ──────────────────────────────────────────
app.include_router(auth_router,       prefix="/api/auth",       tags=["Auth"])
app.include_router(cameras_router,    prefix="/api/cameras",    tags=["Cameras"])
app.include_router(violations_router, prefix="/api/violations", tags=["Violations"])
app.include_router(stats_router,      prefix="/api/stats",      tags=["Stats"])

# ── Mount Evidence folder để xem ảnh bằng chứng ─────────
if os.path.exists(EVIDENCE_DIR):
    app.mount("/evidence", StaticFiles(directory=EVIDENCE_DIR), name="evidence")

# ── Serve Frontend ───────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"),
                        headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="API endpoint not found")
    filepath = os.path.join(FRONTEND_DIR, full_path)
    if os.path.exists(filepath) and os.path.isfile(filepath):
        return FileResponse(filepath)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
