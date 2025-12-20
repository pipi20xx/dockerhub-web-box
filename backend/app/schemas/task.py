from pydantic import BaseModel
from datetime import datetime

class TaskLogBase(BaseModel):
    id: str
    project_id: str
    tag: str
    status: str
    created_at: datetime

class TaskLog(TaskLogBase):
    class Config:
        from_attributes = True