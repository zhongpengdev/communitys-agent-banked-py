from app.core.database import SessionLocal
from app.models.session import SessionModel


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
        
        items = [{
            "id": s.id,
            "user_id": s.user_id,
            "title": s.title,
            "created_at": s.created_at.isoformat() if s.created_at else None
        } for s in sessions]
        
        return {
            "items": items,
            "total": total_count
        }
    finally:
        db.close()


def create_session(user_id: int, title: str):
    db = SessionLocal()
    try:
        new_session = SessionModel(user_id=str(user_id), title=title)
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return {
            "id": new_session.id,
            "user_id": new_session.user_id,
            "title": new_session.title,
            "created_at": new_session.created_at.isoformat() if new_session.created_at else None
        }
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
            return {
                "id": session.id,
                "title": session.title
            }
        return {}
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
        

# 重命名会话
def rename_session_service(session_id: int, new_title: str):
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session:
            session.title = new_title
            db.commit()
            db.refresh(session)
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_session_by_id(session_id: int):
    """
    根据会话 ID 精准查询会话元数据（详情回源时使用）
    """
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session:
            return {
                "id": session.id,
                "user_id": session.user_id,
                "title": session.title,
                "created_at": session.created_at.isoformat() if session.created_at else None
            }
        return None
    finally:
        db.close()


def get_user_session_ids_and_created_at(user_id: str):
    """
    仅拉取用户的会话 ID 和创建时间（构建 ZSET 缓存时使用，覆盖索引扫描）
    """
    db = SessionLocal()
    try:
        sessions = (
            db.query(SessionModel.id, SessionModel.created_at)
            .filter(SessionModel.user_id == str(user_id))
            .all()
        )
        return [{"id": s.id, "created_at": s.created_at} for s in sessions]
    finally:
        db.close()

