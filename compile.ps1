# compile-mql5.ps1
param([string]$File = "file.mq5")  # relative path supported

$meta = "C:\Program Files\MetaTrader 5\metaeditor64.exe"
$log  = [IO.Path]::ChangeExtension((Resolve-Path $File).Path, ".log")

& $meta /compile:"$File" /log:"$log" /inc:"C:\Users\YourName\AppData\Roaming\MetaQuotes\Terminal\...\MQL5" | Out-Null

# Extremely useful logging
Write-Host "Compiled: $File" -ForegroundColor Cyan
if (Test-Path $log) {
    $content = Get-Content $log -Raw
    if ($content -match "0 error|0 warnings") {
        Write-Host "SUCCESS - 0 errors, 0 warnings" -ForegroundColor Green
    } else {
        Write-Host "FAILED" -ForegroundColor Red
    }
    $content | Out-Host
} else {
    Write-Host "No log file generated" -ForegroundColor Red
}