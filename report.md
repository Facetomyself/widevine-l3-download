# Widevine L3 通用化与 KeyDive 本地化

日期：2026-09-30  
来源：`storage/workspace-archive/2026-09-28/ktv-smart-jp-download`  
上游：https://github.com/hyugogirubato/KeyDive（3.0.6，MIT）

## 结论

ktv-smart.jp 那次租赁剧集下载已经证明七步管道可复用。站点硬编码留在归档脚本里；跨项目能力落到本独立仓 `workspace/widevine-l3-download/`。

1. **通用段**：CDM 提取、MPD 按 system id 选 Widevine PSSH、pywidevine license 重放、带 Referer/UA/代理的下载、mp4decrypt、ffmpeg `-c copy`。
2. **站点段**：license URL 模板、Referer、UA、代理。当前 adapter：`workspace/widevine-l3-download/adapters/ktv-smart-jp.json`。
3. **本地化**：两个隔离 venv（KeyDive 要 construct 2.10.70，pywidevine 要 2.8.8）；提取侧 Frida 钉 17.15.3；ADB 固定 `tools/adb/adb.exe`；Kaltura APK 预置进提取 venv 的 `keydive/docs/server/kaltura.apk`，`-a player` 不再打 GitHub；默认提取走 `-a web`（Bitmovin）；日志直写文件。
4. **日常 PC**：`pixel-once-pc-daily`。自家 L3 三件套在 `storage/cdm-devices/google-pixel6-33098/`，指针 `runtime/cdm-current.json`。`doctor` 日常绿（含 `wvd-present`）；`run` 串 license→download→decrypt→mux。`extract` 只用于 provision。桌面 DLL dump 与第三方 `.wvd` 仍禁止。PlayReady/`prks` 不是本站 drop-in。
5. **独立仓**：源码、测试、adapter、三件套在 `workspace/widevine-l3-download`。`tools/widevine-l3/run.ps1` 只转发。

## 证据

- 归档盘点：`agent-notes/recon-archive.md`
- KeyDive 上游：`agent-notes/recon-keydive.md`
- 本仓工具：`agent-notes/recon-tools.md`
- PC-only CDM：`agent-notes/pc-only-cdm.md`
- PlayReady：`agent-notes/pc-only-playready.md`
- CLI：`D:\reverse_ENV\workspace\widevine-l3-download\widevine_l3.py`

## 不做

- 不把 CDM 材料拷进 workspace Git 树；指针只记路径。
- 不把 ruyipage 登录脚本并进通用 CLI。ticket 是运行时输入。
- 不卸载主 venv 里残留的 `keydive==3.0.6`。
- 本次不跑真机 extract canary，也不跑 LDPlayer extract canary。
