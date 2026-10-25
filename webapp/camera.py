"""
Đọc ảnh từ nguồn camera trong một luồng riêng và luôn giữ khung mới nhất.

Nguồn có thể là:
    "0", "1"                        webcam laptop
    "http://<ip-xe>:81/stream"      stream MJPEG của ESP32-CAM
    "duong_pho.mp4"                 file video (phát lặp, đúng tốc độ gốc)

Stream hoặc webcam bị ngắt thì tự mở lại sau RETRY_SECONDS.
"""

import sys
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np

RETRY_SECONDS = 2.0
MAX_READ_FAILURES = 20


@dataclass
class Frame:
    image: np.ndarray
    index: int
    timestamp: float


def describe_source(source: str) -> tuple[object, str]:
    """Trả (giá trị cho cv2.VideoCapture, loại nguồn)."""
    source = source.strip()
    if source.isdigit():
        return int(source), "webcam"
    if source.lower().startswith(("http://", "https://", "rtsp://")):
        return source, "stream"
    return source, "file"


class Camera(threading.Thread):
    def __init__(self, source: str):
        super().__init__(name="camera", daemon=True)
        self.source, self.kind = describe_source(source)
        self._lock = threading.Lock()
        self._frame: Frame | None = None
        self._count = 0
        self._online = False
        self._running = threading.Event()
        self._fps_window: list[float] = []

    # ── API ───────────────────────────────────────────────────────────────
    def latest(self) -> Frame | None:
        with self._lock:
            return self._frame

    @property
    def online(self) -> bool:
        return self._online

    @property
    def fps(self) -> float:
        with self._lock:
            w = self._fps_window
            if len(w) < 2 or w[-1] == w[0]:
                return 0.0
            return (len(w) - 1) / (w[-1] - w[0])

    def stop(self) -> None:
        self._running.clear()

    # ── Luồng đọc ảnh ─────────────────────────────────────────────────────
    def run(self) -> None:
        self._running.set()
        print(f"Camera ({self.kind}): {self.source}")
        while self._running.is_set():
            cap = self._open()
            if cap is None:
                if self.kind == "file":
                    print(f"[LỖI] Không mở được file video {self.source}")
                    return
                print(f"[WARN] Chưa kết nối được camera, thử lại sau {RETRY_SECONDS:.0f}s")
                time.sleep(RETRY_SECONDS)
                continue
            self._online = True
            self._read_until_broken(cap)
            cap.release()
            self._online = False
            if self._running.is_set() and self.kind != "file":
                print("[WARN] Mất kết nối camera, đang mở lại…")
                time.sleep(RETRY_SECONDS)

    def _open(self):
        backends = [cv2.CAP_ANY]
        if self.kind == "webcam":
            if sys.platform == "win32":
                backends.insert(0, cv2.CAP_DSHOW)      # mở webcam Windows nhanh hơn
            elif sys.platform == "darwin":
                backends.insert(0, cv2.CAP_AVFOUNDATION)
        for backend in backends:
            cap = cv2.VideoCapture(self.source, backend)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)    # bỏ ảnh cũ trong bộ đệm
                return cap
            cap.release()
        return None

    def _read_until_broken(self, cap) -> None:
        delay = 0.0
        if self.kind == "file":
            fps = cap.get(cv2.CAP_PROP_FPS)
            delay = 1.0 / fps if 1 <= fps <= 120 else 1 / 30
        failures = 0
        while self._running.is_set():
            ok, image = cap.read()
            if not ok:
                if self.kind == "file":
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                failures += 1
                if failures >= MAX_READ_FAILURES:
                    return
                time.sleep(0.05)
                continue
            failures = 0
            now = time.time()
            with self._lock:
                self._count += 1
                self._frame = Frame(image, self._count, now)
                self._fps_window = (self._fps_window + [now])[-30:]
            if delay:
                time.sleep(delay)
