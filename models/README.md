# Model

| File | Nội dung | Ghi chú |
| --- | --- | --- |
| `road_best.pt` | Model của nhóm, 2 lớp: `0 pothole`, `1 speed_bump` | TV3 train bằng `training/train_colab.ipynb`, chép vào đây |
| `sample/pothole_best.pt` | Model ổ gà mẫu | Model mẫu từ [kdbell4/hazard-detector](https://github.com/kdbell4/hazard-detector) |
| `sample/speedbump_best.pt` | Model gờ giảm tốc mẫu | Model mẫu từ [kdbell4/hazard-detector](https://github.com/kdbell4/hazard-detector) |

Server ưu tiên `road_best.pt` (đổi tên/đường dẫn bằng `MODEL_PATH` trong `.env`).
Khi chưa có file đó, server tự dùng 2 model mẫu để cả nhóm chạy thử được ngay từ đợt 1.
Model mẫu chỉ để thử; báo cáo và demo dùng model nhóm tự train.
