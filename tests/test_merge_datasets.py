"""Kiểm tra tools/merge_datasets.py trên 2 dataset giả (ảnh 1x1 px, không cần mạng)."""

import importlib.util
import struct
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("merge_datasets", ROOT / "tools" / "merge_datasets.py")
merge_datasets = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(merge_datasets)


def _png_1x1() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\x80"))
            + chunk(b"IEND", b""))


def _make_dataset(root: Path, data_yaml: str, images: dict) -> Path:
    """images: {(split, tên ảnh): nội dung file nhãn}."""
    (root / "data.yaml").parent.mkdir(parents=True, exist_ok=True)
    (root / "data.yaml").write_text(data_yaml, encoding="utf-8")
    for (split, stem), label in images.items():
        (root / split / "images").mkdir(parents=True, exist_ok=True)
        (root / split / "labels").mkdir(parents=True, exist_ok=True)
        (root / split / "images" / f"{stem}.png").write_bytes(_png_1x1())
        (root / split / "labels" / f"{stem}.txt").write_text(label)
    return root


@pytest.fixture(scope="module")
def merged(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("ds")
    # Dataset 1: names dạng list một dòng
    ds1 = _make_dataset(tmp / "ds1", "nc: 3\nnames: ['Pothole', 'Speed Bump', 'Normal Road']\n", {
        ("train", "pothole"): "0 0.5 0.5 0.2 0.2\n",
        ("train", "normal"): "2 0.5 0.5 0.9 0.9\n",
        ("valid", "bump"): "1 0.4 0.6 0.3 0.1\n",
        # Nhãn polygon (segment): 4 đỉnh của hình chữ nhật x 0.2–0.6, y 0.3–0.5
        ("test", "polygon"): "0 0.2 0.3 0.6 0.3 0.6 0.5 0.2 0.5\n",
    })
    # Dataset 2: names dạng dict nhiều dòng
    ds2 = _make_dataset(tmp / "ds2", "nc: 2\nnames:\n  0: Road Crack\n  1: pothole\n", {
        ("train", "crack"): "0 0.5 0.5 0.3 0.3\n",
        ("train", "pothole2"): "1 0.3 0.3 0.1 0.1\n",
    })
    out = tmp / "out"
    merge_datasets.merge([ds1, ds2], out)
    return out


def _label(out: Path, split: str, stem: str) -> str:
    return (out / split / "labels" / f"{stem}.txt").read_text()


def test_doi_nhan_ve_hai_lop(merged):
    assert _label(merged, "train", "s0_pothole") == "0 0.5 0.5 0.2 0.2\n"
    assert _label(merged, "valid", "s0_bump") == "1 0.4 0.6 0.3 0.1\n"
    assert _label(merged, "train", "s1_pothole2") == "0 0.3 0.3 0.1 0.1\n"
    assert (merged / "train" / "images" / "s0_pothole.png").exists()


def test_anh_chi_co_normal_road_thanh_nhan_rong(merged):
    assert (merged / "train" / "images" / "s0_normal.png").exists()
    assert _label(merged, "train", "s0_normal") == ""


def test_data_yaml_hai_lop_va_khong_co_path(merged):
    text = (merged / "data.yaml").read_text(encoding="utf-8")
    assert "nc: 2" in text
    assert "names: [pothole, speed_bump]" in text
    assert not any(line.startswith("path:") for line in text.splitlines())


@pytest.mark.xfail(strict=True, reason="merge_datasets.py chưa đổi polygon thành khung bao: "
                                       "lấy 4 số đầu của polygon làm cx cy w h")
def test_polygon_doi_thanh_khung_bao(merged):
    cx, cy, w, h = map(float, _label(merged, "test", "s0_polygon").split()[1:])
    assert (cx, cy, w, h) == pytest.approx((0.4, 0.4, 0.4, 0.2))


@pytest.mark.xfail(strict=True, reason="'Road Crack' chứa chữ 'road' nên map_class() coi là "
                                       "mặt đường bình thường thay vì bỏ ảnh")
def test_anh_road_crack_bi_bo(merged):
    assert not (merged / "train" / "images" / "s1_crack.png").exists()
