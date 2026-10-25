"""
Web server FastAPI: dashboard, luồng ảnh có khung, và các API trạng thái.

    GET  /                  dashboard
    GET  /stream.mjpg       ảnh camera đã vẽ khung phát hiện (MJPEG)
    GET  /api/status        trạng thái camera, xe, model, phát hiện hiện tại
    GET  /api/events?after= nhật ký cảnh báo mới hơn id cho trước
    POST /api/test-alert    bấm thử còi trên xe {"type": "pothole" | "speed_bump"}
"""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from webapp import config, overlay
from webapp.camera import Camera
from webapp.detector import LABELS, RoadDetector
from webapp.device import car
from webapp.notify import telegram
from webapp.pipeline import Pipeline
from webapp.store import Store

STATIC = config.PROJECT_ROOT / "webapp" / "static"
STREAM_FPS = 15

store = Store()
detector = RoadDetector()
camera = Camera(os.environ.get("CAMERA_SOURCE") or config.CAMERA_SOURCE)
pipeline = Pipeline(camera, detector, store)


@asynccontextmanager
async def lifespan(_: FastAPI):
    print("Khởi động hệ thống…")
    await asyncio.to_thread(detector.load)
    camera.start()
    pipeline.start()
    car.start()
    if telegram.enabled:
        print("  Telegram: bật")
    yield
    pipeline.stop()
    camera.stop()
    car.stop()


app = FastAPI(title="Cảnh báo bất thường mặt đường", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/stream.mjpg")
async def stream():
    async def frames():
        last = 0
        while True:
            frame = camera.latest()
            if frame is not None and frame.index != last:
                last = frame.index
                jpeg = await asyncio.to_thread(
                    lambda: overlay.to_jpeg(overlay.draw(frame.image, store.get_detections())))
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            await asyncio.sleep(1 / STREAM_FPS)

    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/status")
async def status():
    return {
        "camera": {"source": str(camera.source), "kind": camera.kind,
                   "online": camera.online, "fps": round(camera.fps, 1)},
        "car": car.snapshot(),
        "models": detector.model_files,
        "settings": {"confidence": config.CONFIDENCE, "confirm_frames": config.CONFIRM_FRAMES,
                     "cooldown_s": config.ALERT_COOLDOWN},
        **store.summary(),
    }


@app.get("/api/events")
async def events(after: int = 0):
    return {"events": store.events_after(after)}


class TestAlert(BaseModel):
    type: str = "pothole"


@app.post("/api/test-alert")
async def test_alert(body: TestAlert):
    if body.type not in LABELS:
        raise HTTPException(400, f"type phải là một trong {list(LABELS)}")
    if not car.snapshot()["configured"]:
        raise HTTPException(400, "Chưa đặt ESP32_IP trong file .env")
    return JSONResponse({"queued": car.send_alert(body.type), "type": body.type})
