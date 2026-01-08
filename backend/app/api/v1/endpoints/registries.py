import docker
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ....database import crud
from ....database.database import get_db
from ....schemas import registry as registry_schema

router = APIRouter()

@router.post("/test", status_code=200)
def test_registry_connection(registry: registry_schema.RegistryCreate, db: Session = Depends(get_db)):
    """测试仓库连接和凭据是否有效"""
    import requests
    from urllib.parse import urlparse
    
    # 1. 构造强制协议的 URL
    raw_url = registry.url.replace("https://", "").replace("http://", "")
    protocol = "https" if registry.is_https else "http"
    url = f"{protocol}://{raw_url}"
    
    parsed = urlparse(url)
    reg_host = parsed.netloc if parsed.netloc else parsed.path.split('/')[0]
    api_url = f"{url.rstrip('/')}/v2/"

    # 2. 强一致性协议检测：先用 Requests 探测用户选的协议是否真的支持
    try:
        # 尝试连接用户选择的协议
        resp = requests.get(api_url, timeout=5, verify=False)
        # 如果通了（200 或 401 都算协议通了），则继续执行后续逻辑
    except Exception as e:
        # 如果用户选了 HTTPS 但失败了，探测一下是不是其实只支持 HTTP
        if registry.is_https:
            try:
                http_test_url = f"http://{reg_host}/v2/"
                h_resp = requests.get(http_test_url, timeout=3)
                if h_resp.status_code in [200, 401]:
                    return {"status": "warning", "message": f"❌ 协议不匹配: 该仓库似乎只支持 HTTP，请切换设置"}
            except: pass
        raise HTTPException(status_code=400, detail=f"连接失败: 无法通过 {protocol.upper()} 访问该地址")

    # 3. 登录验证逻辑
    if registry.credential_id:
        try:
            client = docker.from_env()
            cred = crud.get_credential(db, registry.credential_id)
            if not cred:
                raise Exception("关联的凭据不存在")
            
            # 执行登录测试
            client.login(username=cred.username, password=cred.encrypted_password, registry=url)
            return {"status": "success", "message": f"✅ 登录成功: 协议和凭据均已验证"}
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg:
                error_msg = "认证失败: 用户名或密码错误"
            raise HTTPException(status_code=400, detail=error_msg)
    
    # 4. 匿名访问逻辑
    else:
        if reg_host in ["docker.io", "index.docker.io", "registry-1.docker.io"]:
            return {"status": "warning", "message": "⚠️ Docker Hub 必须绑定凭据才能执行推送"}
        
        # 根据刚才探测的响应判断
        # 这里 resp 变量在步骤 2 中已经获取到了
        try:
            resp = requests.get(api_url, timeout=5, verify=False)
            if resp.status_code == 200:
                return {"status": "success", "message": "✅ 连接成功: 该仓库允许匿名访问"}
            elif resp.status_code == 401:
                return {"status": "info", "message": "💡 地址有效: 但该仓库需要登录凭据"}
            else:
                return {"status": "error", "message": f"❌ 服务器返回异常状态码: {resp.status_code}"}
        except:
            raise HTTPException(status_code=400, detail="探测失败")

@router.get("/", response_model=List[registry_schema.Registry])
def read_registries(db: Session = Depends(get_db)):
    return crud.get_registries(db)

@router.post("/", response_model=registry_schema.Registry)
def create_registry(registry: registry_schema.RegistryCreate, db: Session = Depends(get_db)):
    db_registry = crud.get_registry_by_name(db, name=registry.name)
    if db_registry:
        raise HTTPException(status_code=400, detail="Registry with this name already exists")
    return crud.create_registry(db, registry=registry)

@router.put("/{registry_id}", response_model=registry_schema.Registry)
def update_registry(registry_id: str, registry: registry_schema.RegistryCreate, db: Session = Depends(get_db)):
    db_registry = crud.get_registry(db, registry_id)
    if not db_registry:
        raise HTTPException(status_code=404, detail="Registry not found")
    return crud.update_registry(db, db_registry=db_registry, registry_in=registry)

@router.delete("/{registry_id}")
def delete_registry(registry_id: str, db: Session = Depends(get_db)):
    db_registry = crud.get_registry(db, registry_id)
    if not db_registry:
        raise HTTPException(status_code=404, detail="Registry not found")
    crud.delete_registry(db, db_registry=db_registry)
    return {"message": "Registry deleted successfully"}
