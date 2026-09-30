# widevine-l3-download

把 `ktv-smart-jp-download` 实测七步和 [KeyDive](https://github.com/hyugogirubato/KeyDive) 3.0.6 收成独立项目。站点差异只进 `adapters/`。

适用边界：自有 Android L3 CDM 研究提取，以及已付费/已授权内容的个人备份。不要把 `.wvd` / `client_id.bin` / `private_key.pem` 外传。

日常是 **pixel-once-pc-daily**：自家 L3 `.wvd` 指针一次，之后 license / download / decrypt / mux 全在 Windows 上跑，不插手机。`extract` 只用于 provision 或吊销后重提。

## 路径

| 项 | 位置 |
|----|------|
| CLI | `widevine_l3.py` |
| 包装 | `run.ps1`（给 PATH 加上 reverse_ENV `tools/adb`） |
| reverse_ENV 转发 | `D:\reverse_ENV\tools\widevine-l3\run.ps1` |
| 提取 venv | `.venv-extract/`（KeyDive + construct 2.10.70 + Frida 17.15.3） |
| 重放 venv | `.venv/`（pywidevine + construct 2.8.8） |
| mp4decrypt | `D:\reverse_ENV\tools\bento4\bin\mp4decrypt.exe` |
| ffmpeg | `D:\reverse_ENV\tools\ffmpeg\bin\ffmpeg.exe` |
| CDM 指针 | `runtime/cdm-current.json`（gitignore，只记路径） |
| CDM 材料 | `D:\reverse_ENV\storage\cdm-devices\<device-id>/` |

禁止把 `keydive` / `pywidevine` 装进 `D:\reverse_ENV\.venv`。

## 初始化

```powershell
$py = "D:\reverse_ENV\.venv\Scripts\python.exe"
$cli = "D:\reverse_ENV\workspace\widevine-l3-download\widevine_l3.py"
& $py $cli bootstrap
& $py $cli doctor
```

## 命令

```powershell
$wv = "D:\reverse_ENV\workspace\widevine-l3-download\.venv\Scripts\python.exe"
$cli = "D:\reverse_ENV\workspace\widevine-l3-download\widevine_l3.py"

# 一次性：收进 storage 并写指针
& $wv $cli cdm --install-from "<dir-with-wvd>" --device-id google-pixel6-33098
& $wv $cli doctor

# 日常（PC）
& $wv $cli run --adapter ktv-smart-jp --ticket "<ticket>" --mpd manifest.mpd `
  --video-url "<enc-video>" --audio-url "<enc-audio>" --output out.mp4

# provision / 吊销后重提（需要 Pixel 或模拟器）
& $wv $cli extract -o runtime\cdm -s "<serial>"
```

## 测试

```powershell
& "D:\reverse_ENV\.venv\Scripts\python.exe" -m pytest tests -q
```

## adapter

| 文件 | 站点 |
|------|------|
| `adapters/ktv-smart-jp.json` | ktv-smart.jp / videomarket / カンテレドーガ |

ticket、PSSH、媒体 URL 运行时传入。PlayReady PSSH / `prks` SOAP 不是本管道的 drop-in。

## 来源

- 开源：KeyDive 3.0.6 MIT
- 归档：`storage/workspace-archive/2026-09-28/ktv-smart-jp-download`
- 方法：`article/drm-content-acquisition/widevine-l3-video-download.md`
