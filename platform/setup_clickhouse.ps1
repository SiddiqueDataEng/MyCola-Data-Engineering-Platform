# MyCola Platform - ClickHouse Setup Script for Windows
# Handles download, config creation, and launch scripts.

param(
    [string]$InstallDir   = "C:\mycola\clickhouse",
    [int]$MaxMemoryGB     = 4,
    [string]$ExePath      = ""   # Optional: path to a manually downloaded clickhouse.exe
)

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "MyCola - ClickHouse Setup for Windows"    -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

# ── 1. Create directories ─────────────────────────────────────
Write-Host "[1/5] Creating directories..." -ForegroundColor Yellow

$dataDir    = Join-Path $InstallDir "data"
$tmpDir     = Join-Path $InstallDir "tmp"
$logsDir    = Join-Path $InstallDir "logs"
$userFiles  = Join-Path $InstallDir "user_files"
$fmtSchemas = Join-Path $InstallDir "format_schemas"

foreach ($d in @($InstallDir, $dataDir, $tmpDir, $logsDir, $userFiles, $fmtSchemas)) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
        Write-Host "  Created: $d"
    } else {
        Write-Host "  Exists : $d"
    }
}

# ── 2. Locate or download ClickHouse binary ───────────────────
Write-Host ""
Write-Host "[2/5] Locating ClickHouse binary..." -ForegroundColor Yellow

$clickhouseExe = Join-Path $InstallDir "clickhouse.exe"

# If caller supplied a path, copy it
if ($ExePath -and (Test-Path $ExePath)) {
    Copy-Item -Path $ExePath -Destination $clickhouseExe -Force
    Write-Host "  Copied from: $ExePath" -ForegroundColor Green
}

if (-not (Test-Path $clickhouseExe)) {
    # Try packages.clickhouse.com (official stable tgz, extract .exe inside)
    # As of 2024, ClickHouse does not publish a standalone .exe on GitHub releases.
    # The recommended path is: download the Windows installer zip from clickhouse.com
    
    Write-Host ""
    Write-Host "  clickhouse.exe not found at: $clickhouseExe" -ForegroundColor Red
    Write-Host ""
    Write-Host "  ClickHouse no longer distributes a standalone Windows .exe via CDN." -ForegroundColor Yellow
    Write-Host "  Please download it manually using ONE of these methods:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  METHOD A - Recommended: Use pip (Python ClickHouse Local)" -ForegroundColor Cyan
    Write-Host "  ----------------------------------------------------------"
    Write-Host "  pip install clickhouse-driver" -ForegroundColor Green
    Write-Host "  This gives you the Python client. For the server, continue with Method B."
    Write-Host ""
    Write-Host "  METHOD B - Download clickhouse.exe from clickhouse.com" -ForegroundColor Cyan
    Write-Host "  ----------------------------------------------------------"
    Write-Host "  1. Go to: https://clickhouse.com/#getting_started" -ForegroundColor Green
    Write-Host "  2. Click 'Try Now' > Windows"
    Write-Host "  3. Run the installer OR download the .exe directly"
    Write-Host "  4. Copy clickhouse.exe to: $InstallDir"
    Write-Host "  5. Re-run this script:"
    Write-Host "     powershell -ExecutionPolicy Bypass -File '$PSCommandPath'" -ForegroundColor Green
    Write-Host ""
    Write-Host "  METHOD C - Direct download URL (try this)" -ForegroundColor Cyan
    Write-Host "  ----------------------------------------------------------"
    $directUrl = "https://packages.clickhouse.com/windows/clickhouse.exe"
    Write-Host "  Trying: $directUrl"
    try {
        Invoke-WebRequest -Uri $directUrl -OutFile $clickhouseExe -UseBasicParsing
        Write-Host "  Downloaded OK!" -ForegroundColor Green
    } catch {
        Write-Host "  Failed: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Script will continue to create config files." 
        Write-Host "  Add clickhouse.exe to $InstallDir when ready, then run start_server.cmd"
    }
}

if (Test-Path $clickhouseExe) {
    $size = [math]::Round((Get-Item $clickhouseExe).Length / 1MB, 0)
    Write-Host "  Found clickhouse.exe ($size MB)" -ForegroundColor Green
} else {
    Write-Host "  clickhouse.exe missing - config files will still be created." -ForegroundColor Yellow
}

# ── 3. Write config.xml ───────────────────────────────────────
Write-Host ""
Write-Host "[3/5] Writing configuration files..." -ForegroundColor Yellow

$maxMemBytes = $MaxMemoryGB * 1000000000

$configPath = Join-Path $InstallDir "config.xml"
$usersPath  = Join-Path $InstallDir "users.xml"
$logFile    = Join-Path $logsDir "clickhouse-server.log"
$errFile    = Join-Path $logsDir "clickhouse-server.err.log"

