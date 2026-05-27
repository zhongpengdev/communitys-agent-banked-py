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

# 获取用户的10条历史对话用于热记忆
def get_recent_messages(session_id: int, limit: int = 10):
    """
    倒叙索引最后的10条
    """
    db = SessionLocal()
    try:
        messages = (
            db.query(MessageModel)
            .filter(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.desc())
            .limit(limit)
            .all()
        )
        
        # 得到正确的data序列
        messages.reverse()
        
        data = [{
            "id": msg.id,
            "session_id": msg.session_id,
            "role": msg.role,
            "content": msg.content,
            "create_at": msg.created_at.isoformat() if msg.created_at else None
        } for msg in messages]
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
