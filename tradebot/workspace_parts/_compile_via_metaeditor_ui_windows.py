from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _compile_via_metaeditor_ui_windows(runtime: Mt5RuntimePaths) -> None:
    """Compile `live.mq5` via the MetaEditor UI on native Windows."""

    source_path = str(runtime.deployed_live_mq5).replace("'", "''")
    metaeditor_path = str(runtime.metaeditor_path).replace("'", "''")
    script = f"""
$ErrorActionPreference = 'Stop'
Get-Process MetaEditor64 -ErrorAction SilentlyContinue | Stop-Process -Force
$sourcePath = '{source_path}'
$metaeditorPath = '{metaeditor_path}'
$ex5Path = [System.IO.Path]::ChangeExtension($sourcePath, '.ex5')
$beforeWrite = if (Test-Path $ex5Path) {{ (Get-Item $ex5Path).LastWriteTimeUtc }} else {{ [datetime]::MinValue }}
$beforeLength = if (Test-Path $ex5Path) {{ (Get-Item $ex5Path).Length }} else {{ -1 }}
$meta = Start-Process -FilePath $metaeditorPath -ArgumentList ('"' + $sourcePath + '"') -PassThru
Start-Sleep -Seconds 6
$ws = New-Object -ComObject WScript.Shell
try {{ [void]$ws.AppActivate('MetaEditor') }} catch {{}}
Start-Sleep -Milliseconds 700
$ws.SendKeys('{{F7}}')
$deadline = (Get-Date).AddSeconds(30)
$compiled = $false
while ((Get-Date) -lt $deadline) {{
    Start-Sleep -Milliseconds 500
    if (Test-Path $ex5Path) {{
        $item = Get-Item $ex5Path
        if ($item.LastWriteTimeUtc -gt $beforeWrite -or $item.Length -ne $beforeLength) {{
            $compiled = $true
            break
        }}
    }}
}}
if ($compiled) {{
    try {{ [void]$ws.AppActivate('MetaEditor') }} catch {{}}
    Start-Sleep -Milliseconds 300
    $ws.SendKeys('%{{F4}}')
    Start-Sleep -Seconds 2
}}
if (Get-Process -Id $meta.Id -ErrorAction SilentlyContinue) {{
    Stop-Process -Id $meta.Id -Force
}}
if (-not $compiled) {{
    throw 'MetaEditor UI fallback did not update live.ex5.'
}}
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
        env=runtime_env(runtime),
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "MetaEditor UI fallback failed while compiling live.mq5.\n"
            f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}"
        )
