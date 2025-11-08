"""
TikAPI Test System - Minimal Version
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

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

@app.get("/")
async def root():
    """システム情報"""
    return {
        "message": "TikAPI Test System",
        "version": "1.0.0 - Minimal",
        "status": "running",
        "tikapi_configured": TIKAPI_KEY is not None,
        "tikapi_key_length": len(TIKAPI_KEY) if TIKAPI_KEY else 0
    }

@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
