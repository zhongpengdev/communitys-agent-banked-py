from app.database.client import SessionLocal, MessageModel, DbResult


# 插入一条新消息
def save_message(session_id: int, role: str, content: str):
    """插入一条消息"""
    db = SessionLocal()
    try:
        new_message = MessageModel(session_id=session_id, role=role, content=content)
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        return DbResult(data=[{
            "id": new_message.id,
            "session_id": new_message.session_id,
            "role": new_message.role,
            "content": new_message.content,
            "created_at": new_message.created_at.isoformat() if new_message.created_at else None
        }])
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# 获取历史聊天记录
def get_messages(session_id: int):
    db = SessionLocal()
    try:
        messages = (
            db.query(MessageModel)
            .filter(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.asc())
            .all()
        )
        data = [{
            "id": m.id,
            "session_id": m.session_id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None
        } for m in messages]
        return DbResult(data=data)
    finally:
        db.close()


# 删除session_id的所有消息
def delete_messages(session_id: int):
    db = SessionLocal()
    try:
        messages_to_delete = db.query(MessageModel).filter(MessageModel.session_id == session_id).all()
        data = [{"id": m.id} for m in messages_to_delete]
        
        db.query(MessageModel).filter(MessageModel.session_id == session_id).delete()
        db.commit()
        
        return DbResult(data=data)
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
