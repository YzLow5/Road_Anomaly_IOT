"""
Cấu hình chung của server, đọc từ file .env ở thư mục gốc dự án.

Sao chép .env.example thành .env rồi sửa giá trị. Biến môi trường thật
(nếu có) được ưu tiên hơn giá trị trong .env.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def _load_env_file(path: Path) -> None:
    """Đọc file .env dạng KEY=VALUE, bỏ qua dòng trống và dòng bắt đầu bằng #."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_env_file(PROJECT_ROOT / ".env")


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


def _get_float(name: str, default: float) -> float:
    try:
        return float(_get(name, str(default)))
    except ValueError:
        return default


# ── Nguồn camera ───────────────────────────────────────────────────────────
# Số (0, 1) = webcam laptop; URL = stream ESP32-CAM; đường dẫn = file video.
# Để trống thì tự lấy stream của ESP32_IP.
ESP32_IP = _get("ESP32_IP", "")
CAMERA_SOURCE = _get("CAMERA_SOURCE", "")
if not CAMERA_SOURCE:
    CAMERA_SOURCE = f"http://{ESP32_IP}:81/stream" if ESP32_IP else "0"

# ── Model ──────────────────────────────────────────────────────────────────
# Model 2 lớp của nhóm (0 = pothole, 1 = speed_bump). Nếu file chưa có,
# server dùng 2 model mẫu trong models/sample/ để chạy thử.
MODEL_PATH = PROJECT_ROOT / _get("MODEL_PATH", "models/road_best.pt")
CONFIDENCE = _get_float("CONFIDENCE", 0.5)
IMG_SIZE = int(_get_float("IMG_SIZE", 416))   # ảnh đưa vào model; nhỏ hơn thì nhanh hơn

# Số khung hình liên tiếp phải thấy cùng một loại bất thường mới cảnh báo
# (chống báo giả do một khung hình nhiễu).
CONFIRM_FRAMES = int(_get_float("CONFIRM_FRAMES", 2))

# Sau khi đã báo một loại, chờ bao nhiêu giây mới báo lại loại đó.
ALERT_COOLDOWN = _get_float("ALERT_COOLDOWN", 2.0)

# Khung quá tối (độ sáng trung bình) hoặc gần như một màu (độ lệch chuẩn) thường
# là camera bị che: bỏ qua, không chạy model. Thang 0–255 trên ảnh xám.
MIN_BRIGHTNESS = _get_float("MIN_BRIGHTNESS", 40)
MIN_CONTRAST = _get_float("MIN_CONTRAST", 15)

# ── Thiết bị trên xe ───────────────────────────────────────────────────────
DEVICE_TIMEOUT = _get_float("DEVICE_TIMEOUT", 0.5)

# ── Telegram (để trống = tắt) ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = _get("TELEGRAM_CHAT_ID", "")
