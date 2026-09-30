# recon-archive: ktv-smart-jp-download 站点硬编码 vs 通用管道

归档：`D:\reverse_ENV\storage\workspace-archive\2026-09-28\ktv-smart-jp-download`
来源 MANIFEST：utc `2026-09-28T06:14:55Z`，4824 files，1_545_112_632 bytes（约 1.44 GiB）
对照文章：`article/drm-content-acquisition/widevine-l3-video-download.md`
本切片不复制大文件、不输出 client_id / private_key / wvd / PSSH / KID:KEY 原值。

## 1. scripts/ 职责与硬编码

五个 py，均相对归档根。无下载 / mp4decrypt / ffmpeg 封装脚本；[5]–[7] 只在 README / PROGRESS 里用手敲命令。

| 脚本 | 职责 | 硬编码 |
|------|------|--------|
| `scripts/launch_ruyi.py` | 起持久 ruyipage 151-proxy，打开剧集页，写 `runtime/session.json`，等 `runtime/stop.requested` 后分离不关浏览器 | TARGET=`https://ktv-smart.jp/store/movie.php?id=A035028008999H01`（EP07）；PROXY=`http://127.0.0.1:7897`；FIREFOX=`D:\reverse_ENV\tools\ruyipage\runtimes\151-proxy\firefox\firefox.exe`；profile=`runtime/ruyi-profile`。无 UA/Referer 头（浏览器自身）。 |
| `scripts/launch_and_inspect.py` | 同上 relaunch + DOM inspect，写 `runtime/inspect.json`，capture 仅滤 `m3u8` | 同上 TARGET / PROXY / FIREFOX。登录提示正则含日文「ログイン」等。 |
| `scripts/inspect_page.py` | 按 `session.json` 的 address attach 已开会话，dump 链接/video/iframe/script | **无** URL / PSSH / WVD / 代理 / UA / Referer。站点痕迹只在日文登录 hint 与 movie/play 链接过滤。 |
| `scripts/capture_streams.py` | 打开 EP07、点播放、从 performance + capture 抽 manifest/license 类 URL，写 `runtime/stream-capture.json` | 同上 TARGET / PROXY / FIREFOX。过滤关键字含 `videomarket`（站点绑死）。 |
| `scripts/get_keys.py` | pywidevine：Device.load → challenge → POST license → 打印 keys | WVD 绝对绑死相对路径 `runtime/cdm/Google/Pixel 6/33098/2382784800/google_pixel_6_19.0.1@av1a.240428.001_*_33098_l3.wvd`；license host 绑死 `https://wvks.videomarket.jp/?ticket=` + argv[1]；**PSSH_B64 写死为本话 Widevine 组**（与 `runtime/ep7_A-SD.mpd` 的 edef8ba9 组一致，未做 system-id 选择）；UA=`Mozilla/5.0 ... Firefox/151.0`；Referer=`https://ktv-smart.jp/`；Content-Type `application/octet-stream`。**无 proxies=**，不走 7897。无 ticket 则 URL 为 None。 |

站点绑死常量（跨脚本重复）：

- 剧集 ID 模式：`A03502800N999H01`（PROGRESS：N=2..12；脚本只钉 N=8 即第 7 话）
- 浏览器出口：Clash `127.0.0.1:7897`（README：需日本节点）
- license：`wvks.videomarket.jp`
- Referer：`https://ktv-smart.jp/`
- ruyipage 运行时路径写死在 `D:\reverse_ENV\tools\ruyipage\...`

`runtime/ep7_A-SD.mpd`（8815 B）：DASH **on-demand**（`isoff-on-demand` + 每 Representation 一个 `<BaseURL>` 完整 mp4），双组 ContentProtection（PlayReady `9a04f079-...` + Widevine `edef8ba9-...`），画质 A-0..A-4 视频 + A-0/A-1/A-3 音频。无 CDN 目录前缀（下载时要另拼 Akamai 基址）。

## 2. tools/keydive-venv 版本

`tools/keydive-venv/pyvenv.cfg`：

- version = **3.13.12**
- include-system-site-packages = false
- home = 用户级 `Python313`
- **executable / command 的基解释器是** `D:\reverse_ENV\.venv\Scripts\python.exe`（从主 venv 再 `python -m venv`，不是从官方 Python 直接建）

`pip freeze`（只读，未安装）关键行：

| 包 | 安装版本 | 声明约束 |
|----|----------|----------|
| keydive | **3.0.6** | Requires-Python >=3.8,<4.0；frida>=17.1.3；**protobuf>=5.29.5,<6.0.0**；construct>=2.10.70,<3.0.0 |
| pywidevine | **1.9.0** | **protobuf>=6.33.0,<7.0.0** |
| protobuf | **6.33.6** | 落在 pywidevine 区间，**超出 keydive 上界** |
| frida | **17.18.0** | 满足 keydive；文章写 17.15.3（漂移） |
| construct | **2.8.8** | **低于** keydive 要求的 2.10.70 |
| requests | 2.34.2 | 满足两边 |

