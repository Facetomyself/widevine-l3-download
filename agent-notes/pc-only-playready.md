# pc-only-playready: Windows 本机 PlayReady 能否替代 Pixel+KeyDive

slice: pc-only-playready
date: 2026-09-30
handles: none
scope: 评估「电脑上完成整条解密」的 PlayReady 旁路。不写 exploit，不输出密钥/PSSH/ticket 原值。

## 搜索路径

- 意图：exploratory / comparison（工具选型，非站点攻击）
- search-layer：`search.py --mode deep --intent exploratory` 四查询（pyplayready 库、Device.prd SL2000、Windows SL2000/SL3000、pyplayready vs pywidevine）。Grok 三源 ok、一查询 timeout；Exa/Tavily 补齐。client-native web_search 并行。
- pavedpath-code：PATH 无 `gh`；命中 `C:\Users\mengma\AppData\Local\GitHubCLI\bin\gh.exe`。`gh search repos pyplayready`、`gh repo view GetWVKeys/pyplayready`、`gh search code`（create-device / Device.load）。`ready-dl/pyplayready` 的 GitHub 代码搜索为空（仓库已迁 git.gay，GitHub 侧几乎是 stub）。
- 本地：归档 MPD 解码 `mspr:pro`（只取 LA_URL/ALGID/KEYLEN，KID/CHECKSUM 打 REDACTED）；`get_keys.py`、adapter、文章、Firefox profile prefs。

权威源（不抄密钥、不写提取步骤）：

| 源 | 用途 |
|----|------|
| 归档 `runtime/ep7_A-SD.mpd` | 双 DRM + PlayReady LA_URL |
| `article/drm-content-acquisition/widevine-l3-video-download.md` | wvks ticket、PlayReady PSSH → E2006 |
| https://git.gay/ready-dl/pyplayready + PyPI pyplayready 0.8.5 | 软件 CDM 合同：`.prd` / create-device |
| https://github.com/ready-dl/pyplayready（170★，pushed 2025-04-04，迁出） | 镜像入口 |
| https://github.com/GetWVKeys/pyplayready | 仍可 `gh search code` 的镜像 |
| https://learn.microsoft.com/en-us/playready/overview/security-level | SL150 / SL2000 / SL3000 |
| https://github.com/MicrosoftEdge/MSEdgeExplainers/.../Media/MFCdm/explainer.md | Edge MF CDM 不导出 content key |
| https://docs.doverunner.com/.../playready-sl3000-windows-chrome | Chrome/Win11 SL3000 走 OS MF，非可抽软件 CDM |
| Firefox 132+ PlayReady 发行说明 | Windows-only、origin-filter、MF CDM |

## 1. 该站点 MPD 是否双 DRM；license 是否只发 Widevine（wvks）

**MPD 是双 DRM。观察到的 Web license ticket 端点是 Widevine-only（wvks）。PlayReady 另有 SOAP LA_URL，不在 wvks。**

归档 `runtime/ep7_A-SD.mpd`（EP07 A-SD，on-demand CENC）：

- `schemeIdUri=urn:uuid:9a04f079-9840-4286-ab92-e65be0885f95`（PlayReady 2.0）+ `mspr:pro` + `cenc:pssh`
- `schemeIdUri=urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed`（Widevine）+ `cenc:pssh`
- 音视频 AdaptationSet 各一份，同一 `cenc:default_KID`

解码 `mspr:pro` → WRMHEADER 4.0.0.0：

- `ALGID=AESCTR`，`KEYLEN=16`（与 CENC 共用同一 content key 空间）
- **`LA_URL=https://prks.videomarket.jp/prlic/rightsmanager.asmx`**（SOAP rights manager，**不是** wvks）
- 无 LUI_URL / DS_ID

对照实测 Widevine 路径（文章 + `scripts/get_keys.py` + adapter）：

