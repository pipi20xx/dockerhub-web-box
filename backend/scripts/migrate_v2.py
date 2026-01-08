import sqlite3
import os
import uuid
import shutil

DB_PATH = '/vol1/1000/NVME/dockerhub-web-box/data/projects.db'
BACKUP_PATH = DB_PATH + '.bak'

def migrate():
    if not os.path.exists(DB_PATH):
        print("数据库文件不存在，无需迁移。")
        return

    print(f"开始备份数据库到: {BACKUP_PATH}")
    shutil.copy2(DB_PATH, BACKUP_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. 创建新表 registries
        print("创建 registries 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registries (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL,
                credential_id TEXT,
                FOREIGN KEY (credential_id) REFERENCES credentials (id)
            )
        """)

        # 2. 迁移 Credentials (移除 registry_url)
        # 注意: SQLite ALTER TABLE 不支持删除列，所以我们需要重建表
        print("重构 credentials 表...")
        cursor.execute("CREATE TABLE credentials_new (id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, username TEXT NOT NULL, encrypted_password TEXT NOT NULL)")
        cursor.execute("INSERT INTO credentials_new (id, name, username, encrypted_password) SELECT id, name, username, encrypted_password FROM credentials")
        cursor.execute("DROP TABLE credentials")
        cursor.execute("ALTER TABLE credentials_new RENAME TO credentials")

        # 3. 迁移数据并创建 Registry 记录
        # 我们为每一个旧的 Project 创建一个 Registry，或者尝试去重
        print("从旧项目数据提取 Registry 信息...")
        cursor.execute("SELECT id, registry_url, credential_id FROM projects")
        old_projects = cursor.fetchall()

        registry_map = {} # (url, cred_id) -> registry_id
        
        for p_id, reg_url, cred_id in old_projects:
            key = (reg_url, cred_id)
            if key not in registry_map:
                new_reg_id = str(uuid.uuid4())
                reg_name = f"Registry-{reg_url}-{new_reg_id[:4]}"
                cursor.execute("INSERT INTO registries (id, name, url, credential_id) VALUES (?, ?, ?, ?)", 
                             (new_reg_id, reg_name, reg_url, cred_id))
                registry_map[key] = new_reg_id

        # 4. 重构 projects 表
        print("重构 projects 表...")
        # 记录旧的 registry_id 关联
        project_registry_links = []
        for p_id, reg_url, cred_id in old_projects:
            project_registry_links.append((registry_map[(reg_url, cred_id)], p_id))

        cursor.execute("""
            CREATE TABLE projects_new (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                build_context TEXT NOT NULL,
                dockerfile_path TEXT NOT NULL,
                local_image_name TEXT NOT NULL,
                repo_image_name TEXT NOT NULL,
                no_cache BOOLEAN NOT NULL,
                auto_cleanup BOOLEAN NOT NULL,
                platforms TEXT NOT NULL,
                registry_id TEXT,
                proxy_id TEXT,
                backup_ignore_patterns TEXT,
                FOREIGN KEY (registry_id) REFERENCES registries (id),
                FOREIGN KEY (proxy_id) REFERENCES proxies (id)
            )
        """)
        
        cursor.execute("""
            INSERT INTO projects_new (id, name, build_context, dockerfile_path, local_image_name, repo_image_name, no_cache, auto_cleanup, platforms, proxy_id, backup_ignore_patterns)
            SELECT id, name, build_context, dockerfile_path, local_image_name, repo_image_name, no_cache, auto_cleanup, platforms, proxy_id, backup_ignore_patterns FROM projects
        """)

        # 更新 registry_id
        for reg_id, p_id in project_registry_links:
            cursor.execute("UPDATE projects_new SET registry_id = ? WHERE id = ?", (reg_id, p_id))

        cursor.execute("DROP TABLE projects")
        cursor.execute("ALTER TABLE projects_new RENAME TO projects")

        conn.commit()
        print("✅ 数据库迁移成功！")

    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        # 如果失败，尝试还原备份
        # shutil.copy2(BACKUP_PATH, DB_PATH)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
