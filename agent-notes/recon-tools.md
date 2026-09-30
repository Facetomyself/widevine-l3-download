# recon-tools: KeyDive / pywidevine / mp4decrypt / ffmpeg 落点盘点

slice: recon-tools
date: 2026-09-30
handles: none
git: `refactor/web-reverse-platform-v2...origin/refactor/web-reverse-platform-v2`（工作树已有无关脏：`tools/README.md`、`docs/工具与环境.md`、`tools/muida-frida/`）

## 1. tools/ 现存量

`D:\reverse_ENV\tools` 清单与 `tools/README.md` 均无 ffmpeg / Bento4 / keydive / pywidevine / widevine-l3。

| 组件 | tools/ 状态 | 绝对路径 |
|------|-------------|----------|
| ffmpeg | **缺失** | — |
| Bento4 / mp4decrypt | **缺失** | — |
| keydive CLI | **缺失**（目录不存在） | — |
| pywidevine CLI | **缺失**（目录不存在） | — |
| adb | 有 | `D:\reverse_ENV\tools\adb\adb.exe` |
| frida-server-android-arm64 | 有 | `D:\reverse_ENV\tools\frida-server-android-arm64`（53,489,240 B） |
| frida-server（LDPlayer x86_64） | 有 | `D:\reverse_ENV\tools\frida-server`（111,479,872 B） |
| 主 venv frida | 有 | `D:\reverse_ENV\.venv\Scripts\frida.exe` |

污染例外：主 venv **已装** `keydive==3.0.6`（`D:\reverse_ENV\.venv\Lib\site-packages\keydive`，2026-09-22），**未装** `pywidevine`。这不是 `tools/` 落点。

## 2. 健康检查（未启设备、未跑 px-status）

```
adb.exe version  -> Android Debug Bridge 1.0.41 / platform 37.0.0-14910828
                   Installed as D:\reverse_ENV\tools\adb\adb.exe
frida --version  -> 17.15.3
pip show frida   -> 17.15.3  (Required-by: frida-tools, keydive)
pip show frida-tools -> 14.10.4
pip show protobuf -> 7.36.2  (Required-by: angr, keydive, onnxruntime)
```

pixel6-control 本机路径（`SKILL.md`「本机路径」）：

- adb: `D:\reverse_ENV\tools\adb\adb.exe`
- Frida CLI: `D:\reverse_ENV\.venv\Scripts\frida.exe`
- Pixel 6 server: `D:\reverse_ENV\tools\frida-server-android-arm64`（文档记 17.15.3 handshake 2026-08-26）
- 禁止把 `tools\frida-server`（x86_64）推到 Pixel 6
- Frida 版本不匹配只报告，禁止脚本自行升级宿主 Frida

## 3. 落点：tools/<name>/ 而非 workspace/

