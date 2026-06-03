import jwt
from fastapi import Header, HTTPException
from loguru import logger
from app.core.config import settings

JWT_SECRET = settings.jwt_secret
JWT_ALGORITHM = settings.jwt_algorithm

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

def get_user_id(token: str) -> str:
    payload = decode_token(token)
    
    return str(payload.get("userId") or payload.get("sub") or payload.get("id"))

def verify_token(authorization: str = Header(None)) -> str:
    if not authorization:
        logger.warning("未检测到 Authorization 头，认证失败")
        raise HTTPException(
            status_code=401,
            detail={"code": 401, "message": "缺少 Authorization header", "data": None}
        )
        
    token = authorization.replace("Bearer", "").strip()
    
    try:
        user_id = get_user_id(token)
        return user_id
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"code": 401, "message": "Token 已过期，请重新登录", "data": None}
        )
        
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail={"code": 401, "message": "无效的 Token", "data": None}
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail={"code": 401, "message": f"认证失败: {str(e)}", "data": None}
        )
