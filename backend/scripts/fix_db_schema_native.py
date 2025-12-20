import sqlite3
import os

# Define the path to the database
# Based on the file structure provided: /vol1/1000/NVME/dockerhub-web-box/data/projects.db
DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/projects.db')

def add_column():
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Error: Database file not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(projects)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'backup_ignore_patterns' in columns:
            print("Column 'backup_ignore_patterns' already exists.")
        else:
            print("Adding column 'backup_ignore_patterns'...")
            cursor.execute("ALTER TABLE projects ADD COLUMN backup_ignore_patterns TEXT DEFAULT ''")
            conn.commit()
            print("Successfully added column.")
            
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
