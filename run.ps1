param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsRest
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$script = Join-Path $PSScriptRoot "widevine_l3.py"
$adbDir = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "tools\adb"
if (-not (Test-Path $adbDir)) {
    $adbDir = "D:\reverse_ENV\tools\adb"
}
if (Test-Path $adbDir) {
    $env:PATH = "$adbDir;" + $env:PATH
    $env:ADB = Join-Path $adbDir "adb.exe"
}
if (-not (Test-Path $python)) {
    throw "widevine-l3 isolated venv missing: $python. Run: python widevine_l3.py bootstrap"
}
& $python $script @ArgsRest
exit $LASTEXITCODE
