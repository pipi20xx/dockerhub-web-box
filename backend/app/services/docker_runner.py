import docker
import subprocess
import os
import re
from ..core.config import LOG_DIR, TASK_LOG_SENTINEL
from ..database.database import SessionLocal
from ..database import crud

def decrypt(token: str) -> str:
    return token # Encryption removed

def run_docker_task(task_id: str, project_data: dict, tag_input: str, cred_data: dict | None, proxy_data: dict | None):
    log_file_path = LOG_DIR / f"{task_id}.log"
    
    def log(message: str):
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(message.strip() + "\n")

    tags = [t.strip() for t in re.split(r'[,，|]', tag_input) if t.strip()]
    if not tags: tags = ["latest"]

    p = project_data
    # 平台列表处理
    platforms = p.get('platforms', 'linux/amd64').split(',')
    # 如果选择了多个平台，或者强制指定了非本地平台，则必须使用 buildx
    use_buildx = len(platforms) > 1 or "linux/arm64" in platforms 

    final_status = "FAILED"
    try:
        log(f"✅ 任务进程已启动... (使用 {'Buildx' if use_buildx else '标准'} 模式)")
        log(f"目标平台: {', '.join(platforms)}")
        
        client = docker.from_env()
        repo_base = f"{p['registry_url']}/{p['repo_image_name']}"
        
        # 1. 登录
        if cred_data:
            log(f"--- 正在登录到 {cred_data['registry_url']} ---")
            pwd = decrypt(cred_data['encrypted_password'])
            # 同时执行 SDK 登录和命令行登录 (buildx 需要命令行登录状态)
            client.login(username=cred_data['username'], password=pwd, registry=cred_data['registry_url'])
            login_cmd = ["docker", "login", cred_data['registry_url'], "-u", cred_data['username'], "--password-stdin"]
            subprocess.run(login_cmd, input=pwd, text=True, capture_output=True, check=True)
            log("--- 登录成功 ---")

        # 2. 准备 Dockerfile 和 代理
        effective_dockerfile = p['dockerfile_path']
        build_args = {}
        if proxy_data:
            url = proxy_data['url']
            log(f"--- 🚀 注入代理: {url} ---")
            for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
                build_args[key] = url
            
            # 动态注入代理到 Dockerfile
            try:
                df_full_path = os.path.join(p['build_context'], p['dockerfile_path'])
                with open(df_full_path, 'r', encoding='utf-8') as f: content = f.read()
                
                # 使用三引号避免引号转义地狱
                proxy_setup = """
# --- Proxy Injection ---
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG http_proxy
ARG https_proxy
ENV HTTP_PROXY=$HTTP_PROXY
ENV HTTPS_PROXY=$HTTPS_PROXY
ENV http_proxy=$http_proxy
ENV https_proxy=$https_proxy
RUN if [ -d /etc/apt/apt.conf.d ]; then echo \"Acquire::http::Proxy \\"$HTTP_PROXY\\"\";" > /etc/apt/apt.conf.d/99proxy; fi
"""
                new_content = ""
                for line in content.splitlines():
                    new_content += line + "\n"
                    if line.strip().upper().startswith("FROM "): new_content += proxy_setup
                
                effective_dockerfile = p['dockerfile_path'] + ".tmp"
                with open(os.path.join(p['build_context'], effective_dockerfile), 'w', encoding='utf-8') as f:
                    f.write(new_content)
            except Exception as e:
                log(f"⚠️ 代理注入失败: {e}")

        # 3. 执行构建
        if use_buildx:
            # Buildx 模式：支持多架构同时构建并推送
            log("\n--- 开始 Buildx 多架构构建与推送 ---")
            buildx_cmd = [
                "docker", "buildx", "build",
                "--platform", ",".join(platforms),
                "--file", os.path.join(p['build_context'], effective_dockerfile),
                p['build_context'],
                "--push"
            ]
            # 添加所有 Tag
            for tag in tags:
                buildx_cmd.extend(["-t", f"{repo_base}:{tag}"])
            # 添加 Build Args
            for k, v in build_args.items():
                buildx_cmd.extend(["--build-arg", f"{k}={v}"])
            if p.get('no_cache'):
                buildx_cmd.append("--no-cache")

            # 执行并实时抓取日志
            process = subprocess.Popen(buildx_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=os.environ)
            for line in process.stdout:
                log(line)
            process.wait()
            if process.returncode != 0:
                raise Exception(f"Buildx 构建失败，退出码: {process.returncode}")
        else:
            # 标准模式
            primary_full_image = f"{repo_base}:{tags[0]}"
            log(f"\n--- 开始标准构建: {primary_full_image} ---")
            streamer = client.api.build(
                path=p['build_context'], dockerfile=effective_dockerfile, 
                tag=primary_full_image, nocache=p.get('no_cache', False), 
                rm=True, decode=True, buildargs=build_args
            )
            for chunk in streamer:
                if 'stream' in chunk: log(chunk['stream'])
            
            image = client.images.get(primary_full_image)
            # 打其余标签并推送
            for i, tag in enumerate(tags):
                full_name = f"{repo_base}:{tag}"
                if i > 0: image.tag(repository=repo_base, tag=tag)
                log(f"--- 正在推送: {full_name} ---")
                for chunk in client.images.push(repository=repo_base, tag=tag, stream=True, decode=True):
                    if 'error' in chunk: raise Exception(chunk['error'])
                    if 'status' in chunk: log(f"{chunk['status']} {chunk.get('progress', '')}")

        final_status = "SUCCESS"
        log("\n--- ✅ 任务成功完成! ---")

        # 4. 清理
        if p.get('auto_cleanup', True) and not use_buildx:
            log("\n--- 🧹 正在清理本地镜像... ---")
            for tag in tags:
                try: client.images.remove(f"{repo_base}:{tag}")
                except: pass
        
        # 清理临时 Dockerfile
        try:
            tmp_df = os.path.join(p['build_context'], p['dockerfile_path'] + ".tmp")
            if os.path.exists(tmp_df): os.remove(tmp_df)
        except: pass

    except Exception as e:
        log(f"\n--- ❌ 发生严重错误 ---\n{e}")
    finally:
        log(TASK_LOG_SENTINEL)
        db = SessionLocal()
        try:
            crud.update_task_status(db, task_id=task_id, new_status=final_status)
        finally:
            db.close()