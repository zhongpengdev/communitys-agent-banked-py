"""
JWT 解析工具 - 最精简版本
"""

import jwt
from app.core.config import settings

JWT_SECRET = settings.jwt_secret
JWT_ALGORITHM = "HS512"  # Java 后端使用 HS512


def decode_token(token: str) -> dict:
    """
    解码 JWT token

    Args:
        token: JWT token 字符串

    Returns:
        解码后的 payload

    Raises:
        jwt.ExpiredSignatureError: token 已过期
        jwt.InvalidTokenError: token 无效
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_user_id(token: str) -> str:
    """
    从 token 中提取用户 ID

    Args:
        token: JWT token 字符串

    Returns:
        用户 ID
    """
    payload = decode_token(token)

    print(f"-----userId------{payload.get('userId')}")
    return str(payload.get("userId") or payload.get("sub") or payload.get("id"))
