"""
TikAPI Test System - FastAPI Application
TikAPIのテスト・比較システム
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import asyncio
import os
import time
import logging
from datetime import datetime

# TikTokLive import (比較用)
try:
    from TikTokLive import TikTokLiveClient
    from TikTokLive.client.errors import LiveNotFound, UserOffline
    TIKTOK_LIVE_AVAILABLE = True
except ImportError:
    TIKTOK_LIVE_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TikAPI Test System",
    description="TikAPI精度・速度テストシステム",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 環境変数
TIKAPI_KEY = os.getenv("TIKAPI_KEY")
TIKAPI_BASE_URL = "https://api.tikapi.io/public/v1"

# Data Models
class TestRequest(BaseModel):
    username: str

class BulkTestRequest(BaseModel):
    usernames: List[str]

class TestResult(BaseModel):
    username: str
    tikapi_success: bool
    tikapi_is_live: Optional[bool] = None
    tikapi_response_time: Optional[float] = None
    tikapi_error: Optional[str] = None
    tiktok_live_success: bool = False
    tiktok_live_is_live: Optional[bool] = None
    tiktok_live_response_time: Optional[float] = None
    tiktok_live_error: Optional[str] = None
    match: Optional[bool] = None
    tested_at: datetime

class ComparisonStats(BaseModel):
    total_tests: int
    tikapi_success_rate: float
    tiktok_live_success_rate: float
    match_rate: float
    tikapi_avg_response_time: float
    tiktok_live_avg_response_time: float
    results: List[TestResult]

# TikAPI Client
class TikAPIClient:
    """TikAPI専用クライアント"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = TIKAPI_BASE_URL
        self.headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
    
    async def check_live_status(self, username: str) -> Dict[str, Any]:
        """ユーザーのライブ配信状態をチェック"""
        url = f"{self.base_url}/user/info"
        params = {"username": username}
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=15.0
                )
                
                response_time = (time.time() - start_time) * 1000  # ms
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # TikAPIのレスポンス構造に基づいて解析
                    user_info = data.get("userInfo", {}).get("user", {})
                    is_live = user_info.get("roomId") is not None and user_info.get("roomId") != ""
                    
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
                        "error": f"HTTP {response.status_code}: {response.text}",
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

# TikTokLive Client (比較用)
async def check_with_tiktok_live(username: str) -> Dict[str, Any]:
    """TikTokLiveライブラリでチェック"""
    if not TIKTOK_LIVE_AVAILABLE:
        return {
            "success": False,
            "is_live": None,
            "response_time": 0,
            "error": "TikTokLive not available"
        }
    
    start_time = time.time()
    
    try:
        clean_username = username.lstrip('@')
        client = TikTokLiveClient(unique_id=clean_username)
        
        is_live = await asyncio.wait_for(client.is_live(), timeout=15)
        response_time = (time.time() - start_time) * 1000
        
        return {
            "success": True,
            "is_live": is_live,
            "response_time": response_time,
            "error": None
        }
        
    except asyncio.TimeoutError:
        response_time = (time.time() - start_time) * 1000
        return {
            "success": False,
            "is_live": None,
            "response_time": response_time,
            "error": "Timeout"
        }
    except (UserOffline, LiveNotFound):
        response_time = (time.time() - start_time) * 1000
        return {
            "success": True,
            "is_live": False,
            "response_time": response_time,
            "error": None
        }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            "success": False,
            "is_live": None,
            "response_time": response_time,
            "error": str(e)
        }

# Routes
@app.get("/")
async def root():
    """システム情報"""
    return {
        "message": "TikAPI Test System",
        "version": "1.0.0",
        "tikapi_configured": TIKAPI_KEY is not None,
        "tiktok_live_available": TIKTOK_LIVE_AVAILABLE,
        "endpoints": {
            "test_single": "/test/{username}",
            "test_bulk": "/test/bulk",
            "compare_single": "/compare/{username}",
            "compare_bulk": "/compare/bulk"
        }
    }

@app.get("/test/{username}")
async def test_single_user(username: str):
    """単一ユーザーをTikAPIでテスト"""
    if not TIKAPI_KEY:
        raise HTTPException(status_code=500, detail="TIKAPI_KEY not configured")
    
    client = TikAPIClient(TIKAPI_KEY)
    result = await client.check_live_status(username)
    
    return {
        "username": username,
        "success": result["success"],
        "is_live": result["is_live"],
        "response_time_ms": result["response_time"],
        "error": result["error"],
        "tested_at": datetime.now().isoformat()
    }

