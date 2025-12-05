# 1. Determine Python Executable (Force Venv)
if (Test-Path ".\venv\Scripts\python.exe") {
    $pythonExec = ".\venv\Scripts\python.exe"
    Write-Host "Using Virtual Environment Python: $pythonExec" -ForegroundColor Green
}
else {
    $pythonExec = "python"
    Write-Host "Using System Python (Venv not found at .\venv)" -ForegroundColor Yellow
}

# 2. Check if dependencies are installed
# We check for 'socks' (PySocks) which is often needed by requests/huggingface_hub for SOCKS
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:ALL_PROXY = ""

$checkDeps = & $pythonExec -c "try:`n import socks`n import aiohttp_socks`n print('ok')`nexcept ImportError:`n print('missing')" 2>$null

if ($checkDeps.Trim() -ne "ok") {
    Write-Host "Installing missing SOCKS support libraries (including PySocks)..."
    # PySocks is needed for requests/huggingface_hub SOCKS support
    & $pythonExec -m pip install "httpx[socks]" aiohttp-socks PySocks
}
else {
    Write-Host "SOCKS dependencies (httpx, aiohttp, PySocks) already satisfied." -ForegroundColor Green
}

# 3. Check Tor Port
$torPort = 9150
$testConnection = Test-NetConnection -ComputerName localhost -Port $torPort -InformationLevel Quiet

if (-not $testConnection) {
    Write-Host "Warning: Could not connect to Tor on port $torPort (Tor Browser default)." -ForegroundColor Yellow
    Write-Host "Trying port 9050 (Tor Service default)..." -ForegroundColor Yellow
    $torPort = 9050
    $testConnection = Test-NetConnection -ComputerName localhost -Port $torPort -InformationLevel Quiet
    
    if (-not $testConnection) {
        Write-Host "Error: Could not connect to Tor on port 9150 or 9050." -ForegroundColor Red
        Write-Host "Please ensure Tor Browser or Tor Service is running." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Connected to Tor on port $torPort." -ForegroundColor Green

# 4. Set Proxy Env Vars for the Agent
$env:HTTP_PROXY = "socks5h://127.0.0.1:$torPort"
$env:HTTPS_PROXY = "socks5h://127.0.0.1:$torPort"
$env:ALL_PROXY = "socks5h://127.0.0.1:$torPort"

Write-Host "Proxy environment variables set (using socks5h for remote DNS resolution)." -ForegroundColor Cyan

# 5. Run the agent
Write-Host "Starting Agent..." -ForegroundColor Cyan
& $pythonExec agent.py dev