同 venv 同时装 keydive + pywidevine 时 protobuf 被解析到 6.x。KeyDive 3.0.6 仍跑通（见 `runtime/keydive-run.log` 头：Version 3.0.6，Pixel 6，SDK API 35，arm64）。日志含 CDM 材料，**禁止复制**。

文章「keydive 会拉低 protobuf、勿污染主 venv」成立：主 `.venv` 若直接 pip install keydive 会与 pywidevine 的 protobuf>=6.33 对打。隔离 venv 方向对，但当前隔离体本身已是「pywidevine 赢、keydive 约束被打破」。

## 3. 已 vendor 的大工具（只记路径与量级，未复制）

| 产物 | 路径 | 体积量级 |
|------|------|----------|
| Kaltura 测试 APK | `runtime/cdm/kaltura-device-info-release.apk` | 3_076_862 B（约 2.9 MiB） |
| Bento4 zip | `tools/bento4.zip` | 6_868_939 B（约 6.6 MiB） |
| Bento4 解包 | `tools/bento4/Bento4-SDK-1-6-0-641.x86_64-microsoft-win32/` | 186 files / 12_389_408 B（约 11.8 MiB）；`bin/mp4decrypt.exe` 366_080 B |
| ffmpeg zip | `tools/ffmpeg.zip` | 194_571_190 B（约 186 MiB） |
| ffmpeg 解包 | `tools/ffmpeg-tmp/ffmpeg-master-latest-win64-gpl/` | 44 files / 506_726_811 B（约 483 MiB）；`bin/ffmpeg.exe`≈157 MiB，`ffplay.exe`≈159 MiB，`ffprobe.exe`≈157 MiB |
| WidevineProxy2 | `tools/WidevineProxy2-1.2.7.xpi` | 151_480 B（备用扩展，PROGRESS 称 UI 难自动化，实际走 pywidevine） |
| 成品样片 | `downloads/` 下一话 mp4 | 295_050_105 B（约 281 MiB）；属站点产物，非工具 |

Bento4 版本钉在目录名 **1.6.0-641**（与文章一致）。ffmpeg 无 VERSION 文件，目录名 **master-latest-win64-gpl**（与文章「master-win64-gpl」一致）。

新项目应引用仓内已有工具或单份 vendor，不要再把 480+ MiB ffmpeg 解包树拷进 `workspace/widevine-l3-download`。

## 4. runtime/cdm 结构（相对路径 + 文件名模式）

```
runtime/cdm/
  kaltura-device-info-release.apk          # 手动安装的测试播放器
  kaltura-*.png / kaltura-screen*.png      # UI 截图（FAB 菜单不稳定的证据）
  bitmovin.png / chrome2.png               # 改用设备 Chrome + bitmovin demo 触发
  ui.xml .. ui4.xml                        # uiautomator dump
  Google/Pixel 6/<system_id>/<numeric_id>/
    client_id.bin
    private_key.pem
    google_pixel_6_<cdm_ver>@<build>_<hex8>_<system_id>_l3.wvd
```

本归档实例：`<system_id>=33098`（OEM L3 provisioning 证书），第三段数字目录 `2382784800`，wvd 文件名含 `19.0.1@av1a.240428.001` 与 `_l3`。**不记录文件内容 / hex。**

KeyDive 输出布局可复用：`{company}/{model}/{system_id}/{id}/` + 三件套。`get_keys.py` 把整条路径写死，没有「扫描最新 wvd」逻辑。

旁路 runtime（非 CDM，但站点绑死）：

- `runtime/ruyi-profile/`：持久 Firefox，含 ktv-smart.jp 登录态、gmp-widevinecdm `4.10.3050.0`、已装 WidevineProxy2
- `runtime/ep7_A-SD.mpd`、`inspect.json`、`session.json`（proxy 7897）、`keydive-run.log`、`launch.log`
- `mitmproxy_traffic.flow` 在归档根

## 5. 已通用 vs 绑死 videomarket / ktv-smart.jp

已通用（工具与步骤存在，脚本未参数化）：

1. **KeyDive L3 提取**：隔离 venv + 真机 frida hook；触发用公开 bitmovin DRM demo，不依赖站点 app。Kaltura APK 仅作备选，已本地 vendor。
2. **pywidevine 重放骨架**：Device.load / Cdm / PSSH / get_license_challenge / parse_license / get_keys。不需要浏览器 challenge。
3. **PSSH 按 system id 选择**：文章有判别逻辑；归档 **没有** 独立脚本，`get_keys.py` 跳过选择、直接用写死的 Widevine 组。
4. **mp4decrypt**（Bento4）+ **ffmpeg -c copy**：本地 exe 齐，无 wrapper。
5. **on-demand 整文件下载**：curl + Referer + UA + 代理 — 模式通用，命令散落在文档。

