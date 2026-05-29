param(
  [string]$ComfyRoot = "D:\AI\ComfyUI",
  [int]$Port = 8188
)

$ErrorActionPreference = "Stop"

function Find-Executable($names) {
  foreach ($name in $names) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
      return $cmd.Source
    }
  }
  return ""
}

function Get-VramMb {
  $nvidia = Find-Executable @("nvidia-smi.exe")
  if ($nvidia) {
    try {
      $rows = & $nvidia --query-gpu=memory.total --format=csv,noheader,nounits
      foreach ($row in $rows) {
        $value = 0
        if ([int]::TryParse(($row -replace "\D", ""), [ref]$value)) {
          return $value
        }
      }
    } catch {}
  }
  try {
    $controllers = Get-CimInstance Win32_VideoController
    $best = 0
    foreach ($controller in $controllers) {
      if ($controller.AdapterRAM) {
        $best = [Math]::Max($best, [int]($controller.AdapterRAM / 1MB))
      }
    }
    return $best
  } catch {
    return 0
  }
}

function Get-ComfyLaunchArgs {
  $vram = Get-VramMb
  if ($vram -ge 12000) {
    return @("--listen", "127.0.0.1", "--port", "$Port", "--normalvram")
  }
  if ($vram -ge 6000) {
    return @("--listen", "127.0.0.1", "--port", "$Port", "--lowvram")
  }
  return @("--listen", "127.0.0.1", "--port", "$Port", "--cpu")
}

$python = Find-Executable @("python.exe", "py.exe")
$git = Find-Executable @("git.exe")
if (-not $python) {
  throw "未找到 Python。请先安装 Python 3.10+。"
}
if (-not (Test-Path $ComfyRoot)) {
  if (-not $git) {
    throw "未找到 Git，无法自动下载 ComfyUI。"
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $ComfyRoot -Parent) | Out-Null
  & $git clone https://github.com/comfyanonymous/ComfyUI.git $ComfyRoot
}

$venvPython = Join-Path $ComfyRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  & $python -m venv (Join-Path $ComfyRoot ".venv")
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $ComfyRoot "requirements.txt")

$args = Get-ComfyLaunchArgs
Write-Host "ComfyUI 启动参数：$($args -join ' ')"
Start-Process -FilePath $venvPython -ArgumentList @("main.py") + $args -WorkingDirectory $ComfyRoot
