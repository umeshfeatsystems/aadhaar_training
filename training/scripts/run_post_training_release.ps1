param(
    [string]$Config = "training/configs/rfdetr_medium_recovery.yaml",
    [string]$Checkpoint = "checkpoint_best_total.pth",
    [string]$Python = "python",
    [string]$VenvDir = "venv",
    [double]$PackageThreshold = 0.3,
    [double[]]$Thresholds = @(0.1, 0.2, 0.3, 0.35, 0.4, 0.5, 0.6),
    [string]$ReleaseName = "aadhaar_rfdetr_recovery_v1",
    [string]$OutputRoot = "reports/post_training_release",
    [switch]$SkipOcrCheck,
    [switch]$SkipPackage,
    [switch]$NoMaskedSamples
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
    param(
        [string]$VenvPath,
        [string]$FallbackPython
    )

    $candidates = @(
        (Join-Path $VenvPath "Scripts/python.exe"),
        (Join-Path $VenvPath "bin/python")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    Write-Host "Virtual environment not found at '$VenvPath'. Using '$FallbackPython' from PATH." -ForegroundColor Yellow
    return $FallbackPython
}

function Resolve-CheckpointPath {
    param([string]$Path)

    if (Test-Path $Path) {
        return (Resolve-Path $Path).Path
    }

    if ($Path -eq "checkpoint_best_total.pth") {
        $latest = Get-ChildItem -Path "runs" -Recurse -File -Filter "checkpoint_best_total.pth" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1

        if ($null -ne $latest) {
            Write-Host "Default checkpoint was not found in repo root. Using latest run checkpoint:" -ForegroundColor Yellow
            Write-Host $latest.FullName -ForegroundColor Yellow
            return $latest.FullName
        }
    }

    throw "Checkpoint not found: $Path"
}

function Format-ThresholdName {
    param([double]$Value)
    return ($Value.ToString("0.##") -replace "\.", "p")
}

function Write-NextSteps {
    param(
        [string]$Path,
        [string]$EvalDir,
        [string]$SweepDir,
        [string]$ReleaseDir,
        [double]$Threshold
    )

    $content = @"
Post-training outputs
=====================

1. Final test evaluation:
   $EvalDir

   Open metrics.json in this folder and check:
   - overall recall
   - document_level recall
   - document_level fn
   - ocr_post_mask leakage_images

2. Threshold sweep:
   $SweepDir

   Open threshold_sweep_summary.csv.
   Choose the threshold with the lowest false negatives / OCR leakage.
   For Aadhaar masking, recall is usually more important than precision.

3. Release package:
   $ReleaseDir

   Deploy this release folder only after reviewing the metrics and masked samples.
   The script packaged with threshold: $Threshold

If the sweep shows another threshold is better, rerun this script with:

PowerShell:
  .\training\scripts\run_post_training_release.ps1 -PackageThreshold <best_threshold>

Example:
  .\training\scripts\run_post_training_release.ps1 -PackageThreshold 0.2
"@

    Set-Content -Path $Path -Value $content -Encoding UTF8
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Push-Location $RepoRoot

try {
    Write-Host "Repo: $RepoRoot" -ForegroundColor Green

    if (!(Test-Path $Config)) {
        throw "Config not found: $Config"
    }

    $Checkpoint = Resolve-CheckpointPath -Path $Checkpoint

    $VenvPython = Get-VenvPython -VenvPath $VenvDir -FallbackPython $Python
    Invoke-Step "Show Python version" $VenvPython @("--version")

    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $RunOutputRoot = Join-Path $OutputRoot $Stamp
    $EvalThresholdName = Format-ThresholdName $PackageThreshold
    $EvalDir = Join-Path $RunOutputRoot "test_eval_t$EvalThresholdName"
    $SweepDir = Join-Path $RunOutputRoot "threshold_sweep"
    New-Item -ItemType Directory -Force -Path $RunOutputRoot | Out-Null

    $CommonEvalFlags = @()
    if (!$NoMaskedSamples) {
        $CommonEvalFlags += "--save-masked-samples"
    }
    if (!$SkipOcrCheck) {
        $CommonEvalFlags += "--ocr-post-mask-check"
    }

    Invoke-Step "Final test evaluation" $VenvPython (@(
        "training/evaluate_rfdetr.py",
        "--config", $Config,
        "--checkpoint", $Checkpoint,
        "--split", "test",
        "--threshold", $PackageThreshold.ToString(),
        "--output-dir", $EvalDir
    ) + $CommonEvalFlags)

    $ThresholdArgs = @()
    foreach ($threshold in $Thresholds) {
        $ThresholdArgs += $threshold.ToString()
    }

    Invoke-Step "Threshold sweep on test set" $VenvPython (@(
        "training/threshold_sweep.py",
        "--config", $Config,
        "--checkpoint", $Checkpoint,
        "--split", "test",
        "--thresholds"
    ) + $ThresholdArgs + @(
        "--output-dir", $SweepDir
    ) + $CommonEvalFlags)

    $ReleaseDir = ""
    if ($SkipPackage) {
        Write-Host ""
        Write-Host "Skipping package step because -SkipPackage was provided." -ForegroundColor Yellow
    } else {
        Invoke-Step "Package release" $VenvPython @(
            "training/package_model.py",
            "--config", $Config,
            "--checkpoint", $Checkpoint,
            "--metrics", (Join-Path $EvalDir "metrics.json"),
            "--threshold", $PackageThreshold.ToString(),
            "--release-name", $ReleaseName
        )
        $ReleaseDir = Join-Path "model_registry" $ReleaseName
    }

    $NextStepsPath = Join-Path $RunOutputRoot "NEXT_STEPS.txt"
    Write-NextSteps `
        -Path $NextStepsPath `
        -EvalDir $EvalDir `
        -SweepDir $SweepDir `
        -ReleaseDir $ReleaseDir `
        -Threshold $PackageThreshold

    Write-Host ""
    Write-Host "Done." -ForegroundColor Green
    Write-Host "Final test evaluation: $EvalDir" -ForegroundColor Green
    Write-Host "Threshold sweep:       $SweepDir" -ForegroundColor Green
    if (!$SkipPackage) {
        Write-Host "Release package:       $ReleaseDir" -ForegroundColor Green
    }
    Write-Host "Read this file next:   $NextStepsPath" -ForegroundColor Green
} finally {
    Pop-Location
}
