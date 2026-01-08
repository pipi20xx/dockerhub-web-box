from pydantic import BaseModel, validator
import re

class ProjectBase(BaseModel):
    name: str
    build_context: str
    dockerfile_path: str
    local_image_name: str | None = None
    repo_image_name: str
    no_cache: bool = False
    auto_cleanup: bool = True
    platforms: str = "linux/amd64"
    registry_id: str | None = None
    proxy_id: str | None = None
    backup_ignore_patterns: str | None = ""

    @validator('local_image_name')
    def validate_local_image_name(cls, v):
        if v is None or v == "":
            return v
        pattern = r'^[a-z0-9]+(?:[._-][a-z0-9]+)*$'
        if not re.match(pattern, v):
            raise ValueError('本地镜像名格式不正确 (只能小写字母/数字/._-，且不含斜杠)。')
        return v

    @validator('repo_image_name')
    def validate_repo_image_name(cls, v):
        parts = v.split('/')
        pattern = r'^[a-z0-9]+(?:[._-][a-z0-9]+)*$'
        for part in parts:
            if not re.match(pattern, part):
                raise ValueError(f"仓库镜像名的 '{part}' 部分格式不正确 (只能小写字母/数字/._-)。")
        return v

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class Project(ProjectBase):
    id: str

    class Config:
         from_attributes = True