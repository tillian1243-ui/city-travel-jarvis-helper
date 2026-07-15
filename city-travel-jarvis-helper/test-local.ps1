$ErrorActionPreference="Stop"
if(-not(Test-Path .venv)){python -m venv .venv}
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
$env:STORAGE_MODE="memory";$env:WRITES_ENABLED="true";$env:ACTION_API_KEY="local-city-key";$env:PREVIEW_SIGNING_SECRET="local-city-preview-secret"
pytest -q
