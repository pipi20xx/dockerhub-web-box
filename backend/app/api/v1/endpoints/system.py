import subprocess
import json
import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict
import asyncio
import re

from ....database.database import get_db
from ....database import crud

router = APIRouter()

def run_command(cmd: List[str]) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"命令执行失败: {e.stderr}")

def clean_registry_url(url: str) -> str:
    if not url: return ""
    s = re.sub(r'^https?://', '', url)
    s = s.split('/')[0]
    return s.strip()

@router.get("/status")
def get_system_status():
    try:
        buildx_version = run_command(["docker", "buildx", "version"])
        builders_raw = run_command(["docker", "buildx", "ls", "--format", "json"])
        builders = []
        for line in builders_raw.splitlines():
            if line.strip():
                try: builders.append(json.loads(line))
                except: pass
        has_multiarch_builder = any(b.get("Name") == "web-pusher-builder" for b in builders)
        platforms = []
        for b in builders:
            for node in b.get("Nodes", []):
                platforms.extend(node.get("Platforms", []))
        platforms = sorted(list(set(platforms)))
        return {
            "buildx_available": True,
            "buildx_version": buildx_version,
            "has_multiarch_builder": has_multiarch_builder,
            "supported_platforms": platforms,
            "is_ready": has_multiarch_builder and "linux/arm64" in platforms
        }
    except Exception as e:
        return {"buildx_available": False, "error": str(e), "is_ready": False}

@router.post("/initialize")
async def initialize_env(db: Session = Depends(get_db)):
    async def event_generator():
        yield "--- 🚀 开始初始化多架构构建环境 (终极协议修复方案) ---\n"
        
        # 从新的 Registry 模型中获取所有仓库
        all_registries = crud.get_registries(db)
        insecure_registries = set()
        
        for reg in all_registries:
            clean_host = clean_registry_url(reg.url)
            # 如果仓库被标记为非 HTTPS，或者不是 Docker Hub，我们将其加入信任列表
            if not reg.is_https or clean_host not in ["docker.io", "index.docker.io", "registry-1.docker.io"]:
                if clean_host:
                    insecure_registries.add(clean_host)
            
        yield f"需要特殊配置的仓库: {list(insecure_registries)}\n"

        config_path = "/tmp/buildkitd.toml"
        # 使用最显式的 TOML 格式
        config_content = "[worker.oci]\n  max-parallelism = 4\n\n"
        for host in insecure_registries:
            config_content += f'[registry."{host}"]\n'
            config_content += '  http = true\n'
            config_content += '  insecure = true\n\n'

        with open(config_path, "w") as f:
            f.write(config_content)
        
        yield "--- 注入 BuildKit 配置 ---\n"
        yield config_content
        yield "--------------------------\n"

        yield "\n> [1/3] 检查模拟器状态...\n"
        subprocess.run(["docker", "run", "--privileged", "--rm", "tonistiigi/binfmt", "--install", "all"])
        yield "模拟器已就绪。\n"

        yield "\n> [2/3] 彻底重建 Builder 并绑定配置...\n"
        subprocess.run(["docker", "buildx", "rm", "-f", "web-pusher-builder"], capture_output=True)
        
        # 增加 --driver-opt network=host 提升兼容性
        create_cmd = [
            "docker", "buildx", "create", 
            "--name", "web-pusher-builder", 
            "--driver", "docker-container", 
            "--driver-opt", "network=host",
            "--config", config_path,
            "--use"
        ]
        subprocess.run(create_cmd, capture_output=True)
        yield "Builder 重建完成。\n"

        yield "\n> [3/3] 强制启动引擎 (Bootstrap)...\n"
        process = subprocess.Popen(["docker", "buildx", "inspect", "--bootstrap"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout: 
            yield line
            await asyncio.sleep(0.01)
        process.wait()
        
        yield "\n--- ✅ 初始化完毕。请再次尝试 ARM64 推送 ---\n"

    return StreamingResponse(event_generator(), media_type="text/plain")
