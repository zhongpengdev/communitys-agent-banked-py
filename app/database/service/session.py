from app.database.client import SessionLocal, SessionModel, DbResult


# 分页查询用户的会话历史
def get_sessions_paginated(user_id: str, page: int = 1, page_size: int = 10):
    db = SessionLocal()
    try:
        start = (page - 1) * page_size
        
        # Count total
        total_count = db.query(SessionModel).filter(SessionModel.user_id == str(user_id)).count()
        
        # Get paginated items
        sessions = (
            db.query(SessionModel)
            .filter(SessionModel.user_id == str(user_id))
            .order_by(SessionModel.created_at.desc())
            .offset(start)
            .limit(page_size)
            .all()
        )
        
        data = [{
            "id": s.id,
            "user_id": s.user_id,
            "title": s.title,
            "created_at": s.created_at.isoformat() if s.created_at else None
        } for s in sessions]
        
        return DbResult(data=data, count=total_count)
    finally:
        db.close()


def create_session(user_id: int, title: str):
    db = SessionLocal()
    try:
        new_session = SessionModel(user_id=str(user_id), title=title)
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return DbResult(data=[{
            "id": new_session.id,
            "user_id": new_session.user_id,
            "title": new_session.title,
            "created_at": new_session.created_at.isoformat() if new_session.created_at else None
        }])
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def update_session_title(session_id: int, title: str):
    """更新会话标题"""
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session:
            session.title = title
            db.commit()
            db.refresh(session)
            return DbResult(data=[{
                "id": session.id,
                "title": session.title
            }])
        return DbResult(data=[])
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def check_session_owner(session_id: int, user_id: str):
    """检查会话是否属于用户"""
    db = SessionLocal()
    try:
        session = (
            db.query(SessionModel)
            .filter(SessionModel.id == session_id, SessionModel.user_id == str(user_id))
            .first()
        )
        return session is not None
    finally:
        db.close()


# 删除会话
def delete_session_service(session_id: int):
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session:
            db.delete(session)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
