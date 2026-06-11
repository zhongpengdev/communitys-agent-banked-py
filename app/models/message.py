from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from app.core.database import Base
from sqlalchemy.sql import func

class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    # messages已经开启了联级删除
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
