# PC-only Widevine L3 device feasibility (no Pixel / no Android handset)

Date: 2026-09-30  
Slice: pc-only-cdm  
Scope: DRM research + authorized personal-backup pipeline design. No dumper/exploit/PoC. No pirate VOD playbook. No CDM redistribution.

Search path: user-level `search-layer` (`search.py --mode deep`) + client-native web search + `pavedpath-code` via `D:\reverse_ENV\tools\gh\bin\gh.exe`. Subagents skipped (`gh` available; single evidence file). Native web search refused two DRM-extract queries; facts below are from `gh` raw files/issues, PyPI-adjacent GitHub, Axinom/DoveRunner docs, and search-layer citations.

Local baselines (read-only):

- `D:\reverse_ENV\article\drm-content-acquisition\widevine-l3-video-download.md` — “不要试图提取桌面浏览器 CDM”; Firefox `widevinecdm.dll` 4.10.3050 has no ready dumper.
- `D:\reverse_ENV\workspace\widevine-l3-download\agent-notes\recon-keydive.md` — KeyDive 3.0.6 Android-only; WVD type ANDROID; no VMP.
- `workspace.json` `out_of_scope`: `desktop CDM dump`, `CDM redistribution`, `unauthorized content`. Not modified.

Temp copies: `D:\reverse_ENV\temp\agent-runs\pc-only-cdm\`

---

## Verdict (two questions)

| Question | Grade | Why |
|----------|-------|-----|
| Daily download/license/decrypt **entirely on PC** after a one-time device exists | **可行** | pywidevine already does challenge/license/keys on Windows. Existing ktv pipeline is this. |
| Get the **first** usable `.wvd` / `client_id+rsa` with **no Android at all** (no handset, no emulator, no WSA) from Chrome/Firefox `widevinecdm.dll` 4.10.3050+ | **目前不可行** | No maintained open-source extractor for that CDM generation. Shared Chrome `.wvd` is revoked + banned here. |
| Get a first device on Windows **without a physical Android**, using an Android emulator / WSA | **有条件可行** | KeyDive targets Android CDM via ADB+Frida+root. Maintainer says WSA works. LDPlayer x86_64 needs library-name mismatch handling and has higher revoke/fingerprint risk than ARM64 OEM. |

Recommended design name: **pixel-once-pc-daily**. Fallback: **emulator-once-pc-daily**. Reject: **chrome-dll**, **shared-wvd**.

---

## 1. Desktop Chrome / Firefox `widevinecdm.dll` 4.10.3050+ extractors

Question: is there a still-maintained open-source extractor for desktop Chrome/Firefox CDM, especially 4.10.3050 and newer?

**Answer: 仅旧版 / 已失效 for 4.10.3050+. No maintained extractor for current desktop CDM.**

CDM 4.10.3050.0 is a live 2025–2026 desktop Widevine:

- Firefox: https://bugzilla.mozilla.org/show_bug.cgi?id=2032184 (`[meta] Update Widevine to 4.10.3050.0`); `toolkit/content/gmp-sources/widevinecdm.json` (`"version": "4.10.3050.0"`).
- Chromium: https://chromium.googlesource.com/chromium/src/+/2c01bdef0be588b18eac823aaf806e620c1490cc (`Roll Widevine DEPS to pick up the 4.10.3050.0 CDM`).
- FreeBSD ports bump 2026-06-09: https://github.com/FreeBSD/freebsd-ports/commit/30f0c3c58d1e504cbb7744a10c8f19b9c8354746.

Extractor inventory (`gh repo view`, 2026-09-30):

| Repo | Stars | Last push | Archived | Status vs 4.10.3050 |
|------|-------|-----------|----------|---------------------|
| https://github.com/tomer8007/widevine-l3-decryptor | 1246 | 2022-12-29 | **yes** | Original Chrome extension. **仅旧版 / 已失效**. |
| https://github.com/Satsuoni/widevine-l3-guesser | 915 | 2021-08-06 | **yes** | Brute-force guesser for pre-obfuscation CDMs. **仅旧版**. |
| https://github.com/tbodt/widevine-l3-decryptor | 266 | 2020-11-13 | no | Stale fork of the 2020 extension. **已失效**. |
| https://github.com/widevineleak/Chrome-Widevine-Guesser-2025 | 109 | 2025-06-21 | no | Search snippet: works **Chrome ≤112 / CDM 4.10.2557.0** (replace WidevineCdm folder). **仅旧版**, not 4.10.3050. |
| https://github.com/luckypoker11/L1slashL3 | 1 | 2025-06-21 | no | Same family, 1 star. Not a 4.10.3050 extractor. |
| https://github.com/wvdumper/dumper | 698 | 2023-07-28 | no | **Android** Frida dumper. README: broken on Android 11+. Not desktop DLL. |
| https://github.com/hyugogirubato/KeyDive | 1087 | 2026-06-14 | no | **Android** only (ADB + rooted device + frida-server). Not `widevinecdm.dll`. |
| https://github.com/devine-dl/pywidevine | 935 | 2025-10-27 | no | License **client**. Does **not** extract Chrome/Firefox CDM. |
| https://github.com/li0ard/widevine | 3 | 2026-03-01 | no | TS reimplementation of pywidevine. Same: needs existing provision. |
| https://github.com/castlabs/electron-releases | 288 | 2026-09-03 | no | Licensed Electron CDM for playback. Not an extractor, not a `.wvd`. |

pywidevine maintainer stance (README, still on master 2025):

> Google's Chrome Browser CDM is a simple library extension file programmed in C++ that has been improving its security using math and obscurity for years. It's getting harder and harder to break with its latest versions only being beaten by Brute-force style methods.

https://github.com/devine-dl/pywidevine/blob/master/README.md

Local article already concluded the same for Firefox 4.10.3050. This slice confirms it for 2024–2026 desktop CDMs: historical Chrome-extension / guesser tools stop at ~4.10.2557 / Chrome 112. No `gh`-visible maintained extractor targets 4.10.3050+.

This workspace must not write a replacement dumper.

---

## 2. pywidevine Chrome / Windows device type, and license-server refusal

**Does pywidevine accept Chrome/Windows device type? Yes.**

`DeviceTypes` in https://github.com/devine-dl/pywidevine/blob/master/pywidevine/device.py :

```python
class DeviceTypes(Enum):
    CHROME = 1
    ANDROID = 2
