from sqlalchemy import create_engine, text
import sys
import os

# Add the parent directory to sys.path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from app.core.config import DATABASE_URL

def add_column():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE projects ADD COLUMN backup_ignore_patterns VARCHAR"))
            print("Successfully added 'backup_ignore_patterns' column to 'projects' table.")
        except Exception as e:
            if "duplicate column name" in str(e):
                 print("Column 'backup_ignore_patterns' already exists.")
            else:
                print(f"Error adding column: {e}")

if __name__ == "__main__":
    add_column()
