from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import tarfile
import os
import shutil
import json
import subprocess
from pathlib import Path
from datetime import datetime
import fnmatch

from ....database import crud
from ....database.database import get_db
from ....core.config import BACKUP_DIR
from ....schemas.backup import Backup, BackupCreateRequest, RestoreRequest
from ....schemas.project import ProjectUpdate

router = APIRouter()

def get_project_or_404(db: Session, project_id: str):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

def get_project_backup_dir(project_name: str) -> Path:
    project_backup_dir = BACKUP_DIR / project_name
    project_backup_dir.mkdir(parents=True, exist_ok=True)
    return project_backup_dir

@router.post("/{project_id}", response_model=Backup)
def create_backup(project_id: str, request: BackupCreateRequest, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    
    # 1. Update project's backup_ignore_patterns in DB
    ignore_patterns_str = "\n".join(request.ignore_patterns)
    if project.backup_ignore_patterns != ignore_patterns_str:
        crud.update_project(db, project, ProjectUpdate(
            name=project.name, 
            build_context=project.build_context,
            dockerfile_path=project.dockerfile_path,
            local_image_name=project.local_image_name,
            registry_url=project.registry_url,
            repo_image_name=project.repo_image_name,
            backup_ignore_patterns=ignore_patterns_str
        ))
        # Refresh project to get latest state
        project = get_project_or_404(db, project_id)

    build_path = Path(project.build_context)
    
    if not build_path.exists() or not build_path.is_dir():
         raise HTTPException(status_code=400, detail=f"Build path {build_path} does not exist or is not a directory")

    project_backup_dir = get_project_backup_dir(project.name)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{project.name}-{timestamp}.7z"
    filepath = project_backup_dir / filename
    
    # Sidecar metadata file
    meta_filename = f"{project.name}-{timestamp}.json"
    meta_filepath = project_backup_dir / meta_filename

    # Create a temporary file list for 7z
    list_file_path = project_backup_dir / f"list_{timestamp}.txt"

    try:
        # 1. Manually collect files to include based on ignore patterns
        include_files = []
        for root, dirs, files in os.walk(build_path):
            # Calculate relative path from build_path
            rel_root = os.path.relpath(root, build_path)
            if rel_root == ".":
                rel_root = ""
            
            # Filter directories in-place to prevent os.walk from entering them
            dirs_to_keep = []
            for d in dirs:
                rel_dir = os.path.join(rel_root, d).replace(os.sep, '/')
                is_ignored = False
                for pattern in request.ignore_patterns:
                    p = pattern.strip()
                    if not p: continue
                    clean_pattern = p.lstrip('/')
                    if '/' in clean_pattern:
                        if fnmatch.fnmatch(rel_dir, clean_pattern):
                            is_ignored = True
                            break
                    else:
                        if fnmatch.fnmatch(d, clean_pattern):
                            is_ignored = True
                            break
                if not is_ignored:
                    dirs_to_keep.append(d)
            dirs[:] = dirs_to_keep # This controls the recursion

            # Collect files
            for f in files:
                rel_file = os.path.join(rel_root, f).replace(os.sep, '/')
                is_ignored = False
                for pattern in request.ignore_patterns:
                    p = pattern.strip()
                    if not p: continue
                    clean_pattern = p.lstrip('/')
                    if '/' in clean_pattern:
                        if fnmatch.fnmatch(rel_file, clean_pattern):
                            is_ignored = True
                            break
                    else:
                        if fnmatch.fnmatch(f, clean_pattern):
                            is_ignored = True
                            break
                if not is_ignored:
                    # 7z @listfile needs paths relative to the working directory or absolute
                    # We will run 7z in build_path, so we use relative paths
                    include_files.append(os.path.join(rel_root, f))

        # 2. Write the list to a temporary file
        with open(list_file_path, 'w', encoding='utf-8') as f:
            for item in include_files:
                f.write(f"{item}\n")

        # 3. Call 7z using the list file
        # -mx=1: Fast compression
        # -m0=lzma2: Force LZMA2
        # -mf=off: Explicitly disable all filters (BCJ/BCJ2) to avoid "Unknown Method" errors
        # -mmt=on: Multi-threading
        cmd = [
            "7z", "a", 
            "-t7z", 
            "-mx=1", 
            "-m0=lzma2",
            "-mf=off",
            "-mmt=on",
            str(filepath), 
            f"@{str(list_file_path)}"
        ]
        
        result = subprocess.run(cmd, cwd=build_path, capture_output=True, text=True)
        if result.returncode != 0:
             raise Exception(f"7z failed (code {result.returncode}): {result.stderr}")
        
        # Write metadata
        if request.remark:
             with open(meta_filepath, 'w', encoding='utf-8') as f:
                 json.dump({"remark": request.remark}, f)
                 
    finally:
        # Cleanup the temporary list file
        if list_file_path.exists():
            list_file_path.unlink()

    stat = filepath.stat()
    return Backup(
        filename=filename,
        size=stat.st_size,
        created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
        remark=request.remark
    )

@router.get("/{project_id}", response_model=List[Backup])
def list_backups(project_id: str, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    project_backup_dir = get_project_backup_dir(project.name)
    
    backups = []
    if project_backup_dir.exists():
        # Support both .tar.gz and .7z
        files = list(project_backup_dir.glob("*.tar.gz")) + list(project_backup_dir.glob("*.7z"))
        for file in files:
            stat = file.stat()
            remark = None
            
            # Check for sidecar metadata
            # Replace extension with .json
            if file.name.endswith('.tar.gz'):
                meta_file = project_backup_dir / file.name.replace('.tar.gz', '.json')
            else:
                meta_file = project_backup_dir / file.name.replace('.7z', '.json')
            
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        remark = data.get("remark")
                except:
                    pass

            backups.append(Backup(
                filename=file.name,
                size=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                remark=remark
            ))
    
    # Sort by creation time descending
    backups.sort(key=lambda x: x.created_at, reverse=True)
    return backups

@router.delete("/{project_id}/clear_all")
def clear_all_backups(project_id: str, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    project_backup_dir = get_project_backup_dir(project.name)
    
    if not project_backup_dir.exists():
        return {"status": "success", "message": "No backups to delete"}

    try:
        # Delete all .7z, .tar.gz and .json files in the project backup directory
        count = 0
        for ext in ["*.7z", "*.tar.gz", "*.json"]:
            for file in project_backup_dir.glob(ext):
                file.unlink()
                count += 1
        return {"status": "success", "message": f"Cleared {count} backup related files"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear backups: {str(e)}")

@router.delete("/{project_id}/{filename}")
def delete_backup(project_id: str, filename: str, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    project_backup_dir = get_project_backup_dir(project.name)
    filepath = project_backup_dir / filename
    
    if not filepath.exists():
         raise HTTPException(status_code=404, detail="Backup file not found")
         
    # Security check: ensure the file is within the project's backup directory
    try:
        filepath.resolve().relative_to(project_backup_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid backup file path")

    try:
        filepath.unlink()
        
        # Try delete metadata sidecar
        meta_filename = filename.replace('.tar.gz', '.json').replace('.7z', '.json')
        meta_file = project_backup_dir / meta_filename
        if meta_file.exists():
            meta_file.unlink()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {str(e)}")
        
    return {"status": "success", "message": "Backup deleted"}

@router.post("/{project_id}/restore")
def restore_backup(project_id: str, request: RestoreRequest, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    project_backup_dir = get_project_backup_dir(project.name)
    filepath = project_backup_dir / request.backup_filename
    build_path = Path(project.build_context)

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    
    # Security check
    try:
        filepath.resolve().relative_to(project_backup_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid backup file path")

    if not build_path.exists():
         # If build path doesn't exist, we can try to create it, but usually it should exist.
         # For restore, creating it is fine.
         build_path.mkdir(parents=True, exist_ok=True)

    try:
        if request.strategy == "clear_and_overwrite":
            # Clear directory content but keep the directory itself
            for item in build_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        
        # Restore
        if filepath.suffix == ".7z":
            # 7z x [archive] -o[output_dir] -y
            cmd = ["7z", "x", str(filepath), f"-o{str(build_path)}", "-y"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"7z restore failed: {result.stderr}")
        else:
            with tarfile.open(filepath, "r:gz") as tar:
                tar.extractall(path=build_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")

    return {"status": "success", "message": f"Project restored using {request.strategy} strategy"}