```

CLI `create-device` takes `-t CHROME|ANDROID`, optional `-v` VMP blob, `-l 1..3`. Chrome WVD is typically L3 + VMP FileHashes inside Client ID.

https://github.com/devine-dl/pywidevine/blob/master/pywidevine/main.py

**Does the library itself refuse Chrome CDMs? No.** `Cdm.from_device()` uses whatever type is in the WVD. Chrome vs Android only changes challenge `request_id` construction (`cdm.py`).

**Do license services often refuse Chrome CDMs? Yes, on production endpoints. Conditions:**

1. **VMP / Privacy Mode required for Chrome.** `cdm.py` `set_service_certificate`: “Chrome CDM requires it as of the enforcement of VMP (Verified Media Path).” CLI `--privacy` is **off by default**. Missing cert → challenge looks wrong → reject.
2. **Google revokes desktop CDM generations.** Axinom: older browser CDMs revoked **2024-10-31**; after that Chrome **117+** needed. Later waves noted (2025-04-30, 2026-01-20).  
   https://docs.axinom.com/blog/widevine-revoked-cdm  
   https://docs.axinom.com/services/drm/general/drm-announcements  
   DoveRunner: old Chrome CDM discontinuation (Chrome 107-era) and device/browser revocation errors 7110/7115/7116.  
   https://support.doverunner.com/hc/en-us/articles/47902435642649  
   https://support.doverunner.com/hc/en-us/articles/47901607339289
3. **Test provisions blocked on production.** pywidevine README disclaimer: “License Servers have the ability to block requests from any provision, and are likely already blocking test provisions on production endpoints.”
4. **Type mismatch.** Labeling an Android blob as `CHROME` (or the reverse) changes `request_id` and VMP expectations.
5. **Bitmovin demo is not production.** `pywidevine test` / `cwip-shaka-proxy.appspot.com/no_auth` often accepts a valid device. Japanese VOD / wvks-class endpoints in the local article are stricter (PSSH, UA, ticket, sometimes application_name — KeyDive issue 69).

KeyDive-produced devices are **ANDROID, no VMP** (`recon-keydive.md`). That is the type production Android-oriented license servers expect. A Chrome-typed WVD is a different population: more VMP, more frequent Google CDM-generation revokes.

---

## 3. Public / shared `.wvd` reality

| Axis | Fact |
|------|------|
| Revocation | Google publishes device-certificate status lists. Axinom/DoveRunner surface “revoked” license errors after CDM-generation cutovers. Shared Chrome/Android blobs circulate until the cert is listed, then every copy dies at once. |
| Legal | Circumventing Widevine and redistributing provision material is anti-circumvention territory (US DMCA 1201 and equivalents). Google Widevine terms do not grant a right to extract or share device keys. This slice does not give redistribution steps. |
| This repo | `workspace.json` `out_of_scope` already lists `CDM redistribution`. Article disclaimer: tools are for paid/own-account backup and DRM research, not unauthorized acquisition. **Do not fetch, store, or ship third-party `.wvd`.** |
| Operational | A shared blob is also a shared `deviceUniqueId`. License servers can rate-limit, fingerprint, or ban that ID independently of generation-wide revocation. |

Usable device = **self-extracted from hardware/emulator you operate**, kept in project evidence dirs, not git.

---

## 4. KeyDive on Windows emulator (LDPlayer x86_64) vs ARM64 handset

KeyDive is **Android CDM**, not desktop DLL. README: ADB, **rooted** Android, `frida-server`.  
https://github.com/hyugogirubato/KeyDive/blob/main/README.md

### Official surface

- Maintainer on issue 52 (WSA): “The script is already compatible with WSA… Android environment with DRM widevine and an adb shell root access to run Frida server.” Closed.  
  https://github.com/hyugogirubato/KeyDive/issues/52
- CHANGELOG 2.0.3 (2024-07-07): “Added support for private key function (SDK 35 x86_64).” So x86_64 is in-tree, not ARM-only.  
  https://github.com/hyugogirubato/KeyDive/blob/main/CHANGELOG.md
- Vendor table (`keydive/drm/__init__.py`, main): SDK 22/24 → `libwvdrmengine.so`; SDK 26–31 → `libwvhidl.so`; SDK 33 → `libwvaidl.so`; SDK 34 → `android.hardware.drm-service.widevine`. **SDK 28 HIDL row is `libwvhidl.so`, not `libwvdrmengine.so`.**
- No official issue titled LDPlayer. `gh search issues LDPlayer` on that repo returned empty.
- Issue 63 (`libwvdrmengine.so missing`): old 32-bit phone looping until a DRM session actually loads the `.so`. Not an emulator-specific bug.  
  https://github.com/hyugogirubato/KeyDive/issues/63
- Issue 55 comment: “when i use x86 frida it works” (ABI mismatch).  
  https://github.com/hyugogirubato/KeyDive/issues/55

### LDPlayer (community, not upstream)

Search-layer hit: https://github.com/PyotrMuhammad/Pyotr-x-udemy/blob/main/cdm/README.md — LDPlayer 9 (Android 9 / SDK 28 / x86_64) used with KeyDive; reports `libwvdrmengine.so` vs KeyDive’s SDK 28 `libwvhidl.so` mapping. That is a **community patch**, not KeyDive 3.0.6 default.

Implication: KeyDive **can** run against a rooted Windows Android emulator **if** ADB+Frida ABI match and the loaded Widevine `.so` is in (or patched into) `CDM_VENDOR_API`. It is not a one-command official LDPlayer path.

### ARM64 handset vs x86 emulator

| | ARM64 OEM (Pixel 6 in this lab) | x86_64 emulator (LDPlayer / many AVDs) |
|--|----------------------------------|----------------------------------------|
| CDM library | HIDL/AIDL `libwvhidl.so` / `libwvaidl.so` / service binary | Often older `libwvdrmengine.so` (SDK 28 images) |
| Frida | `android-arm64` | `android-x86_64` (mismatch = attach fail) |
| WVD type | ANDROID L3 | ANDROID L3 (same KeyDive serializer) |
| Identity | OEM company/model/`deviceUniqueId` | Generic Google/x86 emulator identity |
| Revoke / block risk | Lower if unique and unpublished | Higher: shared emulator images, known company/model strings, same blob reused across clones |
| License quality | Local article: Pixel 6 CDM 19.0.1 worked on videomarket | Unverified here; some services filter architecture / emulator |

Emulator CDM is still **Android**. It does **not** satisfy “no Android at all”. It only avoids a physical phone.

Do not document a dump recipe. Canary, if ever: isolated venv, project ADB, `-s` serial, file logs — same localization notes as `recon-keydive.md`.

---

## 5. Feasibility grades (explicit)

1. **每天的下载流程完全在 PC** — **可行**  
   Once a valid self-extracted ANDROID `.wvd` (or `client_id.bin` + `private_key.pem`) exists, pywidevine + mp4decrypt + ffmpeg run on Windows. That is the archived ktv pipeline. Device extract is one-shot; daily work does not need the phone attached.

2. **连第一次 CDM 也不用任何 Android** (no handset, no emulator, no WSA; desktop `widevinecdm.dll` only) — **目前不可行**  
   4.10.3050+ has no maintained open-source extractor. pywidevine will *consume* a Chrome WVD but will not *create* the RSA+client_id from the DLL. Shared Chrome `.wvd` is revoked, legally toxic, and repo-banned.

3. **第一次 CDM 不用 Android 真机，但允许 Windows 上的 Android 模拟器** — **有条件可行**  
   KeyDive + rooted emulator/WSA. Conditions: ABI-matched frida-server, Widevine actually loaded, vendor `.so` name, and accept emulator-identity revoke risk. Not a substitute for Pixel if the target license server fingerprints OEM/ARM.

---

## Design options (short names)

| Name | First device | Daily path | Grade |
|------|--------------|------------|-------|
| `pixel-once-pc-daily` | Pixel 6 + KeyDive 3.0.6 (already recon’d) | pywidevine on PC | **可行** — pick this |
| `emulator-once-pc-daily` | LDPlayer/WSA + KeyDive | pywidevine on PC | **有条件可行** |
| `chrome-dll` | Extract from Chrome/Firefox 4.10.3050+ | n/a | **目前不可行** |
| `shared-wvd` | Third-party blob | n/a | **禁止** (revoke + legal + `out_of_scope`) |

---

## Citations

- https://github.com/devine-dl/pywidevine
- https://github.com/devine-dl/pywidevine/blob/master/pywidevine/device.py
- https://github.com/devine-dl/pywidevine/blob/master/pywidevine/cdm.py
- https://github.com/devine-dl/pywidevine/blob/master/pywidevine/main.py
- https://github.com/devine-dl/pywidevine/blob/master/README.md
- https://github.com/hyugogirubato/KeyDive
- https://github.com/hyugogirubato/KeyDive/blob/main/README.md
- https://github.com/hyugogirubato/KeyDive/blob/main/CHANGELOG.md
- https://github.com/hyugogirubato/KeyDive/blob/main/keydive/drm/__init__.py
- https://github.com/hyugogirubato/KeyDive/issues/52
- https://github.com/hyugogirubato/KeyDive/issues/55
- https://github.com/hyugogirubato/KeyDive/issues/63
- https://github.com/hyugogirubato/KeyDive/issues/69
- https://github.com/wvdumper/dumper
- https://github.com/tomer8007/widevine-l3-decryptor (archived)
- https://github.com/Satsuoni/widevine-l3-guesser (archived)
- https://github.com/tbodt/widevine-l3-decryptor
- https://github.com/widevineleak/Chrome-Widevine-Guesser-2025
- https://docs.axinom.com/blog/widevine-revoked-cdm
- https://docs.axinom.com/services/drm/general/drm-announcements
- https://support.doverunner.com/hc/en-us/articles/47902435642649
- https://bugzilla.mozilla.org/show_bug.cgi?id=2032184
- https://searchfox.org/mozilla-release/source/toolkit/content/gmp-sources/widevinecdm.json
- `article/drm-content-acquisition/widevine-l3-video-download.md`
- `workspace/widevine-l3-download/agent-notes/recon-keydive.md`

Search-layer logs:

- `C:\Users\mengma\.grok\sessions\D%3A%5Creverse_ENV\01a0f0ee-c12b-7041-8a85-3c15d3e81bb2\terminal\call-bc1bba01-33fe-4572-b69e-218ec2190484-16.log`
- `C:\Users\mengma\.grok\sessions\D%3A%5Creverse_ENV\01a0f0ee-c12b-7041-8a85-3c15d3e81bb2\terminal\call-dd5d96c5-ae0c-4d63-9b52-359a997fd72d-32.log`
