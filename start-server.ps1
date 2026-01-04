# AI Dungeon Master - Server Startup Script
# This script starts the web server and Cloudflare tunnel, then displays the public URL

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   AI Dungeon Master - Server Start    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to project directory
Set-Location $PSScriptRoot

# Kill any existing processes
Write-Host "Cleaning up old processes..." -ForegroundColor Yellow
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Start the web server in background
Write-Host "Starting web server..." -ForegroundColor Yellow
$webServer = Start-Process -FilePath "python" -ArgumentList "-m", "src.web.server" -PassThru -WindowStyle Hidden
Write-Host "Web server started (PID: $($webServer.Id))" -ForegroundColor Green

# Wait for server to be ready
Start-Sleep -Seconds 3

# Start cloudflared tunnel and capture output
Write-Host "Starting Cloudflare tunnel..." -ForegroundColor Yellow
Write-Host ""

# Create a temp file to capture the URL
$tempFile = [System.IO.Path]::GetTempFileName()

# Start cloudflared and redirect stderr to file (URL is printed to stderr)
$tunnelProcess = Start-Process -FilePath ".\cloudflared.exe" -ArgumentList "tunnel", "--url", "http://localhost:8000" -RedirectStandardError $tempFile -PassThru -WindowStyle Hidden

# Wait for the tunnel to establish and capture URL
$maxWait = 30
$found = $false
for ($i = 0; $i -lt $maxWait; $i++) {
    Start-Sleep -Seconds 1
    $content = Get-Content $tempFile -Raw -ErrorAction SilentlyContinue
    if ($content -match "https://[a-zA-Z0-9-]+\.trycloudflare\.com") {
        $tunnelUrl = $matches[0]
        $found = $true
        break
    }
}

if ($found) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  SERVER IS RUNNING!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Local:  " -NoNewline -ForegroundColor White
    Write-Host "http://localhost:8000" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Public: " -NoNewline -ForegroundColor White
    Write-Host $tunnelUrl -ForegroundColor Magenta
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""

    # Copy to clipboard
    $tunnelUrl | Set-Clipboard
    Write-Host "  (URL copied to clipboard!)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Update your shortlink with this URL" -ForegroundColor White
    Write-Host ""

    # Save URL to file for reference
    $tunnelUrl | Out-File -FilePath ".\current-url.txt" -Encoding UTF8
    Write-Host "  URL also saved to: current-url.txt" -ForegroundColor Gray
} else {
    Write-Host "Could not detect tunnel URL. Check if cloudflared is working." -ForegroundColor Red
    Write-Host "Tunnel process ID: $($tunnelProcess.Id)" -ForegroundColor Yellow
}

# Cleanup temp file
Remove-Item $tempFile -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Press Ctrl+C to stop the server..." -ForegroundColor Gray
Write-Host ""

# Keep script running and handle shutdown
try {
    while ($true) {
        Start-Sleep -Seconds 5
        # Check if processes are still running
        if (-not (Get-Process -Id $webServer.Id -ErrorAction SilentlyContinue)) {
            Write-Host "Web server stopped unexpectedly!" -ForegroundColor Red
            break
        }
    }
} finally {
    Write-Host ""
    Write-Host "Shutting down..." -ForegroundColor Yellow
    Stop-Process -Id $webServer.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $tunnelProcess.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Server stopped." -ForegroundColor Green
}
