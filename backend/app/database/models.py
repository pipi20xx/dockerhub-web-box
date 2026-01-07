from sqlalchemy import Boolean, Column, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from .database import Base

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    build_context = Column(String, nullable=False)
    dockerfile_path = Column(String, nullable=False)
    local_image_name = Column(String, nullable=False)
    registry_url = Column(String, nullable=False)
    repo_image_name = Column(String, nullable=False)
    no_cache = Column(Boolean, default=False, nullable=False)
    auto_cleanup = Column(Boolean, default=True, nullable=False)
    platforms = Column(String, default="linux/amd64", nullable=False) # 逗号分隔的平台列表
    credential_id = Column(String, ForeignKey("credentials.id"), nullable=True)
    proxy_id = Column(String, ForeignKey("proxies.id"), nullable=True)
    backup_ignore_patterns = Column(String, nullable=True, default="")

class Credential(Base):
    __tablename__ = "credentials"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    registry_url = Column(String, nullable=False)
    username = Column(String, nullable=False)
    encrypted_password = Column(String, nullable=False)

class Proxy(Base):
    __tablename__ = "proxies"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    url = Column(String, nullable=False)

class TaskLog(Base):
    __tablename__ = "task_logs"
    id = Column(String, primary_key=True, index=True) # This will be our task_id
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String, nullable=False)
    status = Column(String, default="PENDING", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())