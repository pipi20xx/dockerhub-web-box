from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .database.database import engine, check_and_migrate_db
from .database import models
from .api.v1.router import api_router

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

# 自动检查并迁移数据库（修复缺少的列）
check_and_migrate_db()

app = FastAPI(title="Docker Web Pusher")

# 包含所有 v1 版本的 API 路由
app.include_router(api_router, prefix="/api/v1")

# --- 静态文件托管与SPA支持 (标准方案) ---

# 定义静态文件目录的正确路径
# 在容器中, __file__ 是 /app/app/main.py, parent.parent 是 /app
# 所以 STATIC_FILES_DIR 正确指向 /app/static
STATIC_FILES_DIR = Path(__file__).parent.parent / "static"

# ✨ 核心修改：将所有非API请求都交由StaticFiles处理
# html=True 参数是关键：它告诉StaticFiles，对于任何未匹配到具体文件的路径
# (例如 / 或 /some/vue/route)，都应该返回 `index.html`。
# 这完美地支持了Vue Router的History模式，且无需任何额外路由或中间件。
app.mount("/", StaticFiles(directory=STATIC_FILES_DIR, html=True), name="static")