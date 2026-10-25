"""Vẽ khung phát hiện lên ảnh và nén JPEG để gửi lên web / Telegram."""

import cv2
import numpy as np

# Màu BGR cho từng loại; chữ không dấu vì OpenCV không vẽ được tiếng Việt có dấu.
STYLE = {
    "pothole": ((40, 40, 230), "O GA"),
    "speed_bump": ((0, 190, 255), "GO GIAM TOC"),
}
MAX_WIDTH = 960


def draw(image: np.ndarray, detections: list[dict]) -> np.ndarray:
    h, w = image.shape[:2]
    if w > MAX_WIDTH:
        image = cv2.resize(image, (MAX_WIDTH, int(h * MAX_WIDTH / w)))
        h, w = image.shape[:2]
    else:
        image = image.copy()
    thickness = max(2, w // 320)
    for det in detections:
        color, text = STYLE[det["label"]]
        x1, y1, x2, y2 = det["box"]
        p1, p2 = (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h))
        cv2.rectangle(image, p1, p2, color, thickness)
        caption = f"{text} {det['confidence']:.0%}"
        (tw, th), _ = cv2.getTextSize(caption, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        top = max(p1[1] - th - 8, 0)
        cv2.rectangle(image, (p1[0], top), (p1[0] + tw + 8, top + th + 8), color, -1)
        cv2.putText(image, caption, (p1[0] + 4, top + th + 3), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return image


def to_jpeg(image: np.ndarray, quality: int = 80) -> bytes:
    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes() if ok else b""
