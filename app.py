"""
TikAPI Test System - FastAPI Application with Official SDK
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import os
import time
import logging
from datetime import datetime

try:
    from tikapi import TikAPI as TikAPISDK
    TIKAPI_AVAILABLE = True
except ImportError:
    TIKAPI_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TikAPI Test System",
    description="TikAPI Test System with Official SDK",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TIKAPI_KEY = os.getenv("TIKAPI_KEY")

class TestRequest(BaseModel):
    username: str

class BulkTestRequest(BaseModel):
    usernames: List[str]

class TestResult(BaseModel):
    username: str
    success: bool
    is_live: Optional[bool] = None
    response_time: Optional[float] = None
    error: Optional[str] = None
    tested_at: datetime

class BulkTestStats(BaseModel):
    total_users: int
    success_count: int
    success_rate: str
    avg_response_time_ms: float
    results: List[Dict[str, Any]]
    tested_at: str

async def check_user_with_sdk(username: str) -> Dict[str, Any]:
    if not TIKAPI_AVAILABLE:
        return {
            "success": False,
            "is_live": None,
            "response_time": 0,
            "error": "TikAPI SDK not available"
        }
    
    if not TIKAPI_KEY:
        return {
            "success": False,
            "is_live": None,
            "response_time": 0,
            "error": "TIKAPI_KEY not configured"
        }
    
    start_time = time.time()
    
    try:
        api = TikAPISDK(TIKAPI_KEY)
        clean_username = username.lstrip('@')
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: api.public.check(username=clean_username)
        )
        
        response_time = (time.time() - start_time) * 1000
        
        if response and hasattr(response, 'json'):
            data = response.json
            
            is_live = False
            if data.get("roomId"):
                is_live = True
            
            return {
                "success": True,
                "is_live": is_live,
                "response_time": response_time,
                "error": None,
                "raw_data": data
            }
        else:
            return {
                "success": False,
                "is_live": None,
                "response_time": response_time,
                "error": "Invalid response from API",
                "raw_data": None
            }
            
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            "success": False,
            "is_live": None,
            "response_time": response_time,
            "error": str(e),
            "raw_data": None
        }

@app.get("/")
async def root():
    return {
        "message": "TikAPI Test System",
        "version": "1.1.0 - Official SDK",
        "tikapi_key_configured": TIKAPI_KEY is not None,
        "tikapi_sdk_available": TIKAPI_AVAILABLE,
        "endpoints": {
            "test_single": "/test/{username}",
            "test_bulk": "/test/bulk",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "tikapi_sdk": TIKAPI_AVAILABLE,
        "tikapi_key": TIKAPI_KEY is not None
    }

@app.get("/test/{username}")
async def test_single_user(username: str):
    result = await check_user_with_sdk(username)
    
    return {
        "username": username,
        "success": result["success"],
        "is_live": result["is_live"],
        "response_time_ms": result["response_time"],
        "error": result["error"],
        "tested_at": datetime.now().isoformat()
    }

@app.post("/test/bulk", response_model=BulkTestStats)
async def test_bulk_users(request: BulkTestRequest):
    results = []
    
    for username in request.usernames:
        result = await check_user_with_sdk(username)
        results.append({
            "username": username,
            "success": result["success"],
            "is_live": result["is_live"],
            "response_time_ms": result["response_time"],
            "error": result["error"]
        })
        await asyncio.sleep(0.5)
    
    success_count = sum(1 for r in results if r["success"])
    total_response_time = sum(r["response_time_ms"] for r in results if r["response_time_ms"])
    avg_response_time = total_response_time / len(results) if results else 0
    
    return BulkTestStats(
        total_users=len(request.usernames),
        success_count=success_count,
        success_rate=f"{(success_count / len(request.usernames)) * 100:.1f}%",
        avg_response_time_ms=round(avg_response_time, 2),
        results=results,
        tested_at=datetime.now().isoformat()
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
