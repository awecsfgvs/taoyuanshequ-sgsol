# 桃园 token 续期（免提权版）
# 用当前用户代理 + 用户根证书抓 /v1/wx/login，不改 hosts、不占 443、不弹 UAC。
# 流程：装证书 → 开代理 → 起 mitmdump → 杀小程序进程 → 等新登录 → 写 config → 还原代理

$ErrorActionPreference = 'Continue'
$Root = 'D:\ty_scan'
$Port = 8899
$ProxyKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
$Bak = Join-Path $Root 'proxy_backup.json'
$Cer = Join-Path $env:USERPROFILE '.mitmproxy\mitmproxy-ca-cert.cer'
$Mitm = 'C:\Users\Administrator\AppData\Local\Programs\Python\Python313\Scripts\mitmdump.exe'
if (-not (Test-Path $Mitm)) {
    $Mitm = Join-Path $env:LOCALAPPDATA 'Python\pythoncore-3.14-64\Scripts\mitmdump.exe'
}
$Py = 'C:\Users\Administrator\AppData\Local\Python\pythoncore-3.14-64\python.exe'
if (-not (Test-Path $Py)) { $Py = 'python' }

function Say($msg) { Write-Host ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg) }

function Restore-Proxy {
    if (Test-Path $Bak) {
        try {
            $b = Get-Content $Bak -Raw -Encoding UTF8 | ConvertFrom-Json
            Set-ItemProperty $ProxyKey -Name ProxyEnable -Value ([int]$b.ProxyEnable)
            Set-ItemProperty $ProxyKey -Name ProxyServer -Value ([string]$b.ProxyServer)
            Set-ItemProperty $ProxyKey -Name ProxyOverride -Value ([string]$b.ProxyOverride)
            Say ("代理已还原 Enable={0} Server='{1}'" -f $b.ProxyEnable, $b.ProxyServer)
        } catch { Say "代理还原失败：$_" }
    }
    Get-Process mitmdump -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
}

if (-not (Test-Path $Mitm)) { Say "找不到 mitmdump：$Mitm"; exit 3 }

# 1) 证书（只需装一次，装过就跳过）
$has = certutil -user -store Root 2>$null | Select-String -SimpleMatch 'mitmproxy'
if (-not $has) {
    if (-not (Test-Path $Cer)) { Say "缺 mitmproxy 证书：$Cer（先跑一次 mitmdump 生成）"; exit 3 }
    certutil -user -addstore -f Root $Cer | Out-Null
    Say '已把 mitmproxy 根证书装进当前用户证书库'
} else {
    Say 'mitmproxy 根证书已在用户库中'
}

# 2) 备份并开启代理
$cur = Get-ItemProperty $ProxyKey
if ([string]$cur.ProxyServer -ne "127.0.0.1:$Port") {
    @{
        ProxyEnable   = $cur.ProxyEnable
        ProxyServer   = [string]$cur.ProxyServer
        ProxyOverride = [string]$cur.ProxyOverride
    } | ConvertTo-Json | Set-Content -Path $Bak -Encoding UTF8
}
Set-ItemProperty $ProxyKey -Name ProxyEnable -Value 1
Set-ItemProperty $ProxyKey -Name ProxyServer -Value "127.0.0.1:$Port"
Set-ItemProperty $ProxyKey -Name ProxyOverride -Value ''
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class NetRef {
  [DllImport("wininet.dll", SetLastError=true)]
  public static extern bool InternetSetOption(IntPtr h, int o, IntPtr b, int l);
}
'@
[void][NetRef]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0)
[void][NetRef]::InternetSetOption([IntPtr]::Zero, 37, [IntPtr]::Zero, 0)
Say "代理已开启 127.0.0.1:$Port"

# 3) 起 mitmdump
$jsonl = Join-Path $Root 'clock.jsonl'
$skip = 0
if (Test-Path $jsonl) { $skip = (Get-Content $jsonl | Measure-Object -Line).Lines }
Get-Process mitmdump -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Start-Sleep -Milliseconds 800
Start-Process -FilePath $Mitm -ArgumentList @(
    '-q', '--mode', 'regular', '--listen-host', '127.0.0.1', '--listen-port', "$Port",
    '--set', 'ssl_insecure=true', '-s', (Join-Path $Root 'cap_proxy.py')
) -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $Root 'mitm_u_out.log') `
  -RedirectStandardError (Join-Path $Root 'mitm_u_err.log') | Out-Null
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -EA SilentlyContinue) { break }
}
if (-not (Get-NetTCPConnection -LocalPort $Port -State Listen -EA SilentlyContinue)) {
    Say '!! 代理端口没起来，看 mitm_u_err.log'
    Restore-Proxy
    exit 3
}
Say "mitmdump 就绪，只会读取第 $skip 行之后的新记录"

# 4) 强制小程序冷启动
$n = 0
Get-Process WeChatAppEx -EA SilentlyContinue | ForEach-Object {
    try { Stop-Process -Id $_.Id -Force; $n++ } catch {}
}
Say "已结束 $n 个小程序进程"
Write-Host ''
Write-Host '  >>> 现在去微信里重新打开三国杀OL / 桃园小程序任意页面 <<<' -ForegroundColor Yellow
Write-Host ''

# 5) 等新 token
$ok = $false
for ($i = 0; $i -lt 72; $i++) {
    Start-Sleep -Seconds 3
    & $Py (Join-Path $Root 'apply_token.py') --skip-lines $skip --min-hours 2 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $ok = $true; break }
}
Restore-Proxy

if (-not $ok) {
    Say '3 分钟内没抓到新的 /v1/wx/login —— 小程序没打开，或微信没走系统代理'
    exit 4
}

Say 'token 已写入 config.json'
Remove-Item (Join-Path $Root '.token_warned') -EA SilentlyContinue
& $Py (Join-Path $Root 'taoyuan_daily.py')
& $Py (Join-Path $Root 'check_health.py')
Say '完成'