from pydantic import BaseModel
from typing import Literal, List

class Backup(BaseModel):
    filename: str
    size: int
    created_at: str
    remark: str | None = None

class BackupCreateRequest(BaseModel):
    ignore_patterns: List[str]
    remark: str | None = None

class RestoreRequest(BaseModel):
    backup_filename: str
    strategy: Literal["overwrite", "clear_and_overwrite"]