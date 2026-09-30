# KeyDive recon (search-layer + pavedpath-code)

Date: 2026-09-30  
Slice: recon-keydive  
Upstream: https://github.com/hyugogirubato/KeyDive  
Scope: own-device L3 CDM research extract + authorized personal backup pipeline. No pirate VOD playbook.

Search path: user-level `search-layer` (`search.py --mode deep --intent exploratory`) + client-native web search + `pavedpath-code` via `D:\reverse_ENV\tools\gh\bin\gh.exe`. Subagents skipped (single repo, `gh` available). Exa lane timed out on `127.0.0.1:7897`; Tavily + Grok citations still landed. Two native web queries on DRM-extract wording were refused; facts below are from `gh` raw files, PyPI JSON, issues, and README.

Temp source copies (not for reuse as runtime): `D:\reverse_ENV\temp\agent-runs\keydive-recon\`

---

## 0. Project basics

| Field | Value | Source |
|-------|--------|--------|
| Repo | hyugogirubato/KeyDive | https://github.com/hyugogirubato/KeyDive |
| Homepage | https://pypi.org/project/keydive/ | `gh repo view` |
| Stars / forks | 1086 / 163 | `gh repo view` 2026-09-30 |
| Language | Python | |
| License | MIT | `pyproject.toml` `license = "MIT"`; LICENSE file; PyPI `info.license=MIT` |
| Latest stable | **3.0.6** (tag + PyPI, not yanked) | GitHub release 2026-04-28T19:16:43Z; PyPI JSON version 3.0.6 |
| Default branch | main, last push 2026-06-14 | 3 commits **ahead** of v3.0.6 |
| Archived | no | |
| Python | `>=3.8,<4.0` | pyproject + PyPI |
| Host Frida (pip dep) | `frida >= 17.1.3` | pyproject |
| Dev extra | `frida-tools >= 14.1.1` | poetry group.dev |
| Optional extra | `offline` → Flask | `pip install keydive[offline]` |

Release assets:  
https://github.com/hyugogirubato/KeyDive/releases/tag/v3.0.6  
- `keydive-3.0.6-py3-none-any.whl`  
- `keydive-3.0.6.tar.gz`

main vs v3.0.6 (`gh api compare/v3.0.6...main`): ahead_by=3  
commits: `fix frida read api ref`, `warn possible crash loop on specific older device`, `add new private func`  
files: `keydive/drm/__init__.py`, `keydive/keydive.js`

---

## 1. Recommended install: pip vs git clone

Official README install is **PyPI**, not git:

```
pip install keydive
```

https://github.com/hyugogirubato/KeyDive/blob/main/README.md  
https://pypi.org/project/keydive/

Pin for reverse_ENV:

```
pip install keydive==3.0.6
```

When to git clone instead:

- Need bundled `docs/server/kaltura.apk` (not inside the pip wheel; poetry `include` only CHANGELOG/README/LICENSE for sdist).
- Need the 3 unreleased main commits (Frida 17 Memory-read shim, extra OEM func).
- Need to patch ADB path / vendor APK dict / log dir without wrapping CLI.

Localization recommendation: **do not install into `D:\reverse_ENV\.venv`**. Use a project venv, e.g. `D:\reverse_ENV\workspace\widevine-l3-download\.venv`. Pin `keydive==3.0.6` unless the Frida 17 JS fix on main is required.

Offline extra (local DRM Flask demo in `docs/server/`): `pip install "keydive[offline]"` — not required for CDM extract.

---

## 2. CLI map (v3.0.6 `keydive/__main__.py`)

Entry: `keydive = "keydive.__main__:main"`

| Flag | Meaning |
|------|---------|
| *(no `-a`)* | **Pure hook / watchdog only.** `core.launch()` is skipped. Hooks Widevine processes already on device. User must trigger DRM playback themselves. |
| `-a player` | Install (if missing) + launch Kaltura Device Info |
| `-a web` | Open Bitmovin DRM demo `https://bitmovin.com/demos/drm` in default browser |
| `-w` / `--wvd` | Also export pywidevine-compatible `.wvd` |
| `-k` / `--keybox` | Also export keybox + OEM cert if present |
| `-o` / `--output` | Extract dir, **default `./device`** |
| `-s` / `--serial` | ADB serial. Else `frida.get_usb_device()` (first USB) |
| `-l` / `--log` | Directory for `keydive_YYYY-MM-DD_HH-MM-SS.log` |
| `-d` / `--delay` | Watcher poll seconds, default 1.0 |
| `-v` | Debug console |
| `-V` | Print `KeyDive 3.0.6` and exit |
| `--no-detect` | Disable OEM private-key auto-detect |
| `--no-disabler` | Skip in-script liboemcrypto memory patch |
| `--no-stop` | Keep capturing after `client_id.bin` |
| `--unencrypt` | Force plaintext client ID in challenge (can crash some CDMs) |
| `--symbols` | Ghidra XML for OEM API 18+ / SDK > 33 if Frida < 16.6 |
| `--challenge` / `--rsa-key` / `--aes-key` | Offline / MITM / keybox decrypt inputs |

