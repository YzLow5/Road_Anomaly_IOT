# Nối dây và cấp nguồn trên xe (không hàn)

## Linh kiện trên xe

- ESP32-CAM (board AI Thinker)
- Còi báo cháy lab 1 (module còi 3 chân: VCC, GND, I/O)
- Breadboard mini 170 lỗ
- Module nguồn breadboard có cổng USB (hoặc cáp USB ra đầu Dupont)
- Sạc dự phòng + cáp USB
- Dây Dupont

## Bảng nối dây

| Chân | Nối tới |
| --- | --- |
| ESP32-CAM `5V` | 5V của module nguồn |
| ESP32-CAM `GND` | GND của module nguồn |
| Còi `VCC` | 5V của module nguồn |
| Còi `GND` | GND của module nguồn |
| Còi `I/O` | ESP32-CAM `GPIO 13` |

Sạc dự phòng → cáp USB → module nguồn breadboard → cấp 5V cho cả ESP32-CAM và còi.

## Lưu ý

- **Đế MB che hết chân GPIO.** Chỉ cắm ESP32-CAM vào đế MB lúc nạp code qua USB. Nạp xong tháo ra, cắm lên breadboard trên xe. Từ lần sau nạp qua Wi-Fi (OTA).
- **Chân nên tránh:** GPIO 12 (ảnh hưởng điện áp flash lúc khởi động), GPIO 4 (đèn flash), GPIO 0 (chế độ nạp code), GPIO 1/3 (Serial).
- **Chân rảnh khi không dùng thẻ SD:** GPIO 13, 14, 15, 2. Có thêm module LED 3 màu thì dùng 14, 15, 2.
- **Còi kêu liên tục ngay khi bật nguồn:** còi kích mức thấp → đổi `BUZZER_ACTIVE_LOW` thành `1` trong `config.h`.
- **Còi chỉ kêu "tách":** còi thụ động → đổi `BUZZER_PASSIVE` thành `1`.
- **Còi trần 2 chân (không có module):** không nối thẳng vào GPIO; mua module còi có transistor.
- **ESP32-CAM tự khởi động lại liên tục / "Brownout detector":** nguồn yếu. Dùng cáp USB ngắn, tốt; cấp đúng chân 5V (không phải 3.3V).
- **Sạc dự phòng tự tắt:** một số loại ngắt khi dòng thấp; thử chạy liên tục 20 phút trước buổi demo.

## Gắn camera

Camera chúc về phía trước 30–45°, để khung hình thấy mặt đường cách đầu xe khoảng 15–30 cm.
Như vậy laptop kịp phát hiện và gửi lệnh còi trước khi xe tới chỗ bất thường.
Ảnh bị ngược: đổi `CAMERA_VFLIP` / `CAMERA_HMIRROR` trong `config.h`.
