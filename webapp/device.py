"""
Giao tiếp với ESP32-CAM trên xe qua HTTP.

- send_alert(label): bảo xe kêu còi. Chạy ở luồng riêng nên không bao giờ
  làm chậm luồng nhận diện.
- Luồng nền hỏi /status mỗi vài giây để biết xe còn online hay không.

Hợp đồng giao tiếp (xem README):
    GET http://<ip-xe>/alert?type=pothole | speed_bump  → 200 "OK"
    GET http://<ip-xe>/status                           → JSON
"""

import json
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from webapp import config

VALID_TYPES = {"pothole", "speed_bump"}
STATUS_INTERVAL = 3.0


class CarDevice:
    def __init__(self, ip: str, timeout: float = 0.5):
        self.ip = ip.strip()
        self.timeout = timeout
        self._queue: "queue.Queue[str]" = queue.Queue(maxsize=4)
        self._lock = threading.Lock()
        self._online = False
        self._device_info: dict = {}
        self._last_alert: dict | None = None
        self._stop = threading.Event()

    # ── Vòng đời ──────────────────────────────────────────────────────────
    def start(self) -> None:
        if not self.ip:
            print("  [INFO] Chưa đặt ESP32_IP — bỏ qua lệnh còi tới xe")
            return
        threading.Thread(target=self._alert_worker, daemon=True).start()
        threading.Thread(target=self._status_worker, daemon=True).start()
        print(f"  ✓ Xe ESP32-CAM: http://{self.ip}")

    def stop(self) -> None:
        self._stop.set()

    # ── API cho engine ────────────────────────────────────────────────────
    def send_alert(self, label: str) -> bool:
        """Xếp lệnh còi vào hàng đợi. Trả False nếu bỏ qua."""
        if not self.ip or label not in VALID_TYPES:
            return False
        try:
            self._queue.put_nowait(label)
            return True
        except queue.Full:
            return False   # xe đang bận kêu, bỏ lệnh thừa

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "configured": bool(self.ip),
                "ip": self.ip,
                "online": self._online,
                "info": dict(self._device_info),
                "last_alert": dict(self._last_alert) if self._last_alert else None,
            }

    # ── Luồng nền ─────────────────────────────────────────────────────────
    def _get(self, path: str) -> bytes:
        url = f"http://{self.ip}{path}"
        with urllib.request.urlopen(url, timeout=self.timeout) as resp:
            return resp.read()

    def _alert_worker(self) -> None:
        while not self._stop.is_set():
            try:
                label = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            started = time.time()
            ok, error = True, ""
            try:
                self._get("/alert?" + urllib.parse.urlencode({"type": label}))
            except (urllib.error.URLError, OSError) as e:
                ok, error = False, str(e)
            with self._lock:
                self._last_alert = {
                    "type": label,
                    "ok": ok,
                    "error": error,
                    "latency_ms": round((time.time() - started) * 1000),
                    "time": datetime.now().strftime("%H:%M:%S"),
                }
                if ok:
                    self._online = True
            if not ok:
                print(f"[WARN] Không gửi được lệnh còi tới xe: {error}")

    def _status_worker(self) -> None:
        while not self._stop.is_set():
            try:
                info = json.loads(self._get("/status").decode("utf-8"))
                online = True
            except (urllib.error.URLError, OSError, ValueError):
                info, online = {}, False
            with self._lock:
                self._online = online
                if online:
                    self._device_info = info
            self._stop.wait(STATUS_INTERVAL)


car = CarDevice(config.ESP32_IP, timeout=config.DEVICE_TIMEOUT)
