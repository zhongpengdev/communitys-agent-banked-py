"""
JWT 认证中间件 - 统一返回格式
"""

from fastapi import Header, HTTPException
from app.utils.JWTutils.jwt_helper import get_user_id
import jwt
from loguru import logger


def verify_token(authorization: str = Header(None)) -> str:
    """
    验证 JWT token 并返回用户 ID

    Args:
        authorization: Authorization header

    Returns:
        用户 ID

    Raises:
        HTTPException: 401 - token 无效或过期
    """
    if not authorization:
        logger.warning("未检测到 Authorization 头，认证失败")
        raise HTTPException(
            status_code=401,
            detail={"code": 401, "message": "缺少 Authorization header", "data": None},
        )

    # 去掉 "Bearer " 前缀
    token = authorization.replace("Bearer ", "").strip()

    logger.debug(f"提取到的 Token: {token}")

    try:
        # 解码并验证 token（会自动检查过期时间）
        user_id = get_user_id(token)

        logger.info(f"用户 {user_id} 验证成功")
        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"code": 401, "message": "Token 已过期，请重新登录", "data": None},
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail={"code": 401, "message": "无效的 Token", "data": None},
        )

    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail={"code": 401, "message": f"认证失败: {str(e)}", "data": None},
        )
