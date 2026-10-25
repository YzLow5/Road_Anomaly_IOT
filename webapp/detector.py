"""
Bọc model YOLOv8: nạp model, chạy trên một khung hình, trả danh sách phát hiện
với nhãn chuẩn của hệ thống: "pothole" (ổ gà) hoặc "speed_bump" (gờ giảm tốc).

Ưu tiên model của nhóm (MODEL_PATH, 2 lớp). Khi chưa có, dùng 2 model mẫu trong
models/sample/ để chạy thử.
"""

from dataclasses import dataclass

import numpy as np

from webapp import config

LABELS = ("pothole", "speed_bump")
SAMPLE_MODELS = [
    config.PROJECT_ROOT / "models" / "sample" / "pothole_best.pt",
    config.PROJECT_ROOT / "models" / "sample" / "speedbump_best.pt",
]


@dataclass
class Detection:
    label: str            # "pothole" | "speed_bump"
    confidence: float
    box: tuple            # (x1, y1, x2, y2) theo tỉ lệ 0–1 của ảnh

    def to_dict(self) -> dict:
        return {"label": self.label, "confidence": round(self.confidence, 3),
                "box": [round(v, 4) for v in self.box]}


def to_system_label(class_name: str) -> str | None:
    """Quy tên lớp của model bất kỳ về nhãn của hệ thống; lớp khác trả None."""
    name = class_name.lower().replace("-", " ").replace("_", " ")
    if "pothole" in name:
        return "pothole"
    if any(word in name for word in ("bump", "hump", "breaker", "speed")):
        return "speed_bump"
    return None


def pick_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


class RoadDetector:
    def __init__(self):
        self.device = pick_device()
        self.models: list = []
        self.model_files: list[str] = []

    def load(self) -> None:
        from ultralytics import YOLO

        paths = [config.MODEL_PATH] if config.MODEL_PATH.exists() else \
            [p for p in SAMPLE_MODELS if p.exists()]
        if not config.MODEL_PATH.exists():
            print(f"[INFO] Chưa có {config.MODEL_PATH.name}, dùng model mẫu để chạy thử")
        for path in paths:
            model = YOLO(str(path))
            model.to(self.device)
            self.models.append(model)
            self.model_files.append(path.name)
            print(f"  model {path.name} ({self.device}): {model.names}")
        if not self.models:
            print("[LỖI] Không có model nào trong models/")

    def detect(self, image: np.ndarray) -> list[Detection]:
        h, w = image.shape[:2]
        found: list[Detection] = []
        for model in self.models:
            result = model.predict(image, conf=config.CONFIDENCE, imgsz=config.IMG_SIZE,
                                   verbose=False)[0]
            for cls, conf, xyxy in zip(result.boxes.cls.tolist(), result.boxes.conf.tolist(),
                                       result.boxes.xyxy.tolist()):
                label = to_system_label(result.names[int(cls)])
                if label is None:
                    continue
                x1, y1, x2, y2 = xyxy
                found.append(Detection(label, float(conf), (x1 / w, y1 / h, x2 / w, y2 / h)))
        return found
