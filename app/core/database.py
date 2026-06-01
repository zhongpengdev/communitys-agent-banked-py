from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(settings.database_url,
                       client_encoding="utf8")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    """Create database tables if they don't exist."""
    try:
        # Import models here to register them with Base before calling create_all
        from app.models.session import SessionModel
        from app.models.message import MessageModel
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Database initialization failed: {e}. This is expected if DATABASE_URL is not set or PG is down.")

# Run initialization on import
init_db()