Canonical README example: `keydive -kw -a player`  
Pure hook example: `keydive -kw -s SERIAL -o OUTPUT -l LOG_DIR`

Device select: `-s` is the only selector. `Remote.__init__` requires `adb` on **PATH** (`shutil.which('adb')`), then `adb start-server`, then Frida USB/serial.

Logs: `configure_logging` writes `keydive_%Y-%m-%d_%H-%M-%S.log` under `-l` dir. Console still uses coloredlogs. Localization: always pass `-l` to a project log dir so stdout is not the only record.

---

## 3. `-a player` Kaltura APK download / skip

Hardcoded in `keydive/adb/__init__.py` `DRM_PLAYER`:

```
name:    Kaltura Device Info
package: com.kaltura.kalturadeviceinfo
url:     https://github.com/kaltura/kaltura-device-info-android/releases/download/t3/kaltura-device-info-release.apk
path:    <package_root>/docs/server/kaltura.apk
```

Upstream APK tag `t3` (2019-04-15):  
https://github.com/kaltura/kaltura-device-info-android/releases/download/t3/kaltura-device-info-release.apk  
Repo: https://github.com/kaltura/kaltura-device-info-android

Bundled copy (git tree, ~3.0 MB):  
https://github.com/hyugogirubato/KeyDive/blob/main/docs/server/kaltura.apk  
raw: https://raw.githubusercontent.com/hyugogirubato/KeyDive/main/docs/server/kaltura.apk

Install flow (`Core.launch` + `Remote.install_application`):

1. `pm` user-app list. If `com.kaltura.kalturadeviceinfo` is already installed → **skip download/install**.
2. Else try **local `path` if `path.is_file()`** (`adb install <path>`).
3. Else **GET `url`** → write `tmp.apk` in CWD → `adb install tmp.apk` → unlink.
4. If process already running → **do not relaunch** (CHANGELOG 3.0.0; issue 73 log).
5. Else `am start` MAIN activity.

**Official skip-download path (no extra CLI flag):**

- Pre-install APK, then still use `-a player` (install skipped, launch if not running).
- Maintainer on issue 49: download https://github.com/hyugogirubato/KeyDive/blob/main/docs/server/kaltura.apk and `adb install kaltura.apk`.
- Omit `-a` entirely (pure hook) if any DRM app is already playing.

**No official `--apk` / `--skip-download` / local-path CLI.** To use a vendor APK you either pre-install it and skip `-a`, or patch `DRM_PLAYER` (git checkout). pip install cannot use the bundled path because `docs/server/kaltura.apk` is not shipped in the wheel; pip users always hit the GitHub URL unless the package is already on device.

Issue 49: `Installation failed for local path: tmp.apk` — download-to-CWD then `adb install` failed; workaround was manual `adb install docs/server/kaltura.apk`. Kaltura also shows “built for an older Android” on API 34+; maintainer said the warning is not currently functional.

There is **no** supported “change URL to a local path via flag”. Local path is only the hardcoded relative file.

---

## 4. Android 15 / API 35 / Frida 16.6+ / 17.x

README (current main):

> For dynamic key extraction on devices with Android SDK > 33 (OEM API 18+), a minimum `frida-server 16.6.0` is required. Otherwise, pre-extracted functions from Ghidra are necessary.

