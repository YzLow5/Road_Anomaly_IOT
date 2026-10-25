"""
Luồng xử lý chính: lấy khung mới nhất từ camera → chạy model → quyết định cảnh
báo → gửi lệnh còi tới xe, Telegram, ghi nhật ký.

Luồng này chạy độc lập với camera: camera luôn đọc ở tốc độ của nó, model xử lý
khung mới nhất mỗi khi rảnh, nên ảnh trên web không bị khựng khi model chậm.
"""

import csv
import threading
import time

from webapp import config, overlay
from webapp.alerts import AlertPolicy
from webapp.camera import Camera
from webapp.detector import RoadDetector
from webapp.device import car
from webapp.notify import telegram
from webapp.store import Store

LOG_FILE = config.PROJECT_ROOT / "detection_log.csv"


class Pipeline(threading.Thread):
    def __init__(self, camera: Camera, detector: RoadDetector, store: Store):
        super().__init__(name="pipeline", daemon=True)
        self.camera = camera
        self.detector = detector
        self.store = store
        self.policy = AlertPolicy(config.CONFIRM_FRAMES, config.ALERT_COOLDOWN)
        self._running = threading.Event()

    def stop(self) -> None:
        self._running.clear()

    def run(self) -> None:
        self._running.set()
        last_index = 0
        while self._running.is_set():
            frame = self.camera.latest()
            if frame is None or frame.index == last_index:
                time.sleep(0.005)
                continue
            last_index = frame.index

            started = time.perf_counter()
            detections = [d.to_dict() for d in self.detector.detect(frame.image)]
            infer_ms = (time.perf_counter() - started) * 1000
            self.store.set_detections(detections, frame.index, infer_ms)

            best = {}
            for det in detections:
                if det["confidence"] > best.get(det["label"], {"confidence": 0})["confidence"]:
                    best[det["label"]] = det
            ready = self.policy.update(set(best), time.time())
            for i, label in enumerate(ready):
                # Cùng lúc thấy cả 2 loại: còi chỉ kêu kiểu của loại nguy hiểm hơn (ổ gà),
                # vì lệnh sau sẽ ghi đè tiếng còi của lệnh trước trên xe.
                self._raise_alert(label, best[label]["confidence"], frame.image, detections,
                                  ring_car=(i == 0))

    def _raise_alert(self, label: str, confidence: float, image, detections,
                     ring_car: bool = True) -> None:
        if ring_car:
            car.send_alert(label)
        event = self.store.add_event(label, confidence)
        if telegram.enabled:
            telegram.send(label, confidence, overlay.to_jpeg(overlay.draw(image, detections)))
        try:
            new_file = not LOG_FILE.exists()
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if new_file:
                    writer.writerow(["time", "label", "confidence"])
                writer.writerow([event["time"], label, event["confidence"]])
        except OSError as e:
            print(f"[WARN] Không ghi được nhật ký: {e}")
        print(f"[CẢNH BÁO] {event['time']} {event['label_vi']} ({confidence:.0%})")
