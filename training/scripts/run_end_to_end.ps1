param(
    [string]$Config = "training/configs/rfdetr_medium_recovery.yaml",
    [string]$DatasetDir = "datasets/releases/aadhaar_recovery_v1",
    [string]$DatasetZip = "",
    [string]$Device = "cuda",
    [string]$RunName = "",
    [string]$Python = "python",
    [string]$VenvDir = "venv",
    [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu124",
    [switch]$CpuTorch,
    [switch]$SkipInstall,
    [switch]$DryRunOnly,
    [switch]$SkipDatasetCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [string]$Title,
        [string]$File,
        [string[]]$Arguments
    )

    Write-Host ""
    Write-Host "==> $Title" -ForegroundColor Cyan
    Write-Host "$File $($Arguments -join ' ')" -ForegroundColor DarkGray
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Title"
    }
}

function Get-VenvPython {
    param([string]$VenvPath)

    $candidates = @(
        (Join-Path $VenvPath "Scripts/python.exe"),
        (Join-Path $VenvPath "bin/python")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw "Virtual environment Python was not found in: $VenvPath"
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Push-Location $RepoRoot

try {
    Write-Host "Repo: $RepoRoot" -ForegroundColor Green

    if (!(Test-Path $Config)) {
        throw "Config not found: $Config"
    }

    if (!(Test-Path "requirements.txt")) {
        throw "requirements.txt not found at repo root."
    }

    if ([string]::IsNullOrWhiteSpace($DatasetZip)) {
        if (!(Test-Path $DatasetDir)) {
            throw "Dataset directory not found: $DatasetDir. Put train/valid/test there or pass -DatasetZip path\to\dataset.zip."
        }
    } else {
        if (!(Test-Path $DatasetZip)) {
            throw "Dataset zip not found: $DatasetZip"
        }
    }

    if (!(Test-Path $VenvDir)) {
        Invoke-Step "Create virtual environment" $Python @("-m", "venv", $VenvDir)
    } else {
        Write-Host "Using existing virtual environment: $VenvDir" -ForegroundColor Green
    }

    $VenvPython = Get-VenvPython $VenvDir

    if (!$SkipInstall) {
        Invoke-Step "Upgrade pip tooling" $VenvPython @("-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools")

        if ($CpuTorch) {
            Invoke-Step "Install CPU PyTorch" $VenvPython @("-m", "pip", "install", "torch", "torchvision")
        } else {
            Invoke-Step "Install CUDA PyTorch" $VenvPython @("-m", "pip", "install", "torch", "torchvision", "--index-url", $TorchIndexUrl)
        }

        Invoke-Step "Install project requirements" $VenvPython @("-m", "pip", "install", "-r", "requirements.txt")
    } else {
        Write-Host "Skipping dependency install because -SkipInstall was provided." -ForegroundColor Yellow
    }

    Invoke-Step "Show Python version" $VenvPython @("--version")
    Invoke-Step "Check PyTorch CUDA" $VenvPython @("-c", "import torch; print('torch', torch.__version__); print('cuda_available', torch.cuda.is_available()); print('cuda_devices', torch.cuda.device_count())")

    $DatasetArgs = @("--config", $Config)
    if ([string]::IsNullOrWhiteSpace($DatasetZip)) {
        $DatasetArgs += @("--dataset-dir", $DatasetDir)
    } else {
        $DatasetArgs += @("--dataset-url", $DatasetZip)
    }

    Invoke-Step "Validate dataset" $VenvPython (@("training/prepare_dataset.py") + $DatasetArgs)

    $TrainArgs = @("training/train_rfdetr.py", "--config", $Config, "--device", $Device)
    if ([string]::IsNullOrWhiteSpace($DatasetZip)) {
        $TrainArgs += @("--dataset-dir", $DatasetDir)
    } else {
        $TrainArgs += @("--dataset-url", $DatasetZip)
    }
    if (![string]::IsNullOrWhiteSpace($RunName)) {
        $TrainArgs += @("--run-name", $RunName)
    }
    if ($SkipDatasetCheck) {
        $TrainArgs += @("--skip-dataset-check")
    }

    Invoke-Step "Dry run training setup" $VenvPython ($TrainArgs + @("--dry-run"))

    if ($DryRunOnly) {
        Write-Host ""
        Write-Host "Dry run completed. Training was not started because -DryRunOnly was provided." -ForegroundColor Green
        exit 0
    }

    Invoke-Step "Start training" $VenvPython $TrainArgs
} finally {
    Pop-Location
}