@app.post("/test/bulk")
async def test_bulk_users(request: BulkTestRequest):
    """複数ユーザーをTikAPIでテスト"""
    if not TIKAPI_KEY:
        raise HTTPException(status_code=500, detail="TIKAPI_KEY not configured")
    
    client = TikAPIClient(TIKAPI_KEY)
    results = []
    
    for username in request.usernames:
        result = await client.check_live_status(username)
        results.append({
            "username": username,
            "success": result["success"],
            "is_live": result["is_live"],
            "response_time_ms": result["response_time"],
            "error": result["error"]
        })
        
        # レート制限回避のため少し待機
        await asyncio.sleep(0.5)
    
    # 統計計算
    success_count = sum(1 for r in results if r["success"])
    total_response_time = sum(r["response_time_ms"] for r in results if r["response_time_ms"])
    avg_response_time = total_response_time / len(results) if results else 0
    
    return {
        "total_users": len(request.usernames),
        "success_count": success_count,
        "success_rate": f"{(success_count / len(request.usernames)) * 100:.1f}%",
        "avg_response_time_ms": round(avg_response_time, 2),
        "results": results,
        "tested_at": datetime.now().isoformat()
    }

@app.get("/compare/{username}")
async def compare_single_user(username: str):
    """TikAPI vs TikTokLiveの比較（単一）"""
    if not TIKAPI_KEY:
        raise HTTPException(status_code=500, detail="TIKAPI_KEY not configured")
    
    # 両方同時実行
    tikapi_client = TikAPIClient(TIKAPI_KEY)
    tikapi_task = tikapi_client.check_live_status(username)
    tiktok_live_task = check_with_tiktok_live(username)
    
    tikapi_result, tiktok_live_result = await asyncio.gather(
        tikapi_task, tiktok_live_task
    )
    
    # 一致判定
    match = None
    if tikapi_result["success"] and tiktok_live_result["success"]:
        match = tikapi_result["is_live"] == tiktok_live_result["is_live"]
    
    return TestResult(
        username=username,
        tikapi_success=tikapi_result["success"],
        tikapi_is_live=tikapi_result["is_live"],
        tikapi_response_time=tikapi_result["response_time"],
        tikapi_error=tikapi_result["error"],
        tiktok_live_success=tiktok_live_result["success"],
        tiktok_live_is_live=tiktok_live_result["is_live"],
        tiktok_live_response_time=tiktok_live_result["response_time"],
        tiktok_live_error=tiktok_live_result["error"],
        match=match,
        tested_at=datetime.now()
    )

@app.post("/compare/bulk", response_model=ComparisonStats)
async def compare_bulk_users(request: BulkTestRequest):
    """TikAPI vs TikTokLiveの比較（一括）"""
    if not TIKAPI_KEY:
        raise HTTPException(status_code=500, detail="TIKAPI_KEY not configured")
    
    results = []
    
    for username in request.usernames:
        result = await compare_single_user(username)
        results.append(result)
        
        # レート制限回避
        await asyncio.sleep(0.5)
    
    # 統計計算
    total = len(results)
    tikapi_success = sum(1 for r in results if r.tikapi_success)
    tiktok_live_success = sum(1 for r in results if r.tiktok_live_success)
    matches = sum(1 for r in results if r.match is True)
    
    tikapi_times = [r.tikapi_response_time for r in results if r.tikapi_response_time]
    tiktok_live_times = [r.tiktok_live_response_time for r in results if r.tiktok_live_response_time]
    
    tikapi_avg = sum(tikapi_times) / len(tikapi_times) if tikapi_times else 0
    tiktok_live_avg = sum(tiktok_live_times) / len(tiktok_live_times) if tiktok_live_times else 0
    
    return ComparisonStats(
        total_tests=total,
        tikapi_success_rate=(tikapi_success / total) * 100,
        tiktok_live_success_rate=(tiktok_live_success / total) * 100,
        match_rate=(matches / total) * 100 if matches > 0 else 0,
        tikapi_avg_response_time=round(tikapi_avg, 2),
        tiktok_live_avg_response_time=round(tiktok_live_avg, 2),
        results=results
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
