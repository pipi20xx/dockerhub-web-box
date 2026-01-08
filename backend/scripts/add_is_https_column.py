import sqlite3
import os

DB_PATH = '/vol1/1000/NVME/dockerhub-web-box/data/projects.db'

def update_schema():
    if not os.path.exists(DB_PATH):
        print("数据库不存在。")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(registries)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'is_https' not in columns:
            print("正在添加 is_https 列...")
            cursor.execute("ALTER TABLE registries ADD COLUMN is_https BOOLEAN DEFAULT 1 NOT NULL")
            conn.commit()
            print("添加成功。")
        else:
            print("列 is_https 已存在。")
    except Exception as e:
        print(f"错误: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_schema()