绑死本站 / 本话：

- 播放页、剧集 ID、Referer、license host `wvks.videomarket.jp`、capture 关键字 `videomarket`
- 文章级链路：`vm_access_token.php` → `vm_play_token.php` → `pf-api.videomarket.jp/v1/play/ktv/streaming/web` → Akamai `vmdash-cenc.akamaized.net` + ticket
- EP07 的 PSSH 常量、WVD 路径、成品文件名
- 日本出口 / 非日 IP errorCode 10003 / Clash 7897 节点名（PROGRESS 文本）
- `Authlogin` 会话 cookie、租赁绑定账号
- ruyi-profile 与 launch 脚本默认打开本站 URL

缺口（通用管道要补的适配器边界）：

- 无「站点适配器」：ticket 获取、license URL 模板、Referer/UA、代理、PSSH 来源均未接口化
- 无 mpd→选 Widevine PSSH→选档→拼 BaseURL 的解析器
- 无 download / decrypt / mux 脚本
- `get_keys.py` 不走代理，与浏览器脚本的 7897 不一致；license 重放依赖系统代理或直连

## 6. 本地化缺口

1. **PATH 上的 adb**  
   本机当前 shell `Get-Command adb` 无命中。仓内有 `D:\reverse_ENV\tools\adb\adb.exe`（`source.properties` Pkg.Revision=37.0.0）。文章写 `export PATH="/path/to/adb:$PATH"`，归档脚本都不调 adb。KeyDive CLI 依赖 PATH 上的 adb。本地化应显式传入 `D:\reverse_ENV\tools\adb`。

2. **GitHub 下 Kaltura APK**  
   文章：KeyDive `-a player` 自动模式卡在 GitHub 下 APK（直连 SSL 中断）。归档已把 `kaltura-device-info-release.apk` 放进 `runtime/cdm/`，实际成功路径是 **不带 `-a` 的纯 hook + 设备 Chrome 开 bitmovin**。通用工具应 vendor 或镜像该 APK，禁止运行时打 GitHub。

3. **主 venv 污染**  
   - 隔离 venv 的基解释器是 `D:\reverse_ENV\.venv\Scripts\python.exe`  
   - keydive protobuf<6 vs pywidevine protobuf>=6.33，安装结果 6.33.6  
   - construct 2.8.8 vs keydive >=2.10.70  
   新工具链：独立 venv（基解释器用官方 Python313 或复制，不要套 .venv），protobuf 策略要二选一或拆两个 venv（extract vs replay）。

4. **px-proxy 已停用 vs 文章仍写 adb reverse 8085**  
   - 架构 / `docs/脚本参考.md` / xfcap：`px-proxy.ps1 -Action on` **直接失败**，仅 `-Action off` 清残留；App 抓包唯一入口 xfcap，禁止设备全局 `http_proxy`。  
   - 文章 [3] 仍写：`adb reverse tcp:8085 tcp:<本机clash>` + `settings put global http_proxy 127.0.0.1:8085`。  
   - 归档 PROGRESS 仍写：`px-proxy.ps1 -Project ktv-smart-jp-download -Action on/off`（adb reverse 8085）。  
   - 归档浏览器脚本实际用 **Clash 7897**，与 8085 不是同一条路。  
   设备侧 CDM 提取若只需访问 bitmovin.com，不一定要日本节点，更不应再开已停用的 px-proxy。站点播放 / license / Akamai 才要 JP 出口（本机 7897 或系统代理）。本地化文档必须把「设备提取出口」和「站点重放出口」拆开，并删掉 px-proxy on。

其它漂移：

- 文章 frida **17.15.3** vs freeze **17.18.0**
- 文章 pywidevine「最新」vs 钉死 **1.9.0**
- 桌面 Firefox CDM 4.10.3050 在 profile 里，文章结论「不要提桌面 CDM」仍成立

## 7. 对通用化的直接含义

可抽成仓内工具的四段：`cdm-extract`（KeyDive + 本地 APK + 显式 adb）→ `pssh-select`（mpd/system-id）→ `license-replay`（pywidevine，参数：wvd、license URL、PSSH、UA、Referer、proxy）→ `decrypt-mux`（mp4decrypt + ffmpeg）。

站点差异只进适配器：ktv-smart.jp / videomarket 的 token 链、ticket、Referer、剧集 ID、JP 代理。归档 scripts 不能当通用 CLI 用。
)