$configLines = @(
    "<clickhouse>",
    "    <!-- Memory: capped at ${MaxMemoryGB}GB for 8GB RAM machine -->",
    "    <max_server_memory_usage>$maxMemBytes</max_server_memory_usage>",
    "    <max_server_memory_usage_to_ram_ratio>0.6</max_server_memory_usage_to_ram_ratio>",
    "    <listen_host>::</listen_host>",
    "    <http_port>8123</http_port>",
    "    <tcp_port>9000</tcp_port>",
    "    <mysql_port>9004</mysql_port>",
    "    <path>$dataDir\</path>",
    "    <tmp_path>$tmpDir\</tmp_path>",
    "    <user_files_path>$userFiles\</user_files_path>",
    "    <format_schema_path>$fmtSchemas\</format_schema_path>",
    "    <logger>",
    "        <level>warning</level>",
    "        <log>$logFile</log>",
    "        <errorlog>$errFile</errorlog>",
    "        <size>100M</size>",
    "        <count>3</count>",
    "    </logger>",
    "    <compression>",
    "        <case>",
    "            <min_part_size>10000000</min_part_size>",
    "            <min_part_size_ratio>0.01</min_part_size_ratio>",
    "            <method>lz4</method>",
    "        </case>",
    "    </compression>",
    "</clickhouse>"
)
$configLines | Out-File -FilePath $configPath -Encoding UTF8
Write-Host "  Written: $configPath"

$usersLines = @(
    "<clickhouse>",
    "    <users>",
    "        <default>",
    "            <password></password>",
    "            <networks><ip>::/0</ip></networks>",
    "            <profile>default</profile>",
    "            <quota>default</quota>",
    "        </default>",
    "        <mycola_admin>",
    "            <password>MyCola_2024!</password>",
    "            <networks>",
    "                <ip>::1</ip>",
    "                <ip>127.0.0.1</ip>",
    "            </networks>",
    "            <profile>default</profile>",
    "            <quota>default</quota>",
    "        </mycola_admin>",
    "    </users>",
    "    <profiles>",
    "        <default>",
    "            <max_memory_usage>2000000000</max_memory_usage>",
    "            <use_uncompressed_cache>0</use_uncompressed_cache>",
    "            <load_balancing>random</load_balancing>",
    "        </default>",
    "    </profiles>",
    "    <quotas>",
    "        <default>",
    "            <interval>",
    "                <duration>3600</duration>",
    "                <queries>0</queries>",
    "                <errors>0</errors>",
    "                <result_rows>0</result_rows>",
    "                <read_rows>0</read_rows>",
    "                <execution_time>0</execution_time>",
    "            </interval>",
    "        </default>",
    "    </quotas>",
    "</clickhouse>"
)
$usersLines | Out-File -FilePath $usersPath -Encoding UTF8
Write-Host "  Written: $usersPath"

# ── 4. Write launch batch scripts ─────────────────────────────
Write-Host ""
Write-Host "[4/5] Writing launch scripts..." -ForegroundColor Yellow

$startPath  = Join-Path $InstallDir "start_server.cmd"
$clientPath = Join-Path $InstallDir "client.cmd"

$startLines = @(
    "@echo off",
    "echo ========================================",
    "echo  MyCola ClickHouse Server",
    "echo ========================================",
    "echo  HTTP  : http://localhost:8123",
    "echo  TCP   : localhost:9000",
    "echo  Admin : mycola_admin / MyCola_2024!",
    "echo  Press Ctrl+C to stop.",
    "echo.",
    "cd /d `"$InstallDir`"",
    "`"$clickhouseExe`" server --config-file=`"$configPath`""
)
$startLines | Out-File -FilePath $startPath -Encoding ASCII
Write-Host "  Written: $startPath"

$clientLines = @(
    "@echo off",
    "`"$clickhouseExe`" client --host localhost --port 9000"
)
$clientLines | Out-File -FilePath $clientPath -Encoding ASCII
Write-Host "  Written: $clientPath"

# ── 5. Summary ────────────────────────────────────────────────
Write-Host ""
Write-Host "[5/5] Config files ready." -ForegroundColor Green
Write-Host ""
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "STATUS SUMMARY"                           -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

if (Test-Path $clickhouseExe) {
    Write-Host "clickhouse.exe : FOUND" -ForegroundColor Green
    Write-Host "config.xml     : READY" -ForegroundColor Green
    Write-Host "users.xml      : READY" -ForegroundColor Green
    Write-Host ""
    Write-Host "Run now:"
    Write-Host "  1. $startPath" -ForegroundColor Yellow
    Write-Host "  2. pip install clickhouse-driver pandas pyarrow" -ForegroundColor Yellow
    Write-Host "  3. python F:\siddi\clickstream_sales_analytics\platform\apply_schema.py" -ForegroundColor Yellow
    Write-Host "  4. python F:\siddi\clickstream_sales_analytics\platform\load_data.py" -ForegroundColor Yellow
} else {
    Write-Host "clickhouse.exe : MISSING" -ForegroundColor Red
    Write-Host "config.xml     : READY" -ForegroundColor Green
    Write-Host "users.xml      : READY" -ForegroundColor Green
    Write-Host ""
    Write-Host "ACTION REQUIRED: Get clickhouse.exe first." -ForegroundColor Red
    Write-Host "See instructions printed above (Methods A/B/C)."
}
Write-Host ""
