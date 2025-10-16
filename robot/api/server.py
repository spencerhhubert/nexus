import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from .client import API
from robot.our_types import SystemLifecycleStage
from robot.our_types.irl_runtime_params import IRLSystemRuntimeParams
from robot.our_types.bricklink import BricklinkPartData
from robot.our_types.bin_state import BinState
from robot.piece.bricklink.api import getPartInfo, getCategoryInfo, getCategories
from robot.piece.bricklink.auth import mkAuth
from robot.piece.bricklink.types import BricklinkCategoryData
from typing import List
from robot.websocket_manager import WebSocketManager
from robot.global_config import GlobalConfig

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_client: Optional[API] = None
websocket_manager: Optional[WebSocketManager] = None


def init_api(controller, gc: Optional[GlobalConfig] = None) -> WebSocketManager:
    global api_client, websocket_manager

    if gc is not None and websocket_manager is None:
        websocket_manager = WebSocketManager(gc)

    if controller is not None:
        api_client = API(controller)

    if websocket_manager is None:
        raise RuntimeError(
            "WebSocketManager not initialized - call init_api with gc first"
        )

    return websocket_manager


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


@app.put("/run")
async def run_system():
    if not api_client:
        raise HTTPException(status_code=503, detail="API not initialized")
    api_client.run()
    return {"success": True}


@app.get("/irl-runtime-params")
async def get_irl_runtime_params() -> IRLSystemRuntimeParams:
    if not api_client:
        raise HTTPException(status_code=503, detail="API not initialized")
    return api_client.getIRLRuntimeParams()


@app.put("/irl-runtime-params")
async def update_irl_runtime_params(params: IRLSystemRuntimeParams):
    if not api_client:
        raise HTTPException(status_code=503, detail="API not initialized")
    api_client.updateIRLRuntimeParams(params)
    return {"success": True}


@app.get("/bin-state")
async def get_bin_state() -> BinState:
    if not api_client:
        raise HTTPException(status_code=503, detail="API not initialized")
    return api_client.getBinState()


@app.put("/bin-state")
async def update_bin_state(request: dict):
    if not api_client:
        raise HTTPException(status_code=503, detail="API not initialized")

    coordinates = {
        "distribution_module_idx": request["distribution_module_idx"],
        "bin_idx": request["bin_idx"],
    }
    category_id = request.get("category_id")

    api_client.updateBinCategory(coordinates, category_id)
    return {"success": True}


@app.get("/bricklink/part/{part_id}/")
async def get_bricklink_part_info(part_id: str) -> BricklinkPartData:
    try:
        auth = mkAuth()
        part_data = getPartInfo(part_id, auth)

        if not part_data:
            raise HTTPException(status_code=404, detail=f"Part '{part_id}' not found")

        return part_data
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch part info: {str(e)}"
        )


@app.get("/bricklink/category/{category_id}")
async def get_bricklink_category_info(category_id: int) -> BricklinkCategoryData:
    try:
        auth = mkAuth()
        category_data = getCategoryInfo(category_id, auth)

        if not category_data:
            raise HTTPException(
                status_code=404, detail=f"Category '{category_id}' not found"
            )

        return category_data
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch category info: {str(e)}"
        )


@app.get("/bricklink/categories")
async def get_bricklink_categories() -> List[BricklinkCategoryData]:
    try:
        auth = mkAuth()
        categories = getCategories(auth)
        return categories
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch categories: {str(e)}"
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if websocket_manager is None:
        await websocket.close()
        return

    websocket_manager.set_event_loop(asyncio.get_event_loop())

    await websocket_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
