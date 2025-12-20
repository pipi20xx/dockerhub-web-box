from pathlib import Path

# --- 路径配置 ---
# ✨ 核心修正：我们重新定义路径的计算方式，使其更健壮

# /app/app/core/config.py
# __file__ 是当前文件的路径

# /app/app
# Path(__file__).parent.parent 是 /app/app
APP_MODULE_DIR = Path(__file__).parent.parent 

# /app
# APP_MODULE_DIR.parent 是 /app，这是我们在Dockerfile中设置的工作目录
APP_ROOT_DIR = APP_MODULE_DIR.parent

# 现在，DATA_DIR 会被正确地计算为 /app/data
DATA_DIR = APP_ROOT_DIR / "data"

LOG_DIR = DATA_DIR / "logs"
BACKUP_DIR = DATA_DIR / "backups"
DATABASE_PATH = DATA_DIR / "projects.db"

# --- 数据库URL ---
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# --- 目录初始化 ---
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

# --- 备份配置 ---
BACKUP_IGNORE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".git",
    "node_modules",
    "target",
    ".vscode",
    ".idea",
    "dist",
    "build",
    "*.log"
]

# --- 任务管理 ---
TASK_MANAGER = {}
TASK_LOG_SENTINEL = "---TASK-COMPLETE---"