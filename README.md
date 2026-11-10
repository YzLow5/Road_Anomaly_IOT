# Hệ thống IoT-AI phát hiện bất thường mặt đường và cảnh báo giao thông thời gian thực

Đồ án môn IoT — nhóm 4 người, 26/10/2026 – 26/11/2026.

Một chiếc xe mô hình mang **ESP32-CAM + còi + sạc dự phòng** chạy trên đường xốp có ổ gà và gờ giảm tốc.
ESP32-CAM stream ảnh qua Wi-Fi về laptop; laptop chạy **YOLOv8** để phát hiện; khi thấy bất thường,
laptop **gửi lệnh còi ngược về xe**, hiện cảnh báo trên web dashboard và gửi Telegram.

```
 Xe mô hình (sạc dự phòng)                     Laptop
┌──────────────────────────┐   ảnh MJPEG   ┌──────────────────────────────┐
│ ESP32-CAM  ──GPIO 13──▶ Còi │ ───────────▶ │ webapp: YOLOv8 → cảnh báo     │──▶ Web dashboard
│            ◀───────────────│ ◀─────────── │ device.py gửi /alert          │──▶ Telegram
└──────────────────────────┘  lệnh /alert  └──────────────────────────────┘
                         cùng hotspot Wi-Fi 2.4GHz
```

## Cấu trúc thư mục

| Đường dẫn | Nội dung | Phụ trách |
| --- | --- | --- |
| `firmware/esp32cam_car/` | Code ESP32-CAM: stream, chụp ảnh, nhận lệnh còi, OTA | TV2 |
| `tools/capture_dataset.py` | Chụp ảnh dataset liên tục từ ESP32-CAM | TV2 |
| `tools/merge_datasets.py` | Gộp dataset Roboflow về 2 lớp `pothole`, `speed_bump` | TV1 |
| `training/train_colab.ipynb` | Notebook train YOLOv8n trên Google Colab | TV1 |
| `models/` | Model của nhóm (`road_best.pt`) + 2 model mẫu | TV1 |
| `main.py` | Chạy hệ thống trên laptop | TV3 |
| `webapp/camera.py` | Đọc ảnh từ ESP32-CAM / webcam / video, tự kết nối lại | TV3 |
| `webapp/detector.py` | Nạp model YOLOv8, phát hiện ổ gà và gờ giảm tốc | TV1 |
| `webapp/alerts.py` | Chống báo giả: xác nhận qua nhiều khung liên tiếp + thời gian chờ | TV1 |
| `webapp/pipeline.py` | Luồng xử lý: ảnh → model → cảnh báo | TV1 + TV3 |
| `webapp/device.py` | Gửi lệnh còi tới xe, theo dõi xe online/offline | TV3 |
| `webapp/notify.py` | Gửi Telegram kèm ảnh | TV3 |
| `webapp/app.py`, `webapp/static/` | API FastAPI + giao diện dashboard | TV3 |
| `docs/` | Báo cáo, sơ đồ nối dây, test case, biên bản họp | TV4 |

## Hợp đồng giao tiếp

Ba người làm chính dựa vào bảng này để làm song song. Đổi giá trị nào thì báo cả nhóm và sửa ở cả `config.h` lẫn `.env`.

| Mục | Giá trị |
| --- | --- |
| Wi-Fi | Hotspot điện thoại 2.4GHz `IOT-ROAD` |
| IP xe | `192.168.43.50` (sửa theo dải IP của hotspot) |
| Stream | `http://<ip-xe>:81/stream` |
| Chụp 1 ảnh | `http://<ip-xe>/capture` |
| Lệnh còi | `http://<ip-xe>/alert?type=pothole` hoặc `speed_bump` → `OK` |
| Trạng thái xe | `http://<ip-xe>/status` → JSON |
| Lớp model | `0 = pothole`, `1 = speed_bump`; ảnh không khung = bình thường |
| Kiểu còi | Ổ gà: tít dài 3 lần · Gờ: tít ngắn 2 lần |

## Chạy server trên laptop

