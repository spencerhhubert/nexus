from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from .client import API
from robot.our_types import SystemLifecycleStage

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_client: Optional[API] = None


def init_api(controller):
    global api_client
    api_client = API(controller)


@app.get("/lifecycle", response_model=SystemLifecycleStage)
async def get_lifecycle():
    if not api_client:
        raise HTTPException(status_code=503, detail="API not initialized")
    return api_client.get_lifecycle_stage()


@app.put("/pause")
async def pause_system():
    if not api_client:
        raise HTTPException(status_code=503, detail="API not initialized")
    api_client.pause()
    return {"success": True}


@app.put("/resume")
async def resume_system():
    if not api_client:
        raise HTTPException(status_code=503, detail="API not initialized")
    api_client.resume()
    return {"success": True}
