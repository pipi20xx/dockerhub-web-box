import uuid
import asyncio
import multiprocessing
from typing import List
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ....core.config import TASK_MANAGER, LOG_DIR, TASK_LOG_SENTINEL
from ....database import crud
from ....database.database import get_db
from ....services.docker_runner import run_docker_task
from ....schemas import task as task_schema

router = APIRouter()

@router.post("/execute/{project_id}")
def execute_task_endpoint(project_id: str, tag: str, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    registry, cred, proxy = None, None, None
    if project.registry_id:
        registry = crud.get_registry(db, project.registry_id)
        if registry and registry.credential_id:
            cred = crud.get_credential(db, registry.credential_id)
    
    if project.proxy_id:
        proxy = crud.get_proxy(db, project.proxy_id)

    task_id = str(uuid.uuid4())
    TASK_MANAGER[task_id] = {"status": "PENDING"}

    crud.create_task_log(db=db, project_id=project_id, task_id=task_id, tag=tag)
    
    project_dict = {c.name: getattr(project, c.name) for c in project.__table__.columns}
    # 构造带协议头的完整 URL
    if registry:
        protocol = "https" if registry.is_https else "http"
        # 清洗可能存在的重复协议头
        clean_url = registry.url.replace("https://", "").replace("http://", "")
        full_reg_url = f"{protocol}://{clean_url}"
    else:
        full_reg_url = "https://docker.io"

    project_dict['registry_url'] = full_reg_url
    
    cred_dict = {c.name: getattr(cred, c.name) for c in cred.__table__.columns} if cred else None
    if cred_dict:
        cred_dict['registry_url'] = full_reg_url

    proxy_dict = {c.name: getattr(proxy, c.name) for c in proxy.__table__.columns} if proxy else None
    
    process = multiprocessing.Process(
        target=run_docker_task, 
        args=(task_id, project_dict, tag, cred_dict, proxy_dict)
    )
    process.daemon = True
    process.start()

    return {"task_id": task_id}

@router.websocket("/logs/{task_id}")
async def websocket_log_stream(websocket: WebSocket, task_id: str):
    await websocket.accept()
    log_file = LOG_DIR / f"{task_id}.log"
    
    retries = 10
    while not log_file.exists() and retries > 0:
        await asyncio.sleep(0.5)
        retries -= 1

    if not log_file.exists():
        await websocket.send_text(f"❌ 错误: 任务 {task_id} 的日志文件未能创建。")
        await websocket.close()
        return

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if TASK_LOG_SENTINEL in line:
                    break
                await websocket.send_text(line.strip())

            while TASK_LOG_SENTINEL not in line:
                line = f.readline()
                if line:
                    if TASK_LOG_SENTINEL in line:
                        break
                    await websocket.send_text(line.strip())
                else:
                    await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        print(f"Client for task {task_id} disconnected.")
    except Exception as e:
        print(f"读取日志时发生错误: {e}")
        try:
            await websocket.send_text(f"❌ 读取日志时发生错误: {e}")
        except:
            pass
    finally:
        await websocket.close()

@router.get("/projects/{project_id}/logs", response_model=List[task_schema.TaskLog])
def get_project_logs(project_id: str, db: Session = Depends(get_db)):
    """获取指定项目的所有历史任务记录"""
    return crud.get_task_logs_for_project(db, project_id=project_id)

@router.get("/logs/{task_id}/content", response_class=PlainTextResponse)
def get_log_content(task_id: str):
    """获取单个任务日志文件的纯文本内容"""
    log_file = LOG_DIR / f"{task_id}.log"
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="日志文件未找到")
    return PlainTextResponse(log_file.read_text(encoding='utf-8'))

# ✨ --- 核心修正：调整了下面两个DELETE路由的顺序 --- ✨

# 1. 将固定路径的路由放在前面，让它被优先匹配
@router.delete("/logs/clear_all", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_logs(db: Session = Depends(get_db)):
    """删除所有的任务日志记录和对应的文件"""
    crud.delete_all_task_logs(db)
    return None

# 2. 将带有路径参数的路由放在后面
@router.delete("/logs/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_single_log(task_id: str, db: Session = Depends(get_db)):
    """删除指定的单个任务日志记录和对应的文件"""
    deleted_task = crud.delete_task_log(db, task_id=task_id)
    if deleted_task is None:
        raise HTTPException(status_code=404, detail="日志未找到")
    return None