Cần Python 3.10–3.13.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                 # macOS/Linux: cp .env.example .env
```

Chạy thử **không cần xe** (webcam laptop + model mẫu):

```bash
python main.py --source 0
```

Chạy với **xe ESP32-CAM** (điền `ESP32_IP` trong `.env` trước):

```bash
python main.py
```

Mở <http://localhost:8000>. Ô **Xe ESP32-CAM** bên phải cho biết xe online hay không, và có nút **Thử còi** để kiểm tra lệnh còi mà không cần model phát hiện gì. Khi có cảnh báo, dashboard hiện băng cảnh báo trên ảnh và kêu bíp trên laptop (bấm vào trang một lần để trình duyệt cho phép phát âm thanh).

Muốn test bằng video đường thật: `python main.py --source duong_pho.mp4`.

## Nạp code cho ESP32-CAM (TV2)

1. Cài [Arduino IDE 2](https://www.arduino.cc/en/software).
2. **File → Preferences → Additional boards manager URLs**, dán:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
3. **Tools → Board → Boards Manager**, tìm `esp32` của Espressif, bấm Install.
4. Mở `firmware/esp32cam_car/esp32cam_car.ino`. Sửa `config.h`: tên + mật khẩu Wi-Fi, IP tĩnh, chân còi.
5. **Tools → Board**: chọn **AI Thinker ESP32-CAM**. Cắm ESP32-CAM vào đế MB, nối USB, chọn cổng COM, bấm **Upload**.
   Báo lỗi `Failed to connect`: giữ nút **IO0** trên đế MB, bấm Upload, thấy `Connecting...` thì thả.
6. Mở **Serial Monitor** (115200 baud), bấm nút **RST**: sẽ thấy IP và các đường dẫn. Mở `http://<ip>/` trên trình duyệt để xem ảnh và bấm thử còi.
7. Lần sau sửa code: **Tools → Port** chọn cổng mạng `xe-esp32cam`, bấm Upload là nạp qua Wi-Fi (mật khẩu OTA trong `config.h`), không cần tháo xe.

Lần nạp đầu nên để `USE_STATIC_IP 0`, xem Serial Monitor để biết hotspot cấp dải IP nào, rồi mới đặt IP tĩnh trong dải đó.

Nối dây và cấp nguồn trên xe: xem [docs/noi-day.md](docs/noi-day.md).

## Dataset và train (TV1)

1. Tải dataset trên Roboflow Universe dạng **YOLOv8** (ví dụ *Road Objects*, *Humps/Bumps & Potholes*), giải nén vào `datasets/`.
2. Gộp và đổi nhãn về 2 lớp:
   ```bash
   python tools/merge_datasets.py datasets/road_objects datasets/humps_bumps --out datasets/road_merged
   ```
3. Chụp thêm ảnh trên mô hình bằng xe (TV2):
   ```bash
   python tools/capture_dataset.py --ip 192.168.43.50 --n 200 --interval 0.5
   ```
   Upload lên Roboflow, vẽ khung, export YOLOv8, rồi gộp chung ở bước 2.
4. Nén `datasets/road_merged` thành zip, train bằng `training/train_colab.ipynb` trên Colab.
5. Tải `road_best.pt` về đặt vào `models/`. Khởi động lại server là dùng model mới.

## Quy tắc làm việc với Git

- Nhánh theo mảng: `ai` (TV1), `iot` (TV2), `web` (TV3), `docs` (TV4). Cuối mỗi đợt merge vào `main`.
- Không commit `.env`, dataset, thư mục `runs/` (đã có trong `.gitignore`).
- Commit nhỏ, ghi rõ việc gì: `iot: thêm tự kết nối lại Wi-Fi`.

## Model mẫu

Hai file trong `models/sample/` là model ổ gà và gờ giảm tốc mẫu, lấy từ
[kdbell4/hazard-detector](https://github.com/kdbell4/hazard-detector), chỉ dùng để cả nhóm chạy thử hệ thống
trong lúc chưa train xong model của mình. Demo và báo cáo dùng model nhóm tự train (`models/road_best.pt`).
