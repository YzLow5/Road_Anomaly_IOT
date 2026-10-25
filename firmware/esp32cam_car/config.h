// =====================================================================
//  Cấu hình ESP32-CAM trên xe — SỬA FILE NÀY trước khi nạp code.
//  Các giá trị phải khớp bảng "Hợp đồng giao tiếp" trong README.
// =====================================================================
#pragma once

// ── Wi-Fi (chỉ 2.4GHz) ───────────────────────────────────────────────
#define WIFI_SSID      "IOT-ROAD"          // tên hotspot điện thoại dùng chung
#define WIFI_PASSWORD  "doi-mat-khau-o-day"

// ── IP tĩnh: để laptop luôn biết địa chỉ xe ──────────────────────────
// Hotspot Android thường cấp dải 192.168.43.x, iPhone là 172.20.10.x.
// Nạp code lần đầu với USE_STATIC_IP 0, xem Serial Monitor để biết dải IP,
// rồi đổi về 1 và điền IP nằm trong dải đó.
#define USE_STATIC_IP  1
#define STATIC_IP      192, 168, 43, 50
#define GATEWAY_IP     192, 168, 43, 1
#define SUBNET_MASK    255, 255, 255, 0

// ── Còi ──────────────────────────────────────────────────────────────
// GPIO 13 rảnh khi không dùng thẻ SD. Tránh GPIO 12 (ảnh hưởng khởi động)
// và GPIO 4 (đèn flash).
#define BUZZER_PIN         13
// Nạp xong mà còi kêu liên tục khi chưa có cảnh báo → đổi thành 1.
#define BUZZER_ACTIVE_LOW  0
// 1 = còi thụ động (cấp điện chỉ kêu "tách"), cần phát xung PWM.
#define BUZZER_PASSIVE     0
#define BUZZER_TONE_HZ     2500

// ── Camera ───────────────────────────────────────────────────────────
// FRAMESIZE_VGA (640x480) cân bằng giữa độ nét và độ trễ.
// Stream giật/trễ thì hạ xuống FRAMESIZE_HVGA (480x320) hoặc FRAMESIZE_QVGA.
#define CAMERA_FRAME_SIZE  FRAMESIZE_VGA
#define CAMERA_JPEG_QUALITY 12             // 10–63, càng nhỏ càng nét, ảnh càng nặng
#define CAMERA_VFLIP       0               // camera gắn ngược thì đổi thành 1
#define CAMERA_HMIRROR     0

// ── Nạp code qua Wi-Fi (OTA) ─────────────────────────────────────────
#define OTA_HOSTNAME   "xe-esp32cam"
#define OTA_PASSWORD   "iotroad"