架构「路径与约束」+ AI 规范 §4：便携 CLI 进 `tools\`，项目证据/脚本进 `workspace\<项目>`。跨项目复用的 KeyDive/pywidevine/mp4decrypt/ffmpeg 应落 `tools/widevine-l3/`（或拆 `tools/ffmpeg` + `tools/bento4` + `tools/widevine-l3`），不要堆进 `workspace/widevine-l3-download/`。

同类先例：

| 先例 | 模式 | 路径 |
|------|------|------|
| 隔离 venv | ASC：androguard 会再装 frida，禁止进主 `.venv` | `tools/asc/.venv/` + `requirements-lock.txt`；Agent 入口 `skill/apk-reverse/scripts/asc.py` |
| 隔离 venv | offline-ocr：antlr4 与 Qiling 冲突 | `tools/offline-ocr/.venv/`；模型在 `storage/ocr-models/` |
| vendor 二进制 gitignored | scrcpy 4.1：README+SHA 跟踪，树 gitignored | `tools/scrcpy/`；入口 skill 脚本 |
| vendor 二进制 gitignored | xfcap aarch64 ELF / xfqtrace `bin\` | `tools/xfcap/xfcap`、`tools/xfqtrace/*` |

workspace 只放站点适配器、CDM 产出、下载物。`workspace/widevine-l3-download/` 目前仅有 `workspace.json`，**未登记** `docs/workspace-projects.yaml`。归档项目 `ktv-smart-jp-download` 是 `excluded`。

## 4. 落地 `tools/widevine-l3/` 要改的文档

必须：

1. `tools/README.md` — 工具表 + 隔离约束（protobuf / frida pin）
2. `docs/工具与环境.md` — 版本/路径表；「更新工具后」清单第 1–2 项
3. `.gitignore` — `tools/widevine-l3/.venv/`；vendor 树按 scrcpy 模式 ignore 二进制、保留 README

按需：

4. `docs/脚本参考.md` — **仅当**增加 `skill/*/scripts/` wrapper 时加一行。纯 CLI 不强制。调用规范本身不用改。
5. `docs/workspace-projects.yaml` — **登记 workspace 项目** `widevine-l3-download`，不是登记 tools。tools 不进 yaml。
6. `docs/agent-architecture.md` Skill 路由 / `skill/README.md` — **仅当**新建 skill。

**新 skill：默认不做。** 先做 CLI（隔离 venv + doctor）。adb/frida 已由 `pixel6-control` 覆盖。只有 Agent 要把「L3 CDM 提取 / license 重放 / decrypt-mux」当成可路由工作流时再加 skill。

## 5. protobuf / frida 隔离

声明冲突（不可装进主 `.venv`）：

| 包 | 声明 | 主 venv 实际 | 归档 keydive-venv |
|----|------|--------------|-------------------|
| keydive | `protobuf>=5.29.5,<6.0.0`；`frida>=17.1.3` | 3.0.6 已污染主 venv | 3.0.6 |
| pywidevine | `protobuf>=6.33.0,<7.0.0` | 未装 | 1.9.0 |
| angr | `protobuf>=6.33.0` | 9.2.222 | — |
| protobuf | — | **7.36.2** | **6.33.6** |
| frida | — | **17.15.3**（Pixel 6 合同） | **17.18.0**（与设备 server 漂移） |

归档实测：同一隔离 venv 里 keydive 3.0.6 + pywidevine 1.9.0 + protobuf 6.33.6 能跑（违反 keydive 声明的 `<6`，满足 pywidevine）。主 venv 7.36.2 对两者声明都不合规。

新隔离 venv 建议：

- 用主 Python 建 `tools/widevine-l3/.venv`，**不要** `pip install` 进 `D:\reverse_ENV\.venv`
- pin `frida==17.15.3`（对齐宿主 + Pixel 6 server；归档 17.18.0 不要照搬）
- protobuf 以归档可运行的 `6.33.6` 为起点，freeze 进 lock；不要让 pip 拉 7.x
- 主 venv 已有的 keydive 3.0.6 视为污染：本切片不卸载，落地时禁止再往主 venv 装

## 6. 归档资产：引用 vs 复制

根：`D:\reverse_ENV\storage\workspace-archive\2026-09-28\ktv-smart-jp-download\`

| 资产 | 体积 | SHA-256 | 建议 |
|------|------|---------|------|
| `tools/ffmpeg.zip` | 194,571,190 B | `576CE558496DBF237DBC859A561E5240D59DC126BAAC921F59704D52260C060E` | **不要再复制一份 zip**。从该 zip 解到 gitignored `tools/ffmpeg/`（scrcpy 模式），README 写 SHA。或短期 junction 到已解包树，归档可能被清，不宜当长期路径。 |
| `tools/ffmpeg-tmp/` 已解包 | 506,726,811 B / 44 files | ffmpeg `N-126755-g52f05ac780-20260922` BtbN win64-gpl | 解包树含 zip 膨胀。exe 164,348,416 B。tools 侧只留 `bin/ffmpeg.exe`+`ffprobe.exe`。 |
| `tools/bento4.zip` | 6,868,939 B | `6916A390F75878872594BE74554B8B54AB220BB29812424441A8E1ECC9A6AC5E` | 可复制 zip 到 `tools/bento4/` 或只抽 bin。 |
| `mp4decrypt.exe` | 366,080 B | `4BF6F374F8623AF2142E7C5D4EC58C824F7CCE19F8FCAAC3E44041B215D81286` | **复制小二进制**（Bento4 1.6.0-641 / mp4decrypt 1.4）。不必 junction 整个 SDK。 |
| `runtime/cdm/kaltura-device-info-release.apk` | 3,076,862 B | `37D01C6AF0A567951D39C3F806B7DFA8D6AC1A88617ED9B2129B62566B8A5418` | **复制小 APK** 到 `tools/widevine-l3/assets/`。根 `.gitignore` 已有 `*.apk`。文档指向本地文件，禁止 KeyDive `-a player` 再下 GitHub。 |
| `tools/keydive-venv/` | 189,972,097 B / 4052 files | — | **不要复制 venv**。按 lock 重建隔离环境。 |

ffmpeg-tmp 506MB + zip 194MB 已在归档双份，tools 再拷会三份。优先：文档指向 archive zip → 解到 gitignored `tools/ffmpeg/` 一份。

## 7. 建议目录

```
tools/widevine-l3/          README + lock + 隔离 .venv + assets/kaltura APK
tools/widevine-l3/.venv/    gitignored；keydive+pywidevine；frida==17.15.3
tools/bento4/               README + mp4decrypt.exe（小，可跟踪或 ignore）
tools/ffmpeg/               README+SHA；bin gitignored（从归档 zip 解）
```

ADB 固定 `tools\adb\adb.exe` 进 PATH/包装脚本，KeyDive 需要 adb 在 PATH。

## 8. 阻塞 / 非阻塞

- 非阻塞：tools 四件套均缺失，归档可作源。
- 注意：主 venv 已有 keydive 3.0.6 + protobuf 7.36.2，与 angr 合同冲突；落地不得再 pip 进主 venv。
- 注意：归档 keydive-venv 的 frida 17.18.0 与 Pixel 6 17.15.3 不一致。
- 未跑：设备 handshake、px-status、KeyDive 真机提取。
