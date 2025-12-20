from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_and_migrate_db():
    inspector = inspect(engine)
    
    # 1. Check projects table for backup_ignore_patterns
    if inspector.has_table("projects"):
        columns = [col['name'] for col in inspector.get_columns("projects")]
        if "backup_ignore_patterns" not in columns:
            print("Migrating database: Adding 'backup_ignore_patterns' column to 'projects' table.")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE projects ADD COLUMN backup_ignore_patterns VARCHAR DEFAULT ''"))
                conn.commit()