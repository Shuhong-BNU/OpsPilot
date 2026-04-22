@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

echo ====================================
echo Start OpsPilot Services
echo ====================================
echo.

echo [1/8] Check package manager...
where uv >nul 2>&1
if errorlevel 1 (
    echo [INFO] uv was not found. Falling back to pip.
    echo [TIP] Install uv for faster setup: pip install uv
    set "USE_UV=0"
) else (
    echo [OK] uv detected.
    set "USE_UV=1"
)
echo.

echo [2/8] Check Python version marker...
if exist .python-version (
    set /p PYTHON_VERSION=<.python-version
    echo [INFO] Current .python-version: !PYTHON_VERSION!
    echo !PYTHON_VERSION! | findstr /C:"3.10" >nul
    if not errorlevel 1 (
        echo [WARN] Python 3.10 is not recommended. Updating marker to 3.13...
        > .python-version echo 3.13
        echo [OK] .python-version updated to 3.13
    )
) else (
    echo [INFO] Creating .python-version...
    > .python-version echo 3.13
)
echo.

echo [3/8] Prepare virtual environment...
if exist .venv\Scripts\python.exe (
    echo [INFO] Existing virtual environment found.
    if "%USE_UV%"=="1" (
        uv sync 2>nul
        if errorlevel 1 (
            echo [WARN] uv sync failed. Updating with pip instead...
            .venv\Scripts\python.exe -m pip install -e . -q
        ) else (
            echo [OK] Dependencies synced with uv.
        )
    ) else (
        echo [INFO] Updating dependencies with pip...
        .venv\Scripts\python.exe -m pip install -e . -q
    )
) else (
    echo [INFO] Creating a new virtual environment...
    if "%USE_UV%"=="1" (
        uv sync 2>nul
        if not errorlevel 1 (
            echo [OK] Virtual environment created with uv.
            goto :venv_ready
        )
        echo [WARN] uv sync failed. Falling back to python -m venv...
    )

    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        echo [TIP] Make sure Python 3.11+ is installed and available in PATH.
        pause
        exit /b 1
    )

    echo [INFO] Installing project dependencies...
    .venv\Scripts\python.exe -m pip install --upgrade pip -q
    .venv\Scripts\python.exe -m pip install -e . -q
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

:venv_ready
echo [OK] Virtual environment is ready.
echo.

set "PYTHON_CMD=.venv\Scripts\python.exe"
set "CAN_INDEX_DOCS=1"

if not exist logs mkdir logs

if exist .env (
    findstr /R /C:"^DASHSCOPE_API_KEY=$" /C:"^DASHSCOPE_API_KEY=your-api-key$" /C:"^DASHSCOPE_API_KEY=your-api-key-here$" .env >nul 2>&1
    if not errorlevel 1 (
        set "CAN_INDEX_DOCS=0"
    )
)

echo [4/8] Start Milvus...
docker ps --format "{{.Names}}" | findstr "milvus-standalone" >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Milvus container is already running.
) else (
    docker compose -f vector-database.yml up -d
    if errorlevel 1 (
        echo [ERROR] Failed to start Docker services. Make sure Docker Desktop is running.
        pause
        exit /b 1
    )
    echo [INFO] Waiting for Milvus to become ready...
    timeout /t 10 /nobreak >nul
)
echo [OK] Milvus is ready.
echo.

echo [5/8] Start CLS MCP service...
start "CLS MCP Server" /min cmd /c "\"%PYTHON_CMD%\" \"mcp_servers\cls_server.py\" > logs\mcp_cls.log 2>&1"
timeout /t 2 /nobreak >nul
echo [OK] CLS MCP service started.
echo.

echo [6/8] Start Monitor MCP service...
start "Monitor MCP Server" /min cmd /c "\"%PYTHON_CMD%\" \"mcp_servers\monitor_server.py\" > logs\mcp_monitor.log 2>&1"
timeout /t 2 /nobreak >nul
echo [OK] Monitor MCP service started.
echo.

echo [7/8] Start FastAPI service...
start "OpsPilot API" "%PYTHON_CMD%" -m uvicorn app.main:app --host 0.0.0.0 --port 9900
echo [INFO] Waiting for API startup...
timeout /t 15 /nobreak >nul
echo.

echo [8/8] Check API and upload default docs...
curl -s http://localhost:9900/health >nul 2>&1
if errorlevel 1 (
    echo [WARN] API may still be starting. Please wait a little longer and retry if needed.
) else (
    echo [OK] FastAPI service is responding.
    set "AUTH_TOKEN="
    for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$json = '{\"username\":\"operator\",\"password\":\"operator123\"}'; try { $resp = Invoke-RestMethod -Uri 'http://localhost:9900/api/auth/login' -Method Post -ContentType 'application/json' -Body $json; Write-Output $resp.access_token } catch { Write-Output '' }"`) do (
        set "AUTH_TOKEN=%%i"
    )

    if "%CAN_INDEX_DOCS%"=="0" (
        echo [WARN] DASHSCOPE_API_KEY is still a placeholder. Skipping default document upload.
        echo [TIP] Set a real key in .env, then re-run start-windows.bat or upload docs manually.
    ) else if defined AUTH_TOKEN (
        for %%f in (aiops-docs\*.md) do (
            echo [INFO] Uploading %%~nxf ...
            curl -s -X POST http://localhost:9900/api/upload -H "Authorization: Bearer !AUTH_TOKEN!" -F "file=@%%f" >nul 2>&1
        )
        echo [OK] Default knowledge documents uploaded.
    ) else (
        echo [WARN] Failed to obtain operator token. Document upload was skipped.
    )
)

echo.
echo ====================================
echo OpsPilot startup finished
echo ====================================
echo Listen address: http://0.0.0.0:9900
echo Browser URL: http://localhost:9900
echo API docs: http://localhost:9900/docs
echo Health: http://localhost:9900/health
echo Metrics: http://localhost:9900/metrics
echo.
echo Logs:
echo   - FastAPI: logs\app_*.log
echo   - CLS MCP: logs\mcp_cls.log
echo   - Monitor MCP: logs\mcp_monitor.log
echo Stop services: stop-windows.bat
echo ====================================
pause
