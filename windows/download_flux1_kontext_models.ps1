param(
  [string]$ComfyRoot = "D:\AI\ComfyUI",
  [string]$HfToken = $env:HF_TOKEN
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ComfyRoot)) {
  throw "没有找到 ComfyUI：$ComfyRoot。请先运行 启动ComfyUI_FLUX中等占用.bat"
}

$python = Join-Path $ComfyRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

& $python -m pip install --upgrade huggingface_hub
$hf = Join-Path $ComfyRoot ".venv\Scripts\huggingface-cli.exe"
if (-not (Test-Path $hf)) {
  $hf = "huggingface-cli"
}

function Download-HfFile($repo, $file, $targetDir) {
  New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
  $args = @("download", $repo, $file, "--local-dir", $targetDir)
  if ($HfToken) {
    $args += @("--token", $HfToken)
  }
  & $hf @args
}

$diffusionDir = Join-Path $ComfyRoot "models\diffusion_models"
$textDir = Join-Path $ComfyRoot "models\text_encoders"
$vaeDir = Join-Path $ComfyRoot "models\vae"

Download-HfFile "Comfy-Org/flux1-kontext-dev_ComfyUI" "split_files/diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors" $ComfyRoot
New-Item -ItemType Directory -Force -Path $diffusionDir | Out-Null
Move-Item -Force (Join-Path $ComfyRoot "split_files\diffusion_models\flux1-dev-kontext_fp8_scaled.safetensors") (Join-Path $diffusionDir "flux1-dev-kontext_fp8_scaled.safetensors")

Download-HfFile "comfyanonymous/flux_text_encoders" "clip_l.safetensors" $textDir
Download-HfFile "comfyanonymous/flux_text_encoders" "t5xxl_fp8_e4m3fn_scaled.safetensors" $textDir
Download-HfFile "Comfy-Org/Lumina_Image_2.0_Repackaged" "split_files/vae/ae.safetensors" $ComfyRoot
New-Item -ItemType Directory -Force -Path $vaeDir | Out-Null
Move-Item -Force (Join-Path $ComfyRoot "split_files\vae\ae.safetensors") (Join-Path $vaeDir "ae.safetensors")

Write-Host "FLUX.1 Kontext Dev 模型文件已放入 ComfyUI models 目录。"
