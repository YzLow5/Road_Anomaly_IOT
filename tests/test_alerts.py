"""Kiểm tra AlertPolicy trong webapp/alerts.py: xác nhận nhiều khung + thời gian chờ."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from webapp.alerts import AlertPolicy  # noqa: E402


def test_chua_du_khung_lien_tiep_thi_chua_bao():
    policy = AlertPolicy(confirm_frames=3, cooldown=2.0)
    assert policy.update({"pothole"}, now=0.0) == []
    assert policy.update({"pothole"}, now=0.1) == []


def test_du_khung_lien_tiep_thi_bao():
    policy = AlertPolicy(confirm_frames=3, cooldown=2.0)
    policy.update({"pothole"}, now=0.0)
    policy.update({"pothole"}, now=0.1)
    assert policy.update({"pothole"}, now=0.2) == ["pothole"]


def test_mat_dau_thi_dem_lai_tu_dau():
    policy = AlertPolicy(confirm_frames=2, cooldown=2.0)
    policy.update({"speed_bump"}, now=0.0)
    policy.update(set(), now=0.1)
    assert policy.update({"speed_bump"}, now=0.2) == []
    assert policy.update({"speed_bump"}, now=0.3) == ["speed_bump"]


def test_trong_thoi_gian_cho_thi_khong_bao_lap():
    policy = AlertPolicy(confirm_frames=2, cooldown=2.0)
    policy.update({"pothole"}, now=0.0)
    assert policy.update({"pothole"}, now=0.1) == ["pothole"]
    assert policy.update({"pothole"}, now=1.0) == []
    assert policy.update({"pothole"}, now=2.0) == []
    assert policy.update({"pothole"}, now=2.2) == ["pothole"]


def test_cung_luc_hai_loai_thi_o_ga_truoc():
    policy = AlertPolicy(confirm_frames=1, cooldown=2.0)
    assert policy.update({"speed_bump", "pothole"}, now=0.0) == ["pothole", "speed_bump"]
