# Convenience launcher for Windows PowerShell.
param(
    [switch]$Reload = $true
)

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install -e ".[dev]" | Out-Null

if ($Reload) {
    & .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
} else {
    & .\.venv\Scripts\python.exe -m uvicorn app.main:app
}
