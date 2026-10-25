"""
Chụp ảnh dataset liên tục từ ESP32-CAM trong lúc kéo xe qua mô hình.

    python tools/capture_dataset.py --ip 192.168.43.50 --n 200 --interval 0.5
    python tools/capture_dataset.py --ip 192.168.43.50 --out dataset_raw/o_ga --n 80

Mỗi ảnh lấy từ http://<ip>/capture. Ảnh trùng nhau (xe đứng yên) tự bị bỏ qua.
Sau khi chụp: lọc ảnh mờ, rồi upload lên Roboflow để gán nhãn khung.
"""

import argparse
import hashlib
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description="Chụp ảnh dataset từ ESP32-CAM")
    ap.add_argument("--ip", required=True, help="IP của xe, ví dụ 192.168.43.50")
    ap.add_argument("--n", type=int, default=200, help="số ảnh cần lưu (mặc định 200)")
    ap.add_argument("--interval", type=float, default=0.5, help="giây giữa 2 lần chụp")
    ap.add_argument("--out", default="dataset_raw/esp32", help="thư mục lưu ảnh")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    url = f"http://{args.ip}/capture"
    seen: set[str] = set()
    saved = errors = 0
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"Chụp từ {url} → {out.resolve()}  (Ctrl+C để dừng sớm)")
    try:
        while saved < args.n:
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = resp.read()
            except (urllib.error.URLError, OSError) as e:
                errors += 1
                print(f"  lỗi: {e}")
                if errors >= 10:
                    print("Lỗi 10 lần liên tiếp — kiểm tra IP, Wi-Fi và nguồn của xe.")
                    break
                time.sleep(1)
                continue
            errors = 0
            digest = hashlib.md5(data).hexdigest()
            if digest in seen:
                time.sleep(args.interval)
                continue
            seen.add(digest)
            (out / f"esp32_{stamp}_{saved:04d}.jpg").write_bytes(data)
            saved += 1
            print(f"  {saved}/{args.n}", end="\r")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    print(f"\nĐã lưu {saved} ảnh vào {out}")


if __name__ == "__main__":
    main()