There is **no** README sentence that names “Android 15” or “API 35” as a first-class supported OS. Evidence is by SDK tables, changelog, and field reports.

| Claim | Evidence |
|-------|----------|
| SDK 35 CDM details added | CHANGELOG 2.1.1 |
| SDK 35 x86_64 private-key function | CHANGELOG 2.0.3 |
| Android 16 preview SDK 36 (“Backlava”) | CHANGELOG 2.2.0 |
| Vendor table last **explicit** `min_sdk` | 34 → `android.hardware.drm-service.widevine` / OEM 18 / `android.hardware.drm-service.widevine` |
| SDK 35 matching | `vendor.min_sdk <= self.sdk` then sort descending; API 35 therefore uses the SDK 34 vendor row |
| Android 17 / SDK 37 | TODO comment in `keydive/drm/__init__.py` |
| Dynamic symbols if Frida ≥ 16.6.0 | `Server.features = major>16 or (16 and minor>=6)` |
| `--symbols` deprecated on Frida 16.6+ | `core.py` warning |
| `--symbols` still required if Frida < 16.6 **and** OEM API > 17 | same |
| Host pip `frida>=17.1.3` | pyproject 3.0.6 |
| JS Frida 17 Memory API shims | `keydive.js` “Backward compatibility … since frida 17”, https://frida.re/news/2025/05/17/frida-17-0-0-released/ |
| Major mismatch host vs device | `ProtocolError` → `Frida python version is different from the server version.` CHANGELOG 3.0.3: stop when server not compatible with major version |
| Field: 3.0.6 on SDK 35 | issue 73 (Fairphone 4, ABI arm64-v8a). Failure was “Frida server is not running”, not “API 35 unsupported”. |
| Field: 3.0.6 + frida-server 17.19.0 | issue 75 (open). SDK 33 Xiaomi; attach error `agent connection closed unexpectedly`. |

Implication for reverse_ENV: host Python `frida` and device `frida-server` must share **major** version. With `keydive==3.0.6` that means **Frida 17.x on both**. README’s 16.6.0 floor is the *minimum for OEM 18+ dynamic extract*, not the version KeyDive 3.0.6 actually pins.

---

## 5. pywidevine handoff

CHANGELOG 3.0.0: **removed `pywidevine` as a runtime dependency.** KeyDive now serializes WVD v2 itself (`keydive/drm/device.py`, modeled on pywidevine Device, no VMP).

Always written (when both blobs captured):

- `client_id.bin` — protobuf `ClientIdentification.SerializeToString()`
- `private_key.pem` — RSA TraditionalOpenSSL PEM, no encryption

If `-w`:

- `{company}_{model}_{cdmver}_{crc32}_{system_id}_l{level}.wvd`
- construct: magic `WVD`, version 2, type ANDROID, security_level, DER private key, client_id blob
- comment in `cdm.py`: https://github.com/devine-dl/pywidevine/blob/master/pywidevine/main.py#L211

Tree under `-o` (default `./device`): `{company}/{model}/{system_id}/{modulus10}/…` (sanitized via unidecode/pathvalidate).

Downstream without KeyDive’s `-w`:

```
pywidevine create-device -k private_key.pem -c client_id.bin -t ANDROID -l 3
```

Issue 69 (closed): KeyDive `-w` can stamp `application_name=com.opera.browser` into the blob identity some license servers reject. Workaround is the pywidevine CLI above, which keeps the original package name from `client_id.bin`. Localization should treat **raw `client_id.bin` + `private_key.pem` as canonical**, and `.wvd` as optional; if a site adapter is strict, rebuild WVD with pywidevine.

---

## 6. reverse_ENV localization notes

Do:

- Dedicated venv: `D:\reverse_ENV\workspace\widevine-l3-download\.venv` (or `storage/` sibling). **Do not** `pip install keydive` into `D:\reverse_ENV\.venv`.
- Put `D:\reverse_ENV\tools\adb` on PATH for that venv session, or wrap so `shutil.which('adb')` resolves `D:\reverse_ENV\tools\adb\adb.exe`. KeyDive always calls bare `adb`; it does not accept an adb path flag.
- Pre-stage vendor or Kaltura APK with that adb; then either `-a player` (skip download) or omit `-a` (pure hook).
- Force file logs: `-l D:\reverse_ENV\workspace\widevine-l3-download\logs` (creates `keydive_*.log`).
- Pin `keydive==3.0.6` unless pulling main for the Frida 17 read-API fix.
- Keep ADB serial via `-s`; never assume single USB device.
- Treat outputs as restricted device credentials: `client_id.bin` / `private_key.pem` / `.wvd` stay in project evidence dirs, not git.

Vendor APK: no upstream flag. Options: (a) pre-install + omit `-a`; (b) fork `DRM_PLAYER` in a local checkout; (c) git clone and replace `docs/server/kaltura.apk` so pip-less path hits the local file.

Risks:

- ADB must be on PATH; Windows store/platform-tools collision possible.
- `-a player` writes `tmp.apk` into **CWD** on URL fallback (issue 49).
- Frida 17 host vs 16.x device will abort.
- API 35 uses SDK 34 vendor row; untested as a named Android 15 matrix by upstream.
- Magisk / SELinux / L1 leftover: in-script disabler exists; Magisk module is deprecated. Issue 75 still fails attach on some Magisk devices.

---

## 7. Out of scope (explicit)

Not delivering: pirate VOD site recipes, CDM redistribution, desktop CDM dump, unauthorized content decrypt. Workspace `out_of_scope` already lists those.

---

## Citations (URLs + versions)

- https://github.com/hyugogirubato/KeyDive
- https://github.com/hyugogirubato/KeyDive/blob/main/README.md
- https://github.com/hyugogirubato/KeyDive/blob/main/CHANGELOG.md
- https://github.com/hyugogirubato/KeyDive/blob/main/pyproject.toml (version 3.0.6, MIT, frida>=17.1.3)
- https://github.com/hyugogirubato/KeyDive/blob/main/LICENSE
- https://github.com/hyugogirubato/KeyDive/releases/tag/v3.0.6 (2026-04-28)
- https://pypi.org/project/keydive/ (3.0.6, MIT, yanked=false)
- https://github.com/hyugogirubato/KeyDive/blob/main/keydive/__main__.py
- https://github.com/hyugogirubato/KeyDive/blob/main/keydive/adb/__init__.py (`DRM_PLAYER`)
- https://github.com/hyugogirubato/KeyDive/blob/main/keydive/adb/remote.py (`install_application`, PATH `adb`)
- https://github.com/hyugogirubato/KeyDive/blob/main/keydive/core.py (`launch`, `watchdog`, Frida 16.6 features)
- https://github.com/hyugogirubato/KeyDive/blob/main/keydive/drm/cdm.py (`export`)
- https://github.com/hyugogirubato/KeyDive/blob/main/keydive/drm/device.py (WVD v2)
- https://github.com/hyugogirubato/KeyDive/blob/main/keydive/drm/__init__.py (`CDM_VENDOR_API`)
- https://github.com/hyugogirubato/KeyDive/blob/main/keydive/keydive.js (Frida 17 shims, dated 2026-06-14)
- https://github.com/hyugogirubato/KeyDive/blob/main/docs/server/kaltura.apk
- https://github.com/kaltura/kaltura-device-info-android/releases/download/t3/kaltura-device-info-release.apk
- https://github.com/hyugogirubato/KeyDive/issues/49 (manual APK install)
- https://github.com/hyugogirubato/KeyDive/issues/69 (WVD application_name vs pywidevine CLI)
- https://github.com/hyugogirubato/KeyDive/issues/73 (SDK 35 + 3.0.6)
- https://github.com/hyugogirubato/KeyDive/issues/75 (open, Frida 17.19.0 attach)
- https://github.com/devine-dl/pywidevine
- https://frida.re/news/2025/05/17/frida-17-0-0-released/

Search-layer log: `C:\Users\mengma\.grok\sessions\D%3A%5Creverse_ENV\01a0f0c2-2ff6-7ae2-9aac-cfc74792abf6\terminal\call-ad963bb1-b015-4c1e-a6e3-e71a45c3ff9f-15.log`
