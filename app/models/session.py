from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import func
from app.core.database import Base

class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    title = Column(String, default="新对话")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
