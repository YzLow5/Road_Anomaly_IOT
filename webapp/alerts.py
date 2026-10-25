"""
Quyết định KHI NÀO phát cảnh báo, để còi không kêu vì một khung hình nhiễu
và không kêu liên tục khi xe đứng yên trước ổ gà.

Quy tắc cho từng loại bất thường:
  1. Phải thấy liên tiếp ít nhất CONFIRM_FRAMES khung hình.
  2. Đã báo rồi thì phải chờ ALERT_COOLDOWN giây mới báo lại.
  3. Mất dấu (khung không thấy) thì đếm lại từ đầu.
Ổ gà được ưu tiên báo trước gờ giảm tốc vì nguy hiểm hơn.
"""

from dataclasses import dataclass, field

PRIORITY = {"pothole": 0, "speed_bump": 1}


@dataclass
class _Track:
    seen_in_a_row: int = 0
    last_alert_at: float = float("-inf")


@dataclass
class AlertPolicy:
    confirm_frames: int = 2
    cooldown: float = 2.0
    _tracks: dict = field(default_factory=lambda: {k: _Track() for k in PRIORITY})

    def update(self, labels_in_frame: set[str], now: float) -> list[str]:
        """Gọi 1 lần cho mỗi khung đã chạy model. Trả các loại cần cảnh báo ngay."""
        ready = []
        for label, track in self._tracks.items():
            if label not in labels_in_frame:
                track.seen_in_a_row = 0
                continue
            track.seen_in_a_row += 1
            if (track.seen_in_a_row >= self.confirm_frames
                    and now - track.last_alert_at >= self.cooldown):
                track.last_alert_at = now
                ready.append(label)
        return sorted(ready, key=PRIORITY.get)

    def streak(self, label: str) -> int:
        return self._tracks[label].seen_in_a_row
