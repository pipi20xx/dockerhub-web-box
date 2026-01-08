import uuid
import os # ✨ 新增：导入os模块以操作文件
from pathlib import Path # ✨ 新增：导入Path模块
from sqlalchemy.orm import Session
from . import models
from ..schemas import project as project_schema, credential as cred_schema, proxy as proxy_schema, registry as registry_schema
from ..core.config import LOG_DIR
 # ✨ 新增：从config导入LOG_DIR

def encrypt(data: str) -> str: return data
def decrypt(token: str) -> str: return token

# --- Project CRUD ---
def get_project(db: Session, project_id: str):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

def get_projects(db: Session):
    return db.query(models.Project).order_by(models.Project.name).all()

def create_project(db: Session, project: project_schema.ProjectCreate):
    db_project = models.Project(id=str(uuid.uuid4()), **project.dict())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def update_project(db: Session, db_project: models.Project, project_in: project_schema.ProjectUpdate):
    update_data = project_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_project, key, value)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def delete_project(db: Session, db_project: models.Project):
    db.delete(db_project)
    db.commit()
    return db_project

# --- Registry CRUD ---
def get_registry(db: Session, registry_id: str):
    return db.query(models.Registry).filter(models.Registry.id == registry_id).first()

def get_registry_by_name(db: Session, name: str):
    return db.query(models.Registry).filter(models.Registry.name == name).first()

def get_registries(db: Session):
    return db.query(models.Registry).order_by(models.Registry.name).all()

def create_registry(db: Session, registry: registry_schema.RegistryCreate):
    db_registry = models.Registry(id=str(uuid.uuid4()), **registry.dict())
    db.add(db_registry)
    db.commit()
    db.refresh(db_registry)
    return db_registry

def update_registry(db: Session, db_registry: models.Registry, registry_in: registry_schema.RegistryCreate):
    update_data = registry_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_registry, key, value)
    db.add(db_registry)
    db.commit()
    db.refresh(db_registry)
    return db_registry

def delete_registry(db: Session, db_registry: models.Registry):
    db.delete(db_registry)
    db.commit()
    return db_registry

# --- Credential CRUD ---
def get_credential(db: Session, cred_id: str):
    return db.query(models.Credential).filter(models.Credential.id == cred_id).first()

def get_credential_by_name(db: Session, name: str):
    return db.query(models.Credential).filter(models.Credential.name == name).first()

def get_credentials(db: Session):
    return db.query(models.Credential).order_by(models.Credential.name).all()

def create_credential(db: Session, cred: cred_schema.CredentialCreate):
    encrypted_password = encrypt(cred.password)
    db_cred = models.Credential(id=str(uuid.uuid4()), name=cred.name, username=cred.username, encrypted_password=encrypted_password)
    db.add(db_cred)
    db.commit()
    db.refresh(db_cred)
    return db_cred

def update_credential(db: Session, db_cred: models.Credential, cred_in: cred_schema.CredentialUpdate):
    update_data = cred_in.dict(exclude_unset=True)
    if 'password' in update_data and update_data['password']:
        update_data['encrypted_password'] = encrypt(update_data['password'])
        del update_data['password']
    
    for key, value in update_data.items():
        setattr(db_cred, key, value)

    db.add(db_cred)
    db.commit()
    db.refresh(db_cred)
    return db_cred

def delete_credential(db: Session, db_cred: models.Credential):
    db.delete(db_cred)
    db.commit()
    return db_cred

# --- Proxy CRUD ---
def get_proxy(db: Session, proxy_id: str):
    return db.query(models.Proxy).filter(models.Proxy.id == proxy_id).first()

def get_proxy_by_name(db: Session, name: str):
    return db.query(models.Proxy).filter(models.Proxy.name == name).first()
    
def get_proxies(db: Session):
    return db.query(models.Proxy).order_by(models.Proxy.name).all()

def create_proxy(db: Session, proxy: proxy_schema.ProxyCreate):
    db_proxy = models.Proxy(id=str(uuid.uuid4()), **proxy.dict())
    db.add(db_proxy)
    db.commit()
    db.refresh(db_proxy)
    return db_proxy

def update_proxy(db: Session, db_proxy: models.Proxy, proxy_in: proxy_schema.ProxyUpdate):
    update_data = proxy_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_proxy, key, value)
    db.add(db_proxy)
    db.commit()
    db.refresh(db_proxy)
    return db_proxy

def delete_proxy(db: Session, db_proxy: models.Proxy):
    db.delete(db_proxy)
    db.commit()
    return db_proxy

# --- TaskLog CRUD ---
def create_task_log(db: Session, project_id: str, task_id: str, tag: str):
    db_task = models.TaskLog(id=task_id, project_id=project_id, tag=tag)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_task_logs_for_project(db: Session, project_id: str):
    return db.query(models.TaskLog).filter(models.TaskLog.project_id == project_id).order_by(models.TaskLog.created_at.desc()).all()

def update_task_status(db: Session, task_id: str, new_status: str):
    db_task = db.query(models.TaskLog).filter(models.TaskLog.id == task_id).first()
    if db_task:
        db_task.status = new_status
        db.commit()
        db.refresh(db_task)
    return db_task

# ✨ --- 新增：删除单条任务日志的函数 --- ✨
def delete_task_log(db: Session, task_id: str):
    # 先从数据库查找记录
    db_task = db.query(models.TaskLog).filter(models.TaskLog.id == task_id).first()
    if not db_task:
        return None # 如果找不到记录，直接返回

    # 删除数据库记录
    db.delete(db_task)
    db.commit()

    # 删除对应的物理日志文件
    log_file_path = LOG_DIR / f"{task_id}.log"
    if log_file_path.exists():
        log_file_path.unlink() # 使用pathlib的unlink方法删除文件

    return db_task

# ✨ --- 新增：删除所有任务日志的函数 --- ✨
def delete_all_task_logs(db: Session):
    # 删除数据库中所有 TaskLog 记录
    num_rows_deleted = db.query(models.TaskLog).delete()
    db.commit()

    # 删除物理日志文件夹下的所有 .log 文件
    for log_file in LOG_DIR.glob("*.log"):
        try:
            log_file.unlink()
        except OSError as e:
            print(f"Error deleting file {log_file}: {e}")
            
    return num_rows_deleted