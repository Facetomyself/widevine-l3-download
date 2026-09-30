from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest

TOOL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_ROOT))

from widevine_l3 import (  # noqa: E402
    PLAYREADY_SYSID,
    WIDEVINE_SYSID,
    parse_mpd,
    pssh_system_name,
    select_widevine_pssh,
)


def _box(system_id: bytes, payload: bytes = b"fixture") -> str:
    size = 12 + 16 + 4 + len(payload)
    raw = (
        size.to_bytes(4, "big")
        + b"pssh"
        + (0).to_bytes(4, "big")
        + system_id
        + len(payload).to_bytes(4, "big")
        + payload
    )
    return base64.b64encode(raw).decode("ascii")


def test_pssh_system_name_widevine_and_playready() -> None:
    wv = base64.b64decode(_box(WIDEVINE_SYSID))
    pr = base64.b64decode(_box(PLAYREADY_SYSID))
    assert pssh_system_name(wv) == "widevine"
    assert pssh_system_name(pr) == "playready"


def test_parse_mpd_selects_widevine(tmp_path: Path) -> None:
    wv = _box(WIDEVINE_SYSID, b"wv-payload")
    pr = _box(PLAYREADY_SYSID, b"pr-payload")
    mpd = tmp_path / "dual.mpd"
    mpd.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" xmlns:cenc="urn:mpeg:cenc:2013">
  <Period>
    <AdaptationSet>
      <ContentProtection schemeIdUri="urn:uuid:9a04f079-9840-4286-ab92-e65be0885f95">
        <cenc:pssh>{pr}</cenc:pssh>
      </ContentProtection>
      <ContentProtection schemeIdUri="urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed" cenc:default_KID="11111111-2222-3333-4444-555555555555">
        <cenc:pssh>{wv}</cenc:pssh>
      </ContentProtection>
      <Representation id="A-4" height="480" bandwidth="800000" codecs="avc1.4D401E">
        <BaseURL>video-A-4.mp4</BaseURL>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
""",
        encoding="utf-8",
    )
    parsed = parse_mpd(mpd)
    systems = [p["system"] for p in parsed["protections"]]
    assert "playready" in systems
    assert "widevine" in systems
    assert select_widevine_pssh(parsed) == wv
    assert parsed["widevineDefaultKid"] == "11111111-2222-3333-4444-555555555555"
    assert parsed["representations"][0]["baseUrl"] == "video-A-4.mp4"


def test_select_widevine_pssh_missing(tmp_path: Path) -> None:
    pr = _box(PLAYREADY_SYSID)
    mpd = tmp_path / "pr-only.mpd"
    mpd.write_text(
        f"""<?xml version="1.0"?>
<MPD xmlns:cenc="urn:mpeg:cenc:2013">
  <ContentProtection schemeIdUri="urn:uuid:9a04f079-9840-4286-ab92-e65be0885f95">
    <cenc:pssh>{pr}</cenc:pssh>
  </ContentProtection>
</MPD>
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no Widevine PSSH"):
        select_widevine_pssh(parse_mpd(mpd))
