"""
Kho dữ liệu dùng chung giữa luồng xử lý và các API web (có khóa luồng).
"""

import threading
import time
from collections import deque

LABEL_VI = {"pothole": "Ổ gà", "speed_bump": "Gờ giảm tốc"}


class Store:
    def __init__(self, max_events: int = 300):
        self._lock = threading.Lock()
        self.started_at = time.time()
        self.detections: list[dict] = []
        self.detections_frame = 0
        self.infer_ms = 0.0
        self.events: deque = deque(maxlen=max_events)
        self._next_event_id = 1
        self.counts = {"pothole": 0, "speed_bump": 0}

    def set_detections(self, detections: list[dict], frame_index: int, infer_ms: float) -> None:
        with self._lock:
            self.detections = detections
            self.detections_frame = frame_index
            self.infer_ms = infer_ms

    def get_detections(self) -> list[dict]:
        with self._lock:
            return list(self.detections)

    def add_event(self, label: str, confidence: float) -> dict:
        with self._lock:
            event = {
                "id": self._next_event_id,
                "time": time.strftime("%H:%M:%S"),
                "epoch": time.time(),
                "label": label,
                "label_vi": LABEL_VI[label],
                "confidence": round(confidence, 3),
            }
            self._next_event_id += 1
            self.events.append(event)
            self.counts[label] += 1
            return event

    def events_after(self, event_id: int) -> list[dict]:
        with self._lock:
            return [e for e in self.events if e["id"] > event_id]

    def summary(self) -> dict:
        with self._lock:
            last = self.events[-1] if self.events else None
            return {
                "detections": list(self.detections),
                "infer_ms": round(self.infer_ms),
                "counts": dict(self.counts),
                "last_event": dict(last, seconds_ago=round(time.time() - last["epoch"], 1))
                if last else None,
                "uptime_s": round(time.time() - self.started_at),
            }
