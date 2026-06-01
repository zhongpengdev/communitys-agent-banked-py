import json
from app.utils.context import get_request_token
from app.utils.http_client import HttpClientManager
from app.core.config import settings

BANKED_URL = settings.banked_url
SERP_KEY = settings.serp_key
DOMAINSDB_KEY = settings.domainsdb_key
API_KEY = settings.api_key
QWEN_CREATE_URL = settings.qwen_create_text_url
QWEN_GET_URL = settings.qwen_get_result_url

def _auth_headers() -> dict:
    token = get_request_token()
    headers = {"Connection": "keep-alive"}
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    return headers

async def http_get(endpoint: str, params: dict = None) -> dict:
    url = f"{BANKED_URL}{endpoint}"
    
    session = HttpClientManager.get_session()
    headers = _auth_headers()
    
    async with session.get(url, params=params, headers=headers) as r:
            r.raise_for_status()
            return await r.json()


async def http_post(endpoint: str, json_data: dict = None) -> dict:
    url = f"{BANKED_URL}{endpoint}"
    
    session = HttpClientManager.get_session()
    headers = _auth_headers()
    
    async with session.post(url, json=json_data, headers=headers) as r:
            r.raise_for_status()
            return await r.json()


async def http_delete(endpoint: str) -> dict:
    url = f"{BANKED_URL}{endpoint}"
    
    session = HttpClientManager.get_session()
    headers = _auth_headers()
    
    async with session.delete(url, headers=headers) as r:
            r.raise_for_status()
            return await r.json()


def ok_response(data) -> dict:
    text = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    return {"content": [{"type": "text", "text": text}]}


def error_response(msg: str) -> dict:
    return {"content": [{"type": "text", "text": json.dumps({"success": False, "message": msg}, ensure_ascii=False)}]}
