# widevine-l3-download

reverse_ENV 内的独立 Widevine L3 个人备份管道。日常 **pixel-once-pc-daily**：自家 ANDROID L3 `.wvd` 指针一次，之后 license / download / decrypt / mux 全在 Windows 上跑。

## 入口

```powershell
$py = "D:\reverse_ENV\workspace\widevine-l3-download\.venv\Scripts\python.exe"
$cli = "D:\reverse_ENV\workspace\widevine-l3-download\widevine_l3.py"
& $py $cli doctor
```

或 `tools/widevine-l3/run.ps1`（转发到本仓）。

## 边界

- 适用：自有设备 L3 CDM 研究提取，已付费/已授权内容的个人备份。
- 禁止：桌面 `widevinecdm.dll` dump、第三方 `.wvd` 分发、未授权内容。
- CDM 三件套只放 `D:\reverse_ENV\storage\cdm-devices\`，本仓 `runtime/cdm-current.json` 只记路径。
- 不要把 keydive / pywidevine 装进 `D:\reverse_ENV\.venv`。

## 测试

```powershell
& "D:\reverse_ENV\.venv\Scripts\python.exe" -m pytest "D:\reverse_ENV\workspace\widevine-l3-download\tests" -q
```
