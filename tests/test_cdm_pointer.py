from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_ROOT))

from widevine_l3 import (  # noqa: E402
    inspect_wvd,
    install_cdm_from_dir,
    resolve_wvd,
    write_cdm_pointer,
)


def test_inspect_wvd_magic(tmp_path: Path) -> None:
    good = tmp_path / "ok.wvd"
    good.write_bytes(b"WVD" + b"\x00" * 8)
    bad = tmp_path / "bad.wvd"
    bad.write_bytes(b"NOT")
    ok, detail = inspect_wvd(good)
    assert ok
    assert "ok.wvd" in detail
    failed, _ = inspect_wvd(bad)
    assert not failed
    missing, _ = inspect_wvd(tmp_path / "nope.wvd")
    assert not missing


def test_resolve_wvd_explicit(tmp_path: Path) -> None:
    wvd = tmp_path / "device.wvd"
    wvd.write_bytes(b"WVD\x00")
    assert resolve_wvd(str(wvd)) == wvd


def test_resolve_wvd_env(tmp_path: Path) -> None:
    wvd = tmp_path / "env.wvd"
    wvd.write_bytes(b"WVD\x00")
    assert resolve_wvd(env={"WIDEVINE_WVD": str(wvd)}) == wvd


def test_resolve_wvd_pointer(tmp_path: Path) -> None:
    wvd = tmp_path / "ptr.wvd"
    wvd.write_bytes(b"WVD\x00")
    pointer = tmp_path / "cdm-current.json"
    write_cdm_pointer(wvd, "fixture-device", pointer_path=pointer)
    data = json.loads(pointer.read_text(encoding="utf-8"))
    assert data["schema"] == "widevine-l3-cdm-pointer.v1"
    assert data["deviceId"] == "fixture-device"
    assert resolve_wvd(env={}, pointer_path=pointer) == wvd


def test_resolve_wvd_missing() -> None:
    with pytest.raises(FileNotFoundError, match="cdm-current.json"):
        resolve_wvd(env={}, pointer_path=Path("__missing_pointer__.json"))


def test_install_cdm_from_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import widevine_l3 as mod

    store = tmp_path / "store"
    monkeypatch.setattr(mod, "CDM_STORE_DIR", store)
    pointer = tmp_path / "runtime" / "cdm-current.json"
    monkeypatch.setattr(mod, "CDM_POINTER_PATH", pointer)

    source = tmp_path / "src"
    source.mkdir()
    (source / "sample_l3.wvd").write_bytes(b"WVD\x00fixture")
    (source / "client_id.bin").write_bytes(b"cid")
    (source / "private_key.pem").write_bytes(b"fixture-rsa-placeholder\n")

    copied = install_cdm_from_dir(source, "google-pixel6-33098")
    assert copied["wvd"].is_file()
    assert copied["wvd"].parent == store / "google-pixel6-33098"
    assert copied["client_id.bin"].is_file()
    payload = json.loads(pointer.read_text(encoding="utf-8"))
    assert payload["deviceId"] == "google-pixel6-33098"
    assert Path(payload["wvd"]).is_file()
    assert resolve_wvd(env={}, pointer_path=pointer) == copied["wvd"]
