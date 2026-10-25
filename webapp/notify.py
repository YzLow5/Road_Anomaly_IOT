"""
Gửi cảnh báo Telegram kèm ảnh khung hình lúc phát hiện.

Bật bằng cách điền TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID trong .env.
Cách lấy: chat với @BotFather để tạo bot lấy token; nhắn bot một câu rồi mở
https://api.telegram.org/bot<TOKEN>/getUpdates để xem chat id.
"""

import threading
import time
import urllib.parse
import urllib.request
import uuid

from webapp import config

LABEL_VI = {"pothole": "Ổ gà", "speed_bump": "Gờ giảm tốc"}
MIN_INTERVAL = 10.0   # giây giữa hai tin nhắn cùng loại, tránh spam


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self._last_sent: dict[str, float] = {}

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, label: str, confidence: float, jpeg: bytes | None) -> None:
        if not self.enabled:
            return
        now = time.time()
        if now - self._last_sent.get(label, 0) < MIN_INTERVAL:
            return
        self._last_sent[label] = now
        caption = (f"⚠️ Phát hiện {LABEL_VI.get(label, label)} phía trước "
                   f"({confidence:.0%}) lúc {time.strftime('%H:%M:%S')}")
        threading.Thread(target=self._send_photo, args=(caption, jpeg), daemon=True).start()

    def _send_photo(self, caption: str, jpeg: bytes | None) -> None:
        try:
            if jpeg:
                boundary = uuid.uuid4().hex
                body = b"".join([
                    self._field(boundary, "chat_id", self.chat_id),
                    self._field(boundary, "caption", caption),
                    (f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; "
                     f"filename=\"frame.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n").encode(),
                    jpeg, b"\r\n", f"--{boundary}--\r\n".encode(),
                ])
                req = urllib.request.Request(
                    f"https://api.telegram.org/bot{self.token}/sendPhoto", data=body,
                    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
            else:
                data = urllib.parse.urlencode({"chat_id": self.chat_id, "text": caption}).encode()
                req = urllib.request.Request(
                    f"https://api.telegram.org/bot{self.token}/sendMessage", data=data)
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as e:
            print(f"[WARN] Telegram: {e}")

    @staticmethod
    def _field(boundary: str, name: str, value: str) -> bytes:
        return (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                f"{value}\r\n").encode("utf-8")


telegram = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
