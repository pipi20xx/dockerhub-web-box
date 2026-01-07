import subprocess
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict
import asyncio

router = APIRouter()

def run_command(cmd: List[str]) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"命令执行失败: {e.stderr}")

@router.get("/status")
def get_system_status():
    """检测当前 Docker 环境对多架构的支持情况"""
    try:
        buildx_version = run_command(["docker", "buildx", "version"])
        builders_raw = run_command(["docker", "buildx", "ls", "--format", "json"])
        
        builders = []
        for line in builders_raw.splitlines():
            if line.strip():
                try:
                    builders.append(json.loads(line))
                except: pass

        has_multiarch_builder = any(b.get("Driver") != "docker" for b in builders)
        
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
        return {
            "buildx_available": False,
            "error": str(e),
            "is_ready": False
        }

@router.post("/initialize")
async def initialize_env():
    """流式返回初始化日志"""
    async def event_generator():
        commands = [
            ["docker", "run", "--privileged", "--rm", "tonistiigi/binfmt", "--install", "all"],
            ["docker", "buildx", "create", "--name", "web-pusher-builder", "--driver", "docker-container", "--use"],
            ["docker", "buildx", "inspect", "--bootstrap"]
        ]
        
        yield "--- 🚀 开始初始化多架构构建环境 ---\n"
        
        for cmd in commands:
            yield f"\n> 执行命令: {' '.join(cmd)}\n"
            try:
                # 使用 Popen 实时捕获输出
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                for line in process.stdout:
                    yield line
                    await asyncio.sleep(0.01) # 微小延迟确保流顺畅
                process.wait()
                
                if process.returncode != 0 and cmd[0] == "docker" and "create" in cmd:
                    # 如果是创建 builder 失败（可能已存在），尝试切换
                    yield "⚠️ Builder 可能已存在，尝试切换...\n"
                    subprocess.run(["docker", "buildx", "use", "web-pusher-builder"])
            except Exception as e:
                yield f"❌ 出错: {str(e)}\n"
        
        yield "\n--- ✅ 环境初始化流程执行完毕 ---\n"

    return StreamingResponse(event_generator(), media_type="text/plain")