import docker
from ..core.config import LOG_DIR, TASK_LOG_SENTINEL
# ✨ --- 新增：导入数据库会话和CRUD操作 --- ✨
from ..database.database import SessionLocal
from ..database import crud

def decrypt(token: str) -> str:
    return token # Encryption removed

def run_docker_task(task_id: str, project_data: dict, tag: str, cred_data: dict | None, proxy_data: dict | None):
    log_file_path = LOG_DIR / f"{task_id}.log"
    
    def log(message: str):
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(message.strip() + "\n")

    # ✨ --- 核心修改：使用 try/except/finally 结构来确保数据库状态总能被更新 --- ✨
    final_status = "FAILED" # 默认任务状态为失败
    try:
        log("✅ 任务进程已启动...")
        client = docker.from_env()
        client.ping()

        p = project_data
        full_repo_image = f"{p['registry_url']}/{p['repo_image_name']}:{tag}"
        has_credentials = bool(cred_data)
        total_steps = 4 if has_credentials else 3
        step = 1

        # 1. 登录
        if has_credentials:
            log(f"--- [{step}/{total_steps}] 正在使用凭证 '{cred_data['name']}' 登录到 {cred_data['registry_url']} ---")
            try:
                decrypted_password = decrypt(cred_data['encrypted_password'])
                login_result = client.login(username=cred_data['username'], password=decrypted_password, registry=cred_data['registry_url'])
                log(f"--- 登录成功: {login_result.get('Status')} ---")
            except Exception as e:
                log(f"--- ❌ 登录失败! ---\n{e}")
                raise
            step += 1

        # 2. 构建
        build_args = {}
        effective_dockerfile = p['dockerfile_path']
        
        if proxy_data:
            url = proxy_data['url']
            log(f"--- 🚀 正在注入通用代理配置: {url} ---")
            # 同时提供大写和小写，确保全工具兼容
            for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
                build_args[key] = url
            build_args['NO_PROXY'] = 'localhost,127.0.0.1'
            build_args['no_proxy'] = 'localhost,127.0.0.1'

            # --- 黑科技：动态注入代理声明到 Dockerfile ---
            try:
                import os
                original_df_path = os.path.join(p['build_context'], p['dockerfile_path'])
                with open(original_df_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 在每一个 FROM 指令后面插入代理声明
                # 这样可以处理多阶段构建（Multi-stage builds）
                proxy_setup = (
                    "\n# --- Proxy Injection by System ---\n"
                    "ARG HTTP_PROXY\nARG HTTPS_PROXY\nARG http_proxy\nARG https_proxy\n"
                    "ENV HTTP_PROXY=$HTTP_PROXY\nENV HTTPS_PROXY=$HTTPS_PROXY\n"
                    "ENV http_proxy=$http_proxy\nENV https_proxy=$https_proxy\n"
                    "RUN if [ -f /etc/apt/apt.conf.d/99proxy ]; then :; elif [ -d /etc/apt/apt.conf.d ]; then "
                    "echo \"Acquire::http::Proxy \\\"$HTTP_PROXY\\\";\" > /etc/apt/apt.conf.d/99proxy; fi\n"
                    "# --- End Proxy Injection ---\n"
                )
                
                new_content = ""
                for line in content.splitlines():
                    new_content += line + "\n"
                    if line.strip().upper().startswith("FROM "):
                        new_content += proxy_setup
                
                effective_dockerfile = p['dockerfile_path'] + ".proxy_tmp"
                temp_df_path = os.path.join(p['build_context'], effective_dockerfile)
                with open(temp_df_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                log(f"--- 已生成临时代理 Dockerfile: {effective_dockerfile} ---")
            except Exception as e:
                log(f"--- ⚠️ 代理注入失败 (将尝试常规构建): {e} ---")

        log(f"\n--- [{step}/{total_steps}] 开始构建镜像: {p['local_image_name']}:{tag} ---")
        try:
            streamer = client.api.build(
                path=p['build_context'], 
                dockerfile=effective_dockerfile, 
                tag=f"{p['local_image_name']}:{tag}", 
                nocache=p['no_cache'], 
                rm=True, 
                decode=True, 
                buildargs=build_args
            )
            for chunk in streamer:
                if 'stream' in chunk: log(chunk['stream'])
        finally:
            # 清理临时文件
            if proxy_data and 'temp_df_path' in locals() and os.path.exists(temp_df_path):
                os.remove(temp_df_path)
        
        image = client.images.get(f"{p['local_image_name']}:{tag}")
        log(f"\n--- 构建成功, 镜像 ID: {image.short_id} ---")
        step += 1

        # 3. 打标签
        log(f"\n--- [{step}/{total_steps}] 开始打标签: {full_repo_image} ---")
        image.tag(repository=f"{p['registry_url']}/{p['repo_image_name']}", tag=tag)
        log("--- 打标签成功 ---")
        step += 1

        # 4. 推送
        log(f"\n--- [{step}/{total_steps}] 开始推送镜像到: {full_repo_image} ---")
        push_stream = client.images.push(repository=f"{p['registry_url']}/{p['repo_image_name']}", tag=tag, stream=True, decode=True)
        for chunk in push_stream:
            status, progress, error = chunk.get('status', ''), chunk.get('progress', ''), chunk.get('error')
            if error:
                log(f"推送错误: {error}")
                # ✨ --- 关键修改：如果检测到错误，立即抛出异常，中断流程 --- ✨
                raise Exception(f"推送镜像失败: {error}")
            elif status:
                log(f"{status} {progress}")

        log("\n--- ✅ 全部任务成功完成! ---")
        # ✨ --- 关键修改：只有在所有步骤都成功后，才将最终状态设为 SUCCESS --- ✨
        final_status = "SUCCESS"

    except Exception as e:
        log(f"\n--- ❌ 任务执行过程中发生严重错误! ---\n{e}")
        # 此时 final_status 保持为 "FAILED"
    finally:
        # 无论成功或失败，都写入日志结束标记
        log(TASK_LOG_SENTINEL)
        
        # ✨ --- 核心修改：创建独立的数据库会话来更新任务状态 --- ✨
        db = None
        try:
            db = SessionLocal()
            crud.update_task_status(db, task_id=task_id, new_status=final_status)
            log(f"--- 数据库状态已更新为: {final_status} ---")
        except Exception as db_e:
            log(f"--- ❌ 更新数据库状态时发生错误! ---\n{db_e}")
        finally:
            if db:
                db.close()