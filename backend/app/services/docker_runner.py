import docker
import subprocess
import os
import re
import tempfile
from ..core.config import LOG_DIR, TASK_LOG_SENTINEL
from ..database.database import SessionLocal
from ..database import crud

def decrypt(token: str) -> str:
    return token # Encryption removed

import hashlib

def run_docker_task(task_id: str, project_data: dict, tag_input: str, cred_data: dict | None, proxy_data: dict | None):
    # temp_builder_name 不再代表临时的，而是代表针对特定仓库的专用 Builder
    target_builder_name = None
    temp_config_path = None
    log_file_path = LOG_DIR / f"{task_id}.log"
    
    def log(message: str):
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(message.strip() + "\n")

    tags = [t.strip() for t in re.split(r'[,，|]', tag_input) if t.strip()]
    if not tags: tags = ["latest"]

    p = project_data
    # 平台列表处理
    platforms = [plat.strip() for plat in p.get('platforms', 'linux/amd64').split(',') if plat.strip()]
    # 仅在需要多平台构建时强制使用 Buildx
    use_buildx = len(platforms) > 1

    final_status = "FAILED"
    try:
        log(f"✅ 任务进程已启动... (模式: {'Buildx' if use_buildx else '标准'})")
        log(f"目标平台: {', '.join(platforms)}")
        
        client = docker.from_env()
        
        # --- 核心改进：更健壮地解析 Registry Host ---
        from urllib.parse import urlparse
        reg_url_raw = p['registry_url']
        if not (reg_url_raw.startswith('http://') or reg_url_raw.startswith('https://')):
            reg_url_raw = 'https://' + reg_url_raw
        parsed_url = urlparse(reg_url_raw)
        reg_host = parsed_url.netloc
        
        # 针对 Docker Hub 的特殊处理
        is_dockerhub = reg_host in ["docker.io", "index.docker.io", "registry-1.docker.io", ""]
        if is_dockerhub:
            reg_host = "docker.io"
            repo_base = p['repo_image_name'] # Docker Hub 允许省略 registry 前缀
        else:
            repo_base = f"{reg_host}/{p['repo_image_name']}".replace("//", "/")
        
        # 1. 登录
        if cred_data:
            # 同样解析凭据中的 registry_url
            c_reg_raw = cred_data['registry_url']
            if not (c_reg_raw.startswith('http://') or c_reg_raw.startswith('https://')):
                c_reg_raw = 'https://' + c_reg_raw
            c_reg_host = urlparse(c_reg_raw).netloc
            if c_reg_host in ["docker.io", "index.docker.io", "registry-1.docker.io", ""]:
                c_reg_host = "" # Docker CLI 登录 Docker Hub 最好传空或不传地址
            
            log(f"--- 正在登录到 {c_reg_host if c_reg_host else 'Docker Hub'} ---")
            pwd = decrypt(cred_data['encrypted_password'])
            # 同时执行 SDK 登录和命令行登录
            client.login(username=cred_data['username'], password=pwd, registry=cred_data['registry_url'])
            
            login_cmd = ["docker", "login", "-u", cred_data['username'], "--password-stdin"]
            if c_reg_host: login_cmd.append(c_reg_host)
            
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
RUN if [ -d /etc/apt/apt.conf.d ]; then echo "Acquire::http::Proxy \\"$HTTP_PROXY\\";" > /etc/apt/apt.conf.d/99proxy; fi
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
            log("\n--- 开始 Buildx 多架构构建与推送 ---")
            
            # 智能配置 Builder (支持持久化复用)
            try:
                # 仅针对非 Docker Hub 且需要特殊配置的仓库
                if not is_dockerhub:
                    # 智能判断: 如果显式 http:// 开头，或者看起来像私有IP/带端口，则启用 http
                    is_private_ip = any(reg_host.startswith(prefix) for prefix in ["192.168.", "10.", "172."])
                    has_port = ":" in reg_host
                    is_http = reg_url_raw.startswith("http://") or is_private_ip or has_port
                    
                    # 生成唯一且稳定的 Builder 名称 (基于仓库地址)
                    host_hash = hashlib.md5(reg_host.encode()).hexdigest()[:6]
                    safe_host_name = re.sub(r'[^a-zA-Z0-9]', '-', reg_host)
                    target_builder_name = f"builder-priv-{safe_host_name}-{host_hash}"

                    # 检查该 Builder 是否已存在
                    check_cmd = ["docker", "buildx", "inspect", target_builder_name]
                    builder_exists = subprocess.run(check_cmd, capture_output=True).returncode == 0
                    
                    if builder_exists:
                        log(f"--- ♻️ 复用已有专用构建环境: {target_builder_name} ---")
                    else:
                        # 不存在则创建
                        fd, temp_config_path = tempfile.mkstemp(suffix=".toml")
                        config_content = f"""[registry."{reg_host}"]
  http = {str(is_http).lower()}
  insecure = true
"""
                        with os.fdopen(fd, 'w') as f:
                            f.write(config_content)
                        
                        log(f"--- 🛠️ 初始化专用构建环境 (信任: {reg_host}, HTTP: {is_http}) ---")
                        
                        create_cmd = [
                            "docker", "buildx", "create",
                            "--name", target_builder_name,
                            "--driver", "docker-container",
                            "--driver-opt", "network=host",
                            "--config", temp_config_path,
                            "--bootstrap"
                        ]
                        
                        try:
                            subprocess.run(create_cmd, check=True, capture_output=True, text=True)
                            log(f"--- ✅ 专用环境创建成功: {target_builder_name} ---")
                        except subprocess.CalledProcessError as e:
                            log(f"⚠️ 创建专用 Builder 失败 (Exit {e.returncode}):\\nSTDOUT: {e.stdout}\\nSTDERR: {e.stderr}")
                            raise Exception(f"无法创建支持 HTTP/Insecure 的构建环境: {e.stderr}")
                        
                else:
                    target_builder_name = None
                
            except Exception as e:
                log(f"⚠️ 环境配置严重错误: {e}")
                raise e

            builder_to_use = target_builder_name if target_builder_name else "web-pusher-builder"
            
            # 构造完整的镜像标签引用，用于缓存源
            primary_tag = tags[0]
            cache_from_image = f"{repo_base}:{primary_tag}"

            buildx_cmd = [
                "docker", "buildx", "build",
                "--builder", builder_to_use,
                "--platform", ",".join(platforms),
                "--file", os.path.join(p['build_context'], effective_dockerfile),
                p['build_context'],
                "--push"
            ]
            
            # --- 缓存策略优化 ---
            buildx_cmd.append("--cache-to=type=inline")
            
            if p.get('no_cache'):
                buildx_cmd.append("--no-cache")
                log("--- ⚡ 强制无缓存构建 (已禁用读取旧缓存) ---")
            else:
                buildx_cmd.append(f"--cache-from=type=registry,ref={cache_from_image}")
                log(f"--- ♻️ 尝试复用远程缓存: {cache_from_image} ---")

            # 添加所有 Tag
            for tag in tags:
                buildx_cmd.extend(["-t", f"{repo_base}:{tag}"])
            # 添加 Build Args
            for k, v in build_args.items():
                buildx_cmd.extend(["--build-arg", f"{k}={v}"])

            # 执行并实时抓取日志
            process = subprocess.Popen(buildx_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=os.environ)
            for line in process.stdout:
                log(line)
            process.wait()
            if process.returncode != 0:
                raise Exception(f"Buildx 构建失败，退出码: {process.returncode}")

        else:
            # 标准模式 (用于单平台构建，最稳定)
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
                # SDK 推送自带鉴权，对 Docker Hub 最友好
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
        
    except Exception as e:
        log(f"\n--- ❌ 发生严重错误 ---\n{e}")
    finally:
        # 清理临时 Dockerfile
        try:
            # 无论成功失败，只要产生了临时文件都尝试清理
            tmp_df = os.path.join(p['build_context'], p['dockerfile_path'] + ".tmp")
            if os.path.exists(tmp_df): 
                os.remove(tmp_df)
                # log("--- 🗑️ 已清理临时 Dockerfile ---")
        except: pass

        # 注意：不再清理 target_builder_name，实现持久化复用
        # 仅清理配置文件（因为它已经被 buildx 加载到内部容器了，本地文件可以删）
        if temp_config_path and os.path.exists(temp_config_path):
             try: os.remove(temp_config_path)
             except: pass

        log(TASK_LOG_SENTINEL)
        db = SessionLocal()
        try:
            crud.update_task_status(db, task_id=task_id, new_status=final_status)
        finally:
            db.close()