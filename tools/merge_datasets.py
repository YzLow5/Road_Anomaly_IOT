"""
Gộp nhiều dataset YOLOv8 (tải từ Roboflow) thành 1 dataset 2 lớp của nhóm:
    0 = pothole, 1 = speed_bump, ảnh không có khung = mặt đường bình thường.

    python tools/merge_datasets.py datasets/road_objects datasets/humps_bumps \\
        --out datasets/road_merged

Mỗi thư mục nguồn là bản export "YOLOv8" của Roboflow (có data.yaml và
train/ valid/ test/, mỗi phần có images/ và labels/).

Quy tắc đổi nhãn (theo tên lớp trong data.yaml, không phân biệt hoa thường):
    tên chứa "pothole"                          → 0 pothole
    tên chứa "bump", "hump", "breaker", "speed"  → 1 speed_bump
    tên chứa "normal", "plain", "road"          → bỏ khung (ảnh thành "bình thường")
    lớp khác (barricade, crack…)                → bỏ CẢ ẢNH, vì để lại sẽ dạy sai model
"""

import argparse
import re
import shutil
from collections import Counter
from pathlib import Path

OUR_NAMES = ["pothole", "speed_bump"]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def map_class(name: str):
    n = name.lower().replace("-", " ").replace("_", " ")
    if "pothole" in n:
        return 0
    if any(k in n for k in ("bump", "hump", "breaker", "speed")):
        return 1
    if any(k in n for k in ("normal", "plain", "road")):
        return "background"
    return None


def read_names(data_yaml: Path) -> list[str]:
    """Đọc 'names' trong data.yaml (dạng list một dòng, list nhiều dòng hoặc dict)."""
    text = data_yaml.read_text(encoding="utf-8")
    m = re.search(r"^names:\s*\[(.*?)\]", text, re.M | re.S)
    if m:
        return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]
    names, in_block = {}, False
    for line in text.splitlines():
        if re.match(r"^names:\s*$", line):
            in_block = True
            continue
        if in_block:
            item = re.match(r"^\s+-\s*(.+)$", line)
            keyed = re.match(r"^\s+(\d+):\s*(.+)$", line)
            if item:
                names[len(names)] = item.group(1).strip().strip("'\"")
            elif keyed:
                names[int(keyed.group(1))] = keyed.group(2).strip().strip("'\"")
            elif line.strip():
                break
    if not names:
        raise ValueError(f"Không đọc được 'names' trong {data_yaml}")
    return [names[i] for i in sorted(names)]


def merge(sources: list[Path], out: Path) -> None:
    stats = Counter()
    for split in ("train", "valid", "test"):
        (out / split / "images").mkdir(parents=True, exist_ok=True)
        (out / split / "labels").mkdir(parents=True, exist_ok=True)

    for src_idx, src in enumerate(sources):
        names = read_names(src / "data.yaml")
        mapping = {i: map_class(n) for i, n in enumerate(names)}
        print(f"[{src.name}] lớp gốc → lớp mới:")
        for i, n in enumerate(names):
            print(f"    {i} {n!r:24} → {mapping[i]}")

        for split in ("train", "valid", "test"):
            img_dir = src / split / "images"
            if not img_dir.exists():
                continue
            for img in sorted(img_dir.iterdir()):
                if img.suffix.lower() not in IMAGE_EXTS:
                    continue
                lbl = src / split / "labels" / (img.stem + ".txt")
                lines = lbl.read_text().splitlines() if lbl.exists() else []
                new_lines, drop = [], False
                for line in lines:
                    parts = line.split()
                    if len(parts) < 5:
                        continue
                    target = mapping.get(int(parts[0]))
                    if target is None:
                        drop = True
                        break
                    if target == "background":
                        continue
                    new_lines.append(" ".join([str(target)] + parts[1:5]))
                if drop:
                    stats["bỏ (lớp lạ)"] += 1
                    continue
                stem = f"s{src_idx}_{img.stem}"
                shutil.copy2(img, out / split / "images" / (stem + img.suffix.lower()))
                (out / split / "labels" / (stem + ".txt")).write_text(
                    "\n".join(new_lines) + ("\n" if new_lines else ""))
                kinds = {OUR_NAMES[int(l.split()[0])] for l in new_lines} or {"normal"}
                for k in kinds:
                    stats[f"{split}:{k}"] += 1
                stats[f"{split}:ảnh"] += 1

    (out / "data.yaml").write_text(
        "# Tạo bởi tools/merge_datasets.py\n"
        "train: train/images\nval: valid/images\ntest: test/images\n"
        "nc: 2\nnames: [pothole, speed_bump]\n", encoding="utf-8")

    print("\nKết quả (số ảnh có chứa mỗi loại):")
    for split in ("train", "valid", "test"):
        print(f"  {split:5}: {stats[f'{split}:ảnh']:5} ảnh — ổ gà {stats[f'{split}:pothole']}, "
              f"gờ {stats[f'{split}:speed_bump']}, bình thường {stats[f'{split}:normal']}")
    if stats["bỏ (lớp lạ)"]:
        print(f"  Bỏ {stats['bỏ (lớp lạ)']} ảnh có lớp không thuộc đề tài")
    print(f"\nData.yaml: {out / 'data.yaml'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gộp dataset Roboflow về 2 lớp pothole / speed_bump")
    ap.add_argument("sources", nargs="+", type=Path, help="các thư mục export YOLOv8")
    ap.add_argument("--out", type=Path, default=Path("datasets/road_merged"))
    a = ap.parse_args()
    merge(a.sources, a.out)
