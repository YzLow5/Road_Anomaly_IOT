"""
Chạy hệ thống trên laptop.

    python main.py                         nguồn camera lấy từ .env
    python main.py --source 0              webcam laptop
    python main.py --source duong.mp4      file video
    python main.py --source http://192.168.43.50:81/stream

Sau đó mở http://localhost:8000
"""

import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Hệ thống cảnh báo bất thường mặt đường")
    parser.add_argument("--source", help="0 = webcam, URL = stream ESP32-CAM, đường dẫn = video")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.source is not None:
        os.environ["CAMERA_SOURCE"] = args.source
    print(f"Dashboard: http://localhost:{args.port}  (Ctrl+C để dừng)")
    uvicorn.run("webapp.app:app", host="0.0.0.0", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
