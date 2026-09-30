#!/usr/bin/env python3
"""Generic Widevine L3 pipeline for reverse_ENV.

Stages: CDM extract (KeyDive) -> PSSH select -> license replay
(pywidevine) -> download -> mp4decrypt -> ffmpeg mux.

Site-specific values come from adapter JSON. Do not install packages
into D:\\reverse_ENV\\.venv.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

WIDEVINE_SYSID = bytes.fromhex("edef8ba979d64acea3c827dcd51d21ed")
PLAYREADY_SYSID = bytes.fromhex("9a04f07998404286ab92e65be0885f95")
ZERO_KID = "00000000000000000000000000000000"

def _discover_roots() -> tuple[Path, Path]:
    here = Path(__file__).resolve().parent
    if here.name == "widevine-l3-download":
        return here.parents[1], here
    if here.parent.name == "tools" and here.name == "widevine-l3":
        repo = here.parents[1]
        return repo, repo / "workspace" / "widevine-l3-download"
    raise RuntimeError(f"unexpected widevine_l3.py location: {here}")


REPO_ROOT, PROJECT_DIR = _discover_roots()
TOOL_ROOT = Path(__file__).resolve().parent
LOCK_PATH = PROJECT_DIR / "runtime-lock.v1.json"
ADAPTERS_DIR = PROJECT_DIR / "adapters"
CDM_POINTER_PATH = PROJECT_DIR / "runtime" / "cdm-current.json"
CDM_STORE_DIR = REPO_ROOT / "storage" / "cdm-devices"
ARCHIVE_ROOT = (
    REPO_ROOT / "storage" / "workspace-archive" / "2026-09-28" / "ktv-smart-jp-download"
)
WVD_MAGIC = b"WVD"
KALTURA_PACKAGE = "com.kaltura.kalturadeviceinfo"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) "
    "Gecko/20100101 Firefox/151.0"
)


def load_lock() -> dict[str, Any]:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_python() -> Path:
    return PROJECT_DIR / ".venv-extract" / "Scripts" / "python.exe"


def replay_python() -> Path:
    return PROJECT_DIR / ".venv" / "Scripts" / "python.exe"


def isolated_python() -> Path:
    return replay_python()


def isolated_keydive() -> Path:
    return PROJECT_DIR / ".venv-extract" / "Scripts" / "keydive.exe"


def adb_exe() -> Path:
    return REPO_ROOT / "tools" / "adb" / "adb.exe"


def mp4decrypt_target() -> Path:
    return REPO_ROOT / "tools" / "bento4" / "bin" / "mp4decrypt.exe"


def mp4decrypt_exe() -> Path:
    local = mp4decrypt_target()
    if local.is_file():
        return local
    return (
        ARCHIVE_ROOT
        / "tools"
        / "bento4"
        / "Bento4-SDK-1-6-0-641.x86_64-microsoft-win32"
        / "bin"
        / "mp4decrypt.exe"
    )


def ffmpeg_exe() -> Path:
    local = REPO_ROOT / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
    if local.is_file():
        return local
    fallback = (
        ARCHIVE_ROOT
        / "tools"
        / "ffmpeg-tmp"
        / "ffmpeg-master-latest-win64-gpl"
        / "bin"
        / "ffmpeg.exe"
    )
    return fallback


def kaltura_apk() -> Path:
    local = PROJECT_DIR / "assets" / "kaltura-device-info-release.apk"
    if local.is_file():
        return local
    return ARCHIVE_ROOT / "runtime" / "cdm" / "kaltura-device-info-release.apk"


def keydive_vendor_apk() -> Path:
    return (
        PROJECT_DIR
        / ".venv-extract"
        / "Lib"
        / "site-packages"
        / "keydive"
        / "docs"
        / "server"
        / "kaltura.apk"
    )


def env_with_adb(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    adb_dir = str(adb_exe().parent)
    env["PATH"] = adb_dir + os.pathsep + env.get("PATH", "")
    env["ADB"] = str(adb_exe())
    return env


def die(msg: str, code: int = 1) -> int:
    print(msg, file=sys.stderr)
    return code


def local_tag(tag: str) -> str:
    return tag.split("}", 1)[-1]


def pssh_system_name(raw: bytes) -> str:
    if len(raw) < 28:
        return "truncated"
    sysid = raw[12:28]
    if sysid == WIDEVINE_SYSID:
        return "widevine"
    if sysid == PLAYREADY_SYSID:
        return "playready"
    return "other:" + sysid.hex()


def parse_mpd(path: Path) -> dict[str, Any]:
    tree = ET.parse(path)
    root = tree.getroot()
    protections: list[dict[str, Any]] = []
    representations: list[dict[str, Any]] = []

    for el in root.iter():
        name = local_tag(el.tag)
        if name == "ContentProtection":
            scheme = (el.get("schemeIdUri") or "").lower()
            default_kid = None
            for key, value in el.attrib.items():
                if local_tag(key) == "default_KID":
                    default_kid = value
            pssh_b64 = None
            for child in el:
                if local_tag(child.tag) == "pssh" and child.text:
                    pssh_b64 = "".join(child.text.split())
            system = "other"
            if "edef8ba9" in scheme:
                system = "widevine"
            elif "9a04f079" in scheme:
                system = "playready"
            elif pssh_b64:
                try:
                    system = pssh_system_name(base64.b64decode(pssh_b64))
                except Exception:
                    system = "invalid-pssh"
            protections.append(
                {
                    "system": system,
                    "schemeIdUri": el.get("schemeIdUri"),
                    "default_KID": default_kid,
                    "pssh": pssh_b64,
                }
            )
        elif name == "Representation":
            base_url = None
            for child in el:
                if local_tag(child.tag) == "BaseURL" and child.text:
                    base_url = child.text.strip()
            representations.append(
                {
                    "id": el.get("id"),
                    "height": _as_int(el.get("height")),
                    "bandwidth": _as_int(el.get("bandwidth")),
                    "codecs": el.get("codecs"),
                    "mimeType": el.get("mimeType"),
                    "baseUrl": base_url,
                }
            )

    widevine = [p for p in protections if p["system"] == "widevine" and p.get("pssh")]
    return {
        "mpd": str(path),
        "protections": protections,
        "representations": representations,
        "widevinePssh": widevine[0]["pssh"] if widevine else None,
        "widevineDefaultKid": widevine[0].get("default_KID") if widevine else None,
    }


def _as_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def select_widevine_pssh(mpd: dict[str, Any]) -> str:
    pssh = mpd.get("widevinePssh")
    if not pssh:
        raise ValueError("no Widevine PSSH (system id edef8ba9) in manifest")
    return pssh


def load_adapter(name_or_path: str) -> dict[str, Any]:
    candidate = Path(name_or_path)
    if not candidate.is_file():
        candidate = ADAPTERS_DIR / name_or_path
        if candidate.suffix == "":
            candidate = candidate.with_suffix(".json")
    if not candidate.is_file():
        raise FileNotFoundError(f"adapter not found: {name_or_path}")
    data = json.loads(candidate.read_text(encoding="utf-8"))
    data["_path"] = str(candidate)
    return data


def resolve_license_url(args: argparse.Namespace) -> str:
    if args.url:
        url = args.url
    else:
        adapter = load_adapter(args.adapter)
        template = adapter.get("license_url")
        if not template:
            raise ValueError("adapter missing license_url")
        if "{ticket}" in template:
            if not args.ticket:
                raise ValueError("adapter license_url needs --ticket")
            url = template.format(ticket=args.ticket)
        else:
            url = template
    return url


def resolve_headers(args: argparse.Namespace) -> tuple[dict[str, str], str | None]:
    referer = args.referer
    ua = args.ua
    proxy = args.proxy
    if args.adapter:
        adapter = load_adapter(args.adapter)
        referer = referer or adapter.get("referer")
        ua = ua or adapter.get("user_agent")
        proxy = proxy or adapter.get("proxy")
    headers = {
        "User-Agent": ua or DEFAULT_UA,
        "Content-Type": "application/octet-stream",
    }
    if referer:
        headers["Referer"] = referer
    return headers, proxy


def inspect_wvd(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, f"missing {path}"
    with path.open("rb") as fh:
        magic = fh.read(3)
    if magic != WVD_MAGIC:
        return False, f"{path.name} missing WVD magic"
    return True, f"{path.name} bytes={path.stat().st_size}"


def load_cdm_pointer(path: Path | None = None) -> dict[str, Any] | None:
    pointer = path or CDM_POINTER_PATH
    if not pointer.is_file():
        return None
    data = json.loads(pointer.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"cdm pointer is not an object: {pointer}")
    return data


def resolve_wvd(
    explicit: str | None = None,
    env: dict[str, str] | None = None,
    pointer_path: Path | None = None,
) -> Path:
    if explicit:
        path = Path(explicit)
    else:
        environ = os.environ if env is None else env
        env_path = environ.get("WIDEVINE_WVD")
        if env_path:
            path = Path(env_path)
        else:
            pointer = load_cdm_pointer(pointer_path)
            if not pointer or not pointer.get("wvd"):
                raise FileNotFoundError(
                    "need --wvd, env WIDEVINE_WVD, or "
                    "workspace/widevine-l3-download/runtime/cdm-current.json"
                )
            path = Path(str(pointer["wvd"]))
    if not path.is_file():
        raise FileNotFoundError(f"wvd not found: {path}")
    ok, detail = inspect_wvd(path)
    if not ok:
        raise ValueError(detail)
    return path


def write_cdm_pointer(
    wvd: Path,
    device_id: str,
    pointer_path: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    dest = pointer_path or CDM_POINTER_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema": "widevine-l3-cdm-pointer.v1",
        "deviceId": device_id,
        "type": "ANDROID",
        "securityLevel": 3,
        "wvd": str(wvd.resolve()),
    }
    if extra:
        payload.update(extra)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def install_cdm_from_dir(source: Path, device_id: str) -> dict[str, Path]:
    if not source.is_dir():
        raise FileNotFoundError(f"cdm source dir missing: {source}")
    wvds = sorted(source.glob("*.wvd"))
    if not wvds:
        raise FileNotFoundError(f"no .wvd in {source}")
    dest_dir = CDM_STORE_DIR / device_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, Path] = {}
    wvd_dest = dest_dir / wvds[0].name
    shutil.copy2(wvds[0], wvd_dest)
    copied["wvd"] = wvd_dest
    for name in ("client_id.bin", "private_key.pem"):
        src = source / name
        if src.is_file():
            target = dest_dir / name
            shutil.copy2(src, target)
            copied[name] = target
    ok, detail = inspect_wvd(wvd_dest)
    if not ok:
        raise ValueError(detail)
    extra = {
        "store": str(dest_dir.resolve()),
        "clientId": str(copied["client_id.bin"].resolve())
        if "client_id.bin" in copied
        else None,
        "privateKey": str(copied["private_key.pem"].resolve())
        if "private_key.pem" in copied
        else None,
    }
    write_cdm_pointer(wvd_dest, device_id, extra=extra)
    return copied


def cmd_pssh(args: argparse.Namespace) -> int:
    mpd = parse_mpd(Path(args.mpd))
    if args.json:
        print(json.dumps(mpd, ensure_ascii=False, indent=2))
        return 0
    pssh = mpd.get("widevinePssh")
    if not pssh:
        return die("no Widevine PSSH in manifest")
    print(pssh)
    if mpd.get("widevineDefaultKid"):
        print(f"default_KID={mpd['widevineDefaultKid']}", file=sys.stderr)
    return 0


def cmd_license(args: argparse.Namespace) -> int:
    try:
        from pywidevine.cdm import Cdm
        from pywidevine.device import Device
        from pywidevine.pssh import PSSH
        import requests
    except ImportError as exc:
        return die(
            f"missing isolated dependency {exc}. Run: widevine_l3.py bootstrap"
        )

    try:
        wvd = resolve_wvd(getattr(args, "wvd", None))
    except (OSError, ValueError) as exc:
        return die(str(exc))

    if args.mpd:
        pssh_b64 = select_widevine_pssh(parse_mpd(Path(args.mpd)))
    elif args.pssh:
        pssh_b64 = args.pssh.strip()
    else:
        return die("need --pssh or --mpd")

    try:
        url = resolve_license_url(args)
        headers, proxy = resolve_headers(args)
    except (OSError, ValueError) as exc:
        return die(str(exc))

    device = Device.load(wvd)
    cdm = Cdm.from_device(device)
    session = cdm.open()
    challenge = cdm.get_license_challenge(session, PSSH(pssh_b64))
    proxies = {"http": proxy, "https": proxy} if proxy else None
    resp = requests.post(
        url, data=challenge, headers=headers, proxies=proxies, timeout=args.timeout
    )
    print(f"license HTTP {resp.status_code} bytes={len(resp.content)}")
    if resp.status_code != 200:
        text = resp.text[:500]
        return die(text)

    cdm.parse_license(session, resp.content)
    keys = cdm.get_keys(session)
    content_keys: list[dict[str, str]] = []
    rows: list[Any]
    if isinstance(keys, dict):
        rows = [{"kid": k, "key": v, "type": "CONTENT"} for k, v in keys.items()]
    else:
        rows = keys
    for item in rows:
        kid = getattr(item, "kid", None)
        key = getattr(item, "key", None)
        ktype = str(getattr(item, "type", "CONTENT"))
        if isinstance(item, dict):
            kid, key, ktype = item.get("kid"), item.get("key"), item.get("type", "CONTENT")
        kid_hex = _key_hex(kid)
        key_hex = _key_hex(key)
        if kid_hex.replace("-", "") == ZERO_KID:
            continue
        line = f"{kid_hex}:{key_hex}"
        print(f"{ktype} {line}")
        if str(ktype).upper() in {"CONTENT", "CONTENT_KEY", "CONTENT"}:
            content_keys.append({"kid": kid_hex, "key": key_hex, "mp4decrypt": line})
    if args.out:
        Path(args.out).write_text(
            json.dumps({"url": url, "keys": content_keys}, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0 if content_keys else die("no content keys (check PSSH system id)")


def _key_hex(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.hex()
    text = str(value)
    if text.startswith("0x"):
        text = text[2:]
    return text.replace("-", "").lower()


def cmd_download(args: argparse.Namespace) -> int:
    try:
        import requests
    except ImportError as exc:
        return die(f"missing requests: {exc}")
    headers, proxy = resolve_headers(args)
    headers.pop("Content-Type", None)
    proxies = {"http": proxy, "https": proxy} if proxy else None
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(
        args.url, headers=headers, proxies=proxies, timeout=args.timeout, stream=True
    ) as resp:
        resp.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if chunk:
                    fh.write(chunk)
    print(json.dumps({"output": str(dest), "bytes": dest.stat().st_size}))
    return 0


def decrypt_file(input_path: Path, output_path: Path, keys: list[str]) -> int:
    exe = mp4decrypt_exe()
    if not exe.is_file():
        print(f"mp4decrypt missing: {exe}. Run bootstrap", file=sys.stderr)
        return 1
    if not keys:
        print("need at least one KID:KEY", file=sys.stderr)
        return 1
    cmd = [str(exe)]
    for key in keys:
        cmd.extend(["--key", key])
    cmd.extend([str(input_path), str(output_path)])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(cmd, check=False).returncode


def cmd_decrypt(args: argparse.Namespace) -> int:
    return decrypt_file(Path(args.input), Path(args.output), [args.key])


def cmd_mux(args: argparse.Namespace) -> int:
    exe = ffmpeg_exe()
    if not exe.is_file():
        return die(f"ffmpeg missing: {exe}. Run bootstrap")
    cmd = [str(exe), "-y", "-i", str(args.video)]
    if args.audio:
        cmd.extend(["-i", str(args.audio)])
    cmd.extend(["-c", "copy", "-movflags", "+faststart", str(args.output)])
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def cmd_extract(args: argparse.Namespace) -> int:
    keydive = isolated_keydive()
    if not keydive.is_file():
        return die(f"keydive missing: {keydive}. Run bootstrap")
    if not adb_exe().is_file():
        return die(f"adb missing: {adb_exe()}")

    vendor = keydive_vendor_apk()
    apk = kaltura_apk()
    if args.auto == "player" and not vendor.is_file():
        if apk.is_file():
            vendor.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(apk, vendor)
        else:
            return die(
                "Kaltura APK missing; refuse GitHub download. Run bootstrap "
                "or copy assets/kaltura-device-info-release.apk"
            )

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    log_dir = Path(args.log) if args.log else out / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(keydive),
        "-w",
        "-o",
        str(out),
        "-l",
        str(log_dir),
    ]
    if args.auto != "none":
        cmd.extend(["-a", args.auto])
    if args.serial:
        cmd.extend(["-s", args.serial])
    if args.verbose:
        cmd.append("-v")

    stdout_log = log_dir / "extract.stdout.log"
    print(json.dumps({"cmd": cmd, "log": str(stdout_log)}, ensure_ascii=False))
    with stdout_log.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(
            cmd, env=env_with_adb(), stdout=fh, stderr=subprocess.STDOUT, check=False
        )
    print(f"exit={proc.returncode} log={stdout_log}")
    return proc.returncode


def cmd_cdm(args: argparse.Namespace) -> int:
    try:
        if args.install_from:
            copied = install_cdm_from_dir(Path(args.install_from), args.device_id)
            wvd = copied["wvd"]
        elif args.wvd:
            wvd = Path(args.wvd)
            ok, detail = inspect_wvd(wvd)
            if not ok:
                return die(detail)
            extra: dict[str, Any] = {}
            if args.client_id:
                extra["clientId"] = str(Path(args.client_id).resolve())
            if args.private_key:
                extra["privateKey"] = str(Path(args.private_key).resolve())
            write_cdm_pointer(wvd, args.device_id, extra=extra)
        else:
            return die("cdm needs --install-from DIR or --wvd PATH")
    except (OSError, ValueError) as exc:
        return die(str(exc))
    pointer = load_cdm_pointer()
    print(
        json.dumps(
            {
                "pointer": str(CDM_POINTER_PATH),
                "deviceId": args.device_id,
                "wvd": str(wvd.resolve()),
                "store": (pointer or {}).get("store"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    out = Path(args.output)
    work = Path(args.work_dir) if args.work_dir else out.parent / (out.stem + "-work")
    work.mkdir(parents=True, exist_ok=True)
    keys_path = work / "keys.json"

    license_ns = argparse.Namespace(
        wvd=getattr(args, "wvd", None),
        mpd=args.mpd,
        pssh=args.pssh,
        url=args.url,
        adapter=args.adapter,
        ticket=args.ticket,
        referer=args.referer,
        ua=args.ua,
        proxy=args.proxy,
        timeout=args.timeout,
        out=str(keys_path),
    )
    rc = cmd_license(license_ns)
    if rc:
        return rc
    payload = json.loads(keys_path.read_text(encoding="utf-8"))
    key_lines = [item["mp4decrypt"] for item in payload.get("keys", [])]
    if not key_lines:
        return die("license returned no content keys")

    video_enc = work / "video.enc.mp4"
    video_dec = work / "video.dec.mp4"
    dl_video = argparse.Namespace(
        url=args.video_url,
        output=str(video_enc),
        adapter=args.adapter,
        referer=args.referer,
        ua=args.ua,
        proxy=args.proxy,
        timeout=max(args.timeout, 60),
    )
    rc = cmd_download(dl_video)
    if rc:
        return rc
    rc = decrypt_file(video_enc, video_dec, key_lines)
    if rc:
        return rc

    audio_dec: Path | None = None
    if args.audio_url:
        audio_enc = work / "audio.enc.mp4"
        audio_dec = work / "audio.dec.mp4"
        dl_audio = argparse.Namespace(
            url=args.audio_url,
            output=str(audio_enc),
            adapter=args.adapter,
            referer=args.referer,
            ua=args.ua,
            proxy=args.proxy,
            timeout=max(args.timeout, 60),
        )
        rc = cmd_download(dl_audio)
        if rc:
            return rc
        rc = decrypt_file(audio_enc, audio_dec, key_lines)
        if rc:
            return rc

    mux_ns = argparse.Namespace(
        video=str(video_dec),
        audio=str(audio_dec) if audio_dec else None,
        output=str(out),
    )
    rc = cmd_mux(mux_ns)
    if rc:
        return rc
    print(
        json.dumps(
            {
                "output": str(out.resolve()),
                "work": str(work.resolve()),
                "keys": str(keys_path.resolve()),
                "bytes": out.stat().st_size if out.is_file() else 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    lock = load_lock()
    provision = getattr(args, "provision", False)
    skip_wvd = getattr(args, "cmd", "") == "bootstrap"
    mode = "provision" if provision else ("bootstrap" if skip_wvd else "daily")
    report: dict[str, Any] = {"ok": True, "checks": [], "mode": mode}

    def check(name: str, ok: bool, detail: str) -> None:
        report["checks"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            report["ok"] = False

    extract_py = extract_python()
    replay_py = replay_python()
    check("extract-venv", extract_py.is_file(), str(extract_py))
    check("replay-venv", replay_py.is_file(), str(replay_py))

    check("mp4decrypt", mp4decrypt_exe().is_file(), str(mp4decrypt_exe()))
    ff = ffmpeg_exe()
    check("ffmpeg", ff.is_file(), str(ff))

    if not skip_wvd:
        try:
            wvd = resolve_wvd()
            ok, detail = inspect_wvd(wvd)
            check("wvd-present", ok, detail)
        except (OSError, ValueError) as exc:
            check("wvd-present", False, str(exc))

    extract_pins = {k: v for k, v in lock["python"]["extract"].items() if k != "venv"}
    replay_pins = {k: v for k, v in lock["python"]["replay"].items() if k != "venv"}
    if extract_py.is_file():
        versions = _pip_versions(extract_py)
        for pkg, want in extract_pins.items():
            check(f"extract:{pkg}", versions.get(pkg) == want, f"got={versions.get(pkg)} want={want}")
        check("extract-import-keydive", *_import_ok(extract_py, "import keydive"))
    if replay_py.is_file():
        versions = _pip_versions(replay_py)
        for pkg, want in replay_pins.items():
            check(f"replay:{pkg}", versions.get(pkg) == want, f"got={versions.get(pkg)} want={want}")
        check(
            "replay-import-pywidevine",
            *_import_ok(replay_py, "from pywidevine.cdm import Cdm; from pywidevine.pssh import PSSH"),
        )

    if mp4decrypt_exe().is_file():
        want = lock["assets"]["mp4decrypt"]["sha256"]
        got = sha256_file(mp4decrypt_exe())
        check("mp4decrypt-hash", got == want, got)

    if provision:
        check("adb", adb_exe().is_file(), str(adb_exe()))
        apk = kaltura_apk()
        if apk.is_file():
            digest = sha256_file(apk)
            expected = lock["assets"]["kalturaApk"]["sha256"]
            check("kaltura-apk-hash", digest == expected, f"{apk} sha256={digest}")
        else:
            check("kaltura-apk", False, "missing; bootstrap copies from archive")
        vendor = keydive_vendor_apk()
        check(
            "keydive-local-apk",
            vendor.is_file(),
            str(vendor) + (" (GitHub download skipped)" if vendor.is_file() else ""),
        )
        check("keydive-exe", isolated_keydive().is_file(), str(isolated_keydive()))

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


def _import_ok(python: Path, statement: str) -> tuple[bool, str]:
    proc = subprocess.run(
        [str(python), "-c", statement], capture_output=True, text=True, check=False
    )
    if proc.returncode == 0:
        return True, "ok"
    err = (proc.stderr or proc.stdout or "").strip().splitlines()
    return False, err[-1] if err else f"exit {proc.returncode}"


def _pip_versions(python: Path) -> dict[str, str]:
    proc = subprocess.run(
        [str(python), "-m", "pip", "show", "keydive", "pywidevine", "protobuf", "frida", "construct"],
        capture_output=True,
        text=True,
        check=False,
    )
    versions: dict[str, str] = {}
    name = None
    for line in proc.stdout.splitlines():
        if line.startswith("Name:"):
            name = line.split(":", 1)[1].strip().lower()
        elif line.startswith("Version:") and name:
            versions[name] = line.split(":", 1)[1].strip()
            name = None
    return versions


def _ensure_venv(python_exe: Path, packages: list[str], pins: dict[str, str], force: bool) -> None:
    python_exe.parent.mkdir(parents=True, exist_ok=True)
    if not python_exe.is_file():
        raise FileNotFoundError(str(python_exe))
    versions = _pip_versions(python_exe)
    if not force and all(versions.get(name) == want for name, want in pins.items()):
        print(f"pins already satisfied: {python_exe}")
        return
    cmd = [
        str(python_exe),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-cache-dir",
        *packages,
    ]
    print("pip:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def cmd_bootstrap(args: argparse.Namespace) -> int:
    lock = load_lock()
    base_py = Path(args.python) if args.python else Path(sys.executable)
    extract_dir = PROJECT_DIR / ".venv-extract"
    replay_dir = PROJECT_DIR / ".venv"
    if not extract_python().is_file():
        subprocess.run([str(base_py), "-m", "venv", str(extract_dir)], check=True)
    if not replay_python().is_file():
        subprocess.run([str(base_py), "-m", "venv", str(replay_dir)], check=True)

    extract_pins = {k: v for k, v in lock["python"]["extract"].items() if k != "venv"}
    replay_pins = {k: v for k, v in lock["python"]["replay"].items() if k != "venv"}
    _ensure_venv(
        extract_python(),
        ["keydive==3.0.6", "frida==17.15.3", "protobuf==5.29.6", "construct==2.10.70"],
        extract_pins,
        args.force,
    )
    _ensure_venv(
        replay_python(),
        ["pywidevine==1.9.0", "requests==2.32.5", "protobuf==6.33.6", "construct==2.8.8"],
        replay_pins,
        args.force,
    )

    assets = PROJECT_DIR / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    src_apk = ARCHIVE_ROOT / "runtime" / "cdm" / "kaltura-device-info-release.apk"
    dest_apk = assets / "kaltura-device-info-release.apk"
    if src_apk.is_file():
        shutil.copy2(src_apk, dest_apk)
        digest = sha256_file(dest_apk)
        want = lock["assets"]["kalturaApk"]["sha256"]
        if digest != want:
            return die(f"kaltura apk hash mismatch: {digest}")
        vendor = keydive_vendor_apk()
        vendor.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest_apk, vendor)
        print(f"vendor apk -> {vendor}")
    else:
        return die(f"archive apk missing: {src_apk}")

    src_mp4 = (
        ARCHIVE_ROOT
        / "tools"
        / "bento4"
        / "Bento4-SDK-1-6-0-641.x86_64-microsoft-win32"
        / "bin"
        / "mp4decrypt.exe"
    )
    dest_mp4 = mp4decrypt_target()
    dest_mp4.parent.mkdir(parents=True, exist_ok=True)
    if src_mp4.is_file():
        shutil.copy2(src_mp4, dest_mp4)
        digest = sha256_file(dest_mp4)
        want = lock["assets"]["mp4decrypt"]["sha256"]
        if digest != want:
            return die(f"mp4decrypt hash mismatch: {digest}")
        print(f"mp4decrypt -> {dest_mp4}")
    else:
        return die(f"archive mp4decrypt missing: {src_mp4}")

    dest_ff = REPO_ROOT / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
    dest_fp = REPO_ROOT / "tools" / "ffmpeg" / "bin" / "ffprobe.exe"
    src_ff_dir = (
        ARCHIVE_ROOT / "tools" / "ffmpeg-tmp" / "ffmpeg-master-latest-win64-gpl" / "bin"
    )
    if not dest_ff.is_file():
        dest_ff.parent.mkdir(parents=True, exist_ok=True)
        if (src_ff_dir / "ffmpeg.exe").is_file():
            shutil.copy2(src_ff_dir / "ffmpeg.exe", dest_ff)
            if (src_ff_dir / "ffprobe.exe").is_file():
                shutil.copy2(src_ff_dir / "ffprobe.exe", dest_fp)
            print(f"ffmpeg -> {dest_ff}")
        else:
            print(f"ffmpeg source missing: {src_ff_dir}", file=sys.stderr)

    return cmd_doctor(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local Widevine L3 pipeline (KeyDive + pywidevine + Bento4 + ffmpeg)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("doctor", help="daily PC checks (venv, decrypt tools, local .wvd)")
    p.add_argument(
        "--provision",
        action="store_true",
        help="also check adb/KeyDive/Kaltura (device extract path)",
    )
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("cdm", help="point daily license at a self-extracted .wvd")
    p.add_argument("--install-from", help="directory with .wvd + client_id.bin + private_key.pem")
    p.add_argument("--wvd", help="existing .wvd path (no copy)")
    p.add_argument("--client-id", help="optional client_id.bin path recorded in the pointer")
    p.add_argument("--private-key", help="optional private_key.pem path recorded in the pointer")
    p.add_argument("--device-id", required=True, help="store folder name, e.g. google-pixel6-33098")
    p.set_defaults(func=cmd_cdm)

    p = sub.add_parser("bootstrap", help="create isolated venv and vendor local binaries")
    p.add_argument(
        "--python",
        help="base interpreter for venv (default: current python)",
    )
    p.add_argument("--force", action="store_true", help="reinstall pip pins even if they match")
    p.set_defaults(func=cmd_bootstrap)

    p = sub.add_parser("extract", help="run KeyDive with local adb/apk; default -a web")
    p.add_argument("-o", "--output", required=True, help="CDM output directory")
    p.add_argument("-s", "--serial", help="adb serial")
    p.add_argument(
        "-a",
        "--auto",
        choices=["web", "player", "none"],
        default="web",
        help="web=Bitmovin demo (default); player=local Kaltura APK; none=pure hook",
    )
    p.add_argument("-l", "--log", help="KeyDive log directory")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("pssh", help="select Widevine PSSH from an MPD")
    p.add_argument("--mpd", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_pssh)

    p = sub.add_parser("license", help="replay license with a local .wvd")
    p.add_argument("--wvd", help="overrides WIDEVINE_WVD and runtime/cdm-current.json")
    p.add_argument("--pssh", help="Widevine PSSH base64")
    p.add_argument("--mpd", help="MPD path; Widevine PSSH is selected automatically")
    p.add_argument("--url", help="license server URL")
    p.add_argument("--adapter", help="adapter name or JSON path")
    p.add_argument("--ticket", help="fills {ticket} in adapter license_url")
    p.add_argument("--referer")
    p.add_argument("--ua")
    p.add_argument("--proxy")
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--out", help="write content keys JSON")
    p.set_defaults(func=cmd_license)

    p = sub.add_parser("download", help="HTTP download with Referer/UA/proxy")
    p.add_argument("--url", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--adapter")
    p.add_argument("--referer")
    p.add_argument("--ua")
    p.add_argument("--proxy")
    p.add_argument("--timeout", type=int, default=60)
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("decrypt", help="mp4decrypt --key KID:KEY")
    p.add_argument("--key", required=True, help="KID:KEY hex")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_decrypt)

    p = sub.add_parser("mux", help="ffmpeg -c copy")
    p.add_argument("--video", required=True)
    p.add_argument("--audio")
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_mux)

    p = sub.add_parser("run", help="PC daily: license + download + decrypt + mux")
    p.add_argument("--wvd", help="overrides WIDEVINE_WVD and runtime/cdm-current.json")
    p.add_argument("--mpd", help="MPD path; Widevine PSSH is selected automatically")
    p.add_argument("--pssh", help="Widevine PSSH base64")
    p.add_argument("--url", help="license server URL")
    p.add_argument("--adapter", help="adapter name or JSON path")
    p.add_argument("--ticket", help="fills {ticket} in adapter license_url")
    p.add_argument("--referer")
    p.add_argument("--ua")
    p.add_argument("--proxy")
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--video-url", required=True)
    p.add_argument("--audio-url")
    p.add_argument("--output", required=True, help="final muxed mp4")
    p.add_argument("--work-dir", help="encrypted/decrypted intermediates (default: <output>-work)")
    p.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
