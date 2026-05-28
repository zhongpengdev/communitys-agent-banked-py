import os
import json
from dotenv import load_dotenv
from app.utils.context import get_request_token
from app.utils.http_client import HttpClientManager

load_dotenv()

BANKED_URL = os.getenv("Banked_URL", "")
SERP_KEY = os.getenv("SERP_KEY", "")
DOMAINSDB_KEY = os.getenv("DOMAINSDB_KEY", "")
API_KEY = os.getenv("API_KEY", "")
QWEN_CREATE_URL = os.getenv("QWEN_CREATE_TEXT_URL", "")
QWEN_GET_URL = os.getenv("QWEN_GET_RESULT_URL", "")

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
