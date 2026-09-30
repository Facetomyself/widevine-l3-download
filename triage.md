# triage

## 未完成

| 项 | 原因 | 建议 |
|----|------|------|
| 带真实 ticket 的 `run` canary | ticket 分钟级，要从播放页现抓 | 用户打开已租赁页后：`widevine_l3.py run --adapter ktv-smart-jp --ticket …` |
| 真机 `extract` canary | 日常不再需要；吊销后才要 | 用户确认 Pixel 在线：`px-frida.ps1` → `extract --auto web` → `cdm --install-from` |
| 主 venv `keydive==3.0.6` 残留 | 本切片不卸载，避免牵动其它会话 | 另开维护任务从 `.venv` 卸掉 |
| 知识库文章仍写 px-proxy 8085 | `article/` 是独立子仓 | 用 `article-archiver` 改 `widevine-l3-video-download.md` 指向 `tools/widevine-l3` 与 pixel-once-pc-daily |
| ffmpeg / mp4decrypt 二进制 | gitignored，依赖 bootstrap 从归档复制 | 归档若清理，需重新放入 vendor zip |
| Frida 17.15.3 vs 文档中的 Muida 17.16.1 | 主 venv 实测仍是 17.15.3；extract venv 钉 17.15.3 | 仅 provision 时对齐设备 server |
| LDPlayer extract | 有可用自家 `.wvd`，按方案跳过 | 仅当该 device 被吊销且 Pixel 不可用时 canary |

## 已关闭

- 通用 CLI 与 ktv adapter
- 隔离 venv 锁（keydive 3.0.6 / pywidevine 1.9.0 / protobuf 6.33.6 / frida 17.15.3）
- 本地 Kaltura APK、ADB PATH、日志直写
- CDM 指针 + `storage/cdm-devices/` 安装
- 日常 `doctor`（`wvd-present`）与 `doctor --provision`
- `run` 子命令（license → download → decrypt → mux）
- CLI 迁入独立项目目录；pytest 12 passed；日常 doctor 绿
- 独立 Git 仓：项目根 `.git`，Private 远端待首提后登记
