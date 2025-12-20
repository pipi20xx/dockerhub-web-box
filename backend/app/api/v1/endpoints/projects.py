from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import os

from ....database import crud
from ....database.database import get_db
from ....schemas import project as schema

router = APIRouter()

def validate_project_paths(project: schema.ProjectCreate):
    if not os.path.isabs(project.build_context) or not os.path.isdir(project.build_context):
        raise HTTPException(status_code=400, detail=f"构建上下文路径 '{project.build_context}' 无效或不是一个目录。")
    dockerfile_full_path = os.path.join(project.build_context, project.dockerfile_path)
    if not os.path.isfile(dockerfile_full_path):
        raise HTTPException(status_code=400, detail=f"在构建上下文中找不到Dockerfile: '{dockerfile_full_path}'。")

@router.get("/", response_model=List[schema.Project])
def read_projects(db: Session = Depends(get_db)):
    return crud.get_projects(db)

@router.get("/{project_id}", response_model=schema.Project)
def read_project(project_id: str, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="项目未找到")
    return db_project

@router.post("/", response_model=schema.Project, status_code=201)
def create_project(project: schema.ProjectCreate, db: Session = Depends(get_db)):
    validate_project_paths(project)
    return crud.create_project(db=db, project=project)

@router.put("/{project_id}", response_model=schema.Project)
def update_project(project_id: str, project_in: schema.ProjectUpdate, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="项目未找到")
    validate_project_paths(project_in)
    return crud.update_project(db=db, db_project=db_project, project_in=project_in)

@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="项目未找到")
    crud.delete_project(db, db_project)
    return None

@router.post("/{project_id}/copy", response_model=schema.Project)
def copy_project(project_id: str, db: Session = Depends(get_db)):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="项目未找到")
    
    new_project_data = schema.ProjectCreate(
        name=f"{db_project.name}_copy",
        build_context=db_project.build_context,
        dockerfile_path=db_project.dockerfile_path,
        local_image_name=db_project.local_image_name,
        registry_url=db_project.registry_url,
        repo_image_name=db_project.repo_image_name,
        backup_ignore_patterns=db_project.backup_ignore_patterns
    )
    return crud.create_project(db=db, project=new_project_data)

@router.get("/all/export")
def export_all_data(db: Session = Depends(get_db)):
    projects = crud.get_projects(db)
    credentials = crud.get_credentials(db)
    proxies = crud.get_proxies(db)
    return {
        "version": "1.0",
        "projects": projects,
        "credentials": credentials,
        "proxies": proxies
    }

@router.post("/all/import")
def import_all_data(data: dict, db: Session = Depends(get_db)):
    from uuid import uuid4
    
    cred_map = {}
    for c in data.get("credentials", []):
        name = c.get("name", "MISSING_NAME")
        existing = db.execute(text("SELECT id FROM credentials WHERE name = :name"), {"name": name}).fetchone()
        
        # Store as plain text (crud.encrypt is now an identity function)
        pwd_to_store = c.get("password", "") or c.get("encrypted_password", "")

        c_data = {
            "name": name,
            "registry_url": c.get("registry_url", "MISSING_REGISTRY"),
            "username": c.get("username", "MISSING_USER"),
            "encrypted_password": pwd_to_store
        }
        if existing:
            db.execute(
                text("UPDATE credentials SET registry_url=:registry_url, username=:username, encrypted_password=:encrypted_password WHERE id=:id"),
                {"id": existing[0], **c_data}
            )
            new_id = existing[0]
        else:
            new_id = str(uuid4())
            db.execute(
                text("INSERT INTO credentials (id, name, registry_url, username, encrypted_password) VALUES (:id, :name, :registry_url, :username, :encrypted_password)"),
                {"id": new_id, **c_data}
            )
        cred_map[c.get("id")] = new_id

    proxy_map = {}
    for p in data.get("proxies", []):
        name = p.get("name", "MISSING_NAME")
        existing = db.execute(text("SELECT id FROM proxies WHERE name = :name"), {"name": name}).fetchone()
        p_data = {"name": name, "url": p.get("url", "MISSING_URL")}
        if existing:
            db.execute(text("UPDATE proxies SET url=:url WHERE id=:id"), {"id": existing[0], **p_data})
            new_id = existing[0]
        else:
            new_id = str(uuid4())
            db.execute(text("INSERT INTO proxies (id, name, url) VALUES (:id, :name, :url)"), {"id": new_id, **p_data})
        proxy_map[p.get("id")] = new_id

    for prj in data.get("projects", []):
        name = prj.get("name", "MISSING_NAME")
        existing = db.execute(text("SELECT id FROM projects WHERE name = :name"), {"name": name}).fetchone()
        prj_data = {
            "name": name,
            "build_context": prj.get("build_context", "MISSING_CONTEXT"),
            "dockerfile_path": prj.get("dockerfile_path", "Dockerfile"),
            "local_image_name": prj.get("local_image_name", "missing_image"),
            "registry_url": prj.get("registry_url", "MISSING_REGISTRY"),
            "repo_image_name": prj.get("repo_image_name", "missing_repo"),
            "no_cache": prj.get("no_cache", False),
            "credential_id": cred_map.get(prj.get("credential_id")),
            "proxy_id": proxy_map.get(prj.get("proxy_id")),
            "backup_ignore_patterns": prj.get("backup_ignore_patterns", "")
        }
        if existing:
            cols = ", ".join([f"{k}=:{k}" for k in prj_data.keys()])
            db.execute(text(f"UPDATE projects SET {cols} WHERE id=:id"), {"id": existing[0], **prj_data})
        else:
            new_id = str(uuid4())
            cols = ", ".join(prj_data.keys())
            vals = ", ".join([f":{k}" for k in prj_data.keys()])
            db.execute(text(f"INSERT INTO projects (id, {cols}) VALUES (:id, {vals})"), {"id": new_id, **prj_data})

    db.commit()
    return {"status": "success", "message": "Import completed"}