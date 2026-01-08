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
    platforms = p.get('platforms', 'linux/amd64').split(',')
    # 统一使用 Buildx，不再区分标准模式
    use_buildx = True 

    final_status = "FAILED"
    try:
        log(f"✅ 任务进程已启动... (统一使用 Buildx 模式)")
        log(f"目标平台: {', '.join(platforms)}")
        
        client = docker.from_env()
        # 彻底清洗仓库地址，去除协议头和多余斜杠，确保 buildx 解析正确
        raw_reg = p['registry_url'].replace("https://", "").replace("http://", "").rstrip('/')
        repo_base = f"{raw_reg}/{p['repo_image_name']}".replace("//", "/")
        
        # 1. 登录
        if cred_data:
            # 针对 Buildx 优化：如果是非安全仓库，去掉协议头
            reg_url = cred_data['registry_url']
            # 提取纯净地址
            reg_url = re.sub(r'^https?://', '', reg_url).rstrip('/')
            
            log(f"--- 正在登录到 {reg_url} ---")
            pwd = decrypt(cred_data['encrypted_password'])
            # 同时执行 SDK 登录和命令行登录 (buildx 需要命令行登录状态)
            client.login(username=cred_data['username'], password=pwd, registry=cred_data['registry_url'])
            login_cmd = ["docker", "login", reg_url, "-u", cred_data['username'], "--password-stdin"]
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

        # 3. 执行构建 (统一 Buildx 流程)
        log("\n--- 开始 Buildx 多架构构建与推送 ---")
        
        # 智能配置 Builder (支持持久化复用)
        try:
            # 尝试解析并信任目标仓库
            raw_url = p['registry_url']
            reg_host = raw_url.replace("https://", "").replace("http://", "").split('/')[0]
            
            # 仅针对非 Docker Hub 且需要特殊配置的仓库
            if reg_host not in ["docker.io", "index.docker.io", "registry-1.docker.io"]:
                # 智能判断: 如果显式 http:// 开头，或者看起来像私有IP/带端口，则启用 http
                is_private_ip = any(reg_host.startswith(prefix) for prefix in ["192.168.", "10.", "172."])
                has_port = ":" in reg_host
                is_http = raw_url.startswith("http://") or is_private_ip or has_port
                
                # 生成唯一且稳定的 Builder 名称 (基于仓库地址)
                # 例如: builder-private-192-168-50-12-6100-a1b2c3
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
                    # 创建临时配置文件 (修复 TOML 格式)
                    fd, temp_config_path = tempfile.mkstemp(suffix=".toml")
                    # 使用三引号确保换行符正确，避免转义问题
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
            # 如果是上面抛出的异常，直接中断任务
            log(f"⚠️ 环境配置严重错误: {e}")
            raise e

        builder_to_use = target_builder_name if target_builder_name else "web-pusher-builder"
        
        # 构造完整的镜像标签引用，用于缓存源
        # 使用列表中的第一个 tag 作为主要的缓存来源
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
        # 默认启用 Inline Cache (将缓存元数据写入镜像)
        buildx_cmd.append("--cache-to=type=inline")
        
        if p.get('no_cache'):
            # 用户强制要求无缓存构建：添加 --no-cache，且不读取旧缓存
            buildx_cmd.append("--no-cache")
            log("--- ⚡ 强制无缓存构建 (已禁用读取旧缓存) ---")
        else:
            # 普通构建：尝试利用远程 Registry 中的缓存
            # 注意：如果这是第一次推送，或者是私有非安全仓库，这里可能会有 warning，但不影响构建
            buildx_cmd.append(f"--cache-from=type=registry,ref={cache_from_image}")
            log(f"--- ♻️ 尝试复用远程缓存: {cache_from_image} ---")
        # --------------------

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