- license：`https://wvks.videomarket.jp/?ticket=<ticket>`
- 挑战：pywidevine protobuf，`Content-Type: application/octet-stream`
- **把同一 MPD 的 PlayReady PSSH 丢给 wvks → HTTP 400 `E2006 failed to find any keys`**（文章结论 3 / findings F5）

浏览器侧：归档播放走 ruyipage Firefox 151-proxy。profile `prefs.js` 只有 `media.gmp-widevinecdm.*`（4.10.3050.0），**无** `media.eme.playready` / `mfcdm`。performance 过滤拿到的是 `wvks.videomarket.jp/?ticket=`。Firefox 132+ 虽可在 Windows 上接 PlayReady，但是 MF CDM + origin-filter，本 profile 未开、本站也未出现 prks 请求。

结论口径：

- Manifest：**双 DRM 信令**（PlayReady + Widevine PSSH 并存）。
- 已抓到的 **Web 播放 license 发放：只发 Widevine wvks ticket**。
- PlayReady 的 license 入口写在 PSSH 里（prks SOAP），**从未在本归档的 Firefox 会话里被打到**。未做 Edge 抓包，不能声称站点永远不发 PlayReady license；只能声称 **当前管道与 adapter 只接 wvks**。

## 2. 开源工具在 Windows 上如何拿到 SL2000/SL3000 或软件 CDM；是否仍要一次设备提取

分两条，不要混：

### A. Windows 本机 PlayReady（Edge / Chrome MF CDM）

- 走 `com.microsoft.playready.recommendation`（及 `.3000` 硬件档），密钥留在 Media Foundation / PMP / TEE。
- EME 不把 content key 交给 JS 或用户态解密器。DoveRunner：Win11 Chrome SL3000 是 OS 硬件路径，**不是** 可抽的 `widevinecdm.dll` 同类软件模块。
- 因此：**本机播放 ≠ 本机拿到 KID:KEY 去做 mp4decrypt**。不能替代 Pixel+KeyDive 的「导出 device → 重放 license → 导出 content key」。

### B. pyplayready（Python 软件 CDM，对标 pywidevine）

公开合同（git.gay README / PyPI 0.8.5 / GetWVKeys 镜像 `main.py`）：

```
Device.load("DEVICE.prd") → Cdm.from_device → get_license_challenge(wrm_header)
  → POST SOAP (Content-Type: text/xml) → parse_license → get_keys
```

- `.prd` 内嵌 group certificate，**SL 从证书读出**（enum SL150 / SL2000 / SL3000），不是 Windows 本机自动变成 SL2000。
- `pyplayready create-device -c bgroupcert.dat -k zgpriv.dat`（或 `-pk zgpriv_protected.dat`）把 **已经存在的** group cert + group key 编成 `.prd`。库 **不提供** 这些材料。
- `pyplayready test DEVICE.prd -sl 2000` 打的是 **Microsoft 测试服** `test.playready.microsoft.com/.../rightsmanager.asmx?cfg=(persist:false,sl:2000)`，只验证设备文件，不给商业站点授权。
- Microsoft 文档：SL150 测试证书 **不能** 绑商业 SL2000 内容；商业 license 会看客户端证书 SL。pyplayready 在用户态跑，即使 `.prd` 声称 SL3000，也不是 TEE。

**仍要一次设备提取。** 对象从「Pixel + KeyDive → `.wvd`」换成「已 provision 的 PlayReady 设备/证书链 → `bgroupcert.dat`+`zgpriv.dat` → `.prd`」。Windows 零售机不会因为装了 Edge 就掉出可用的生产 group key。本切片不记录任何 Windows/Xbox/TV 提取步骤。

软件 CDM 与硬件 SL 对照：

| 材料 | 谁发 | 能否在 PC 上当 pyplayready 设备 |
|------|------|--------------------------------|
| Microsoft 测试证书 SL150 | Porting Kit / 测试服 | 只能打测试服，打不了 videomarket |
| 生产 SL2000 软件证书 | OEM provision | 需要已提取的 group 材料；库本身不生成 |
| 生产 SL3000 | TEE 设备 | `.prd` 可声称 3000，无 TEE；站点还可能拒 |

## 3. 对 videomarket / ktv-smart.jp 的 wvks ticket，PlayReady 路径是否对得上

**对不上。不是同一 ticket URL，也不是同一协议。**

| | Widevine（已跑通） | PlayReady（MPD 信令） |
|--|-------------------|----------------------|
| 端点 | `wvks.videomarket.jp/?ticket=` | `prks.videomarket.jp/prlic/rightsmanager.asmx` |
| 协议 | protobuf challenge，octet-stream | SOAP/XML WRMHEADER challenge |
| 令牌 | 播放页签发的短时 ticket | LA_URL 写死在 PSSH；归档未见 ticket 查询串 |
| PSSH | `edef8ba9-...` | `9a04f079-...` |
| 客户端 | pywidevine + Pixel L3 `.wvd` | 若走软件 CDM：pyplayready + `.prd`；若走本机：Edge MF，无 key 导出 |
| 实测 | ticket + Widevine PSSH → keys | PlayReady PSSH + wvks → E2006 |

adapter `workspace/widevine-l3-download/adapters/ktv-smart-jp.json` 的 `license_url` 只有 wvks 模板。把 pyplayready 指到同一 ticket URL 会重复 E2006。

未知（未抓 Edge / 未打 prks）：

- prks 是否还要播放 token、Cookie、自定义 SOAP header
- shaka 在 Edge 是否真的选 PlayReady（Web 播放器可能永远选 Widevine）
- 同一 CENC key 在 prks 是否对软件 SL2000 发放（HDCP / MinimumSecurityLevel）

这些未知不改变「wvks ticket 不是 PlayReady 入口」。

## 4. 可行性

**对本案例不可行。** 不能替代 Pixel+KeyDive 作为「电脑上完成整条解密」的另一条路。

分级：

1. **本案例（ktv-smart.jp / videomarket wvks）**  
   已验证管道是 Widevine ticket。PlayReady 是平行 license 栈。Windows 本机 PlayReady 不导出 key。pyplayready 既对不上 wvks，又要另一次设备提取，还要未验证的 prks 会话。

2. **仅部分站点**  
   若某站 **只** 发 PlayReady（典型：Edge/UWP/Xbox 客户端，license 就是 SOAP LA_URL），且已有合法 `.prd`，则 pyplayready 在 PC 上的角色类似 pywidevine。这是另一类站点适配器，不是本站 drop-in。

3. **不可「用本机 PlayReady 替代 Widevine L3 提取」**  
   OS CDM = 播放保护路径。软件 CDM（pyplayready）= 仍要 provision 材料。两条都不消灭「一次设备提取」。

文章原结论仍成立：不要试图提取桌面浏览器 CDM（Firefox `widevinecdm.dll` 4.10.3050 无现成 dumper；Edge PlayReady 更是 MF/PMP）。正确的 PC 重放路径仍是 **已有 Android L3 `.wvd` + pywidevine + wvks**。

## 阻塞

- 无 Edge/Chrome 对本站的 PlayReady license 抓包，prks 的鉴权头未知。
- `ready-dl/pyplayready` GitHub 代码搜索空（源在 git.gay）；PyPI/镜像 README 足够回答合同，不必再 clone。
- 本切片不获取、不测试任何 `.prd` / group cert。

## 建议下一步

保持 Pixel+KeyDive → `.wvd` → `tools/widevine-l3` + ktv-smart-jp adapter（wvks）。不要为这个站点加 PlayReady 分支。若以后遇到 **仅 PlayReady、LA_URL 可重放** 的站点，再单独立项评估 `.prd` 来源，而不是复用 wvks ticket。
