from __future__ import annotations

import json
import sys
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_ROOT))

from widevine_l3 import PROJECT_DIR, load_adapter  # noqa: E402


def test_project_root_is_independent_repo() -> None:
    assert PROJECT_DIR.name == "widevine-l3-download"
    assert (PROJECT_DIR / "adapters" / "ktv-smart-jp.json").is_file()
    assert (PROJECT_DIR / "widevine_l3.py").is_file()
    git_dir = PROJECT_DIR / ".git"
    assert git_dir.exists()
    env_root = PROJECT_DIR.parents[1]
    assert env_root.name == "reverse_ENV"
    env_git = env_root / ".git"
    assert git_dir.resolve() != env_git.resolve()
    ignore = (PROJECT_DIR / ".gitignore").read_text(encoding="utf-8")
    assert "*.wvd" in ignore
    assert "runtime/" in ignore
    assert ".venv-extract/" in ignore


def test_load_ktv_adapter() -> None:
    adapter = load_adapter("ktv-smart-jp")
    assert adapter["name"] == "ktv-smart-jp"
    assert "{ticket}" in adapter["license_url"]
    assert adapter["referer"].startswith("https://ktv-smart.jp")
    assert "wvks.videomarket.jp" in adapter["license_url"]


def test_load_adapter_path(tmp_path: Path) -> None:
    path = tmp_path / "site.json"
    path.write_text(
        json.dumps(
            {
                "name": "example",
                "referer": "https://example.test/",
                "license_url": "https://license.example.test/?token={ticket}",
            }
        ),
        encoding="utf-8",
    )
    adapter = load_adapter(str(path))
    assert adapter["name"] == "example"
