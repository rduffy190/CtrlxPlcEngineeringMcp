@echo off
rem Windows setup when Claude Code runs on the same PC as ctrlX PLC Engineering.
rem Safe to re-run. Does:
rem   1. creates .venv and installs requirements
rem   2. creates scripts\.ctrlx_token if missing (read by start_bridge.bat and by the MCP server)
rem   3. creates scripts\config.bat with TUNNEL=0 if missing
rem   4. registers the MCP server with Claude Code (local scope, this folder only)
setlocal
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")

if not exist "%ROOT%\.venv\Scripts\python.exe" (
    echo Creating .venv ...
    %PY% -m venv "%ROOT%\.venv" || (echo Could not create the venv. Install Python 3.10+ first. & pause & exit /b 1)
)
"%ROOT%\.venv\Scripts\python.exe" -m pip install -q -r "%ROOT%\requirements.txt" || (echo pip install failed & pause & exit /b 1)

if not exist "%ROOT%\scripts\.ctrlx_token" (
    "%ROOT%\.venv\Scripts\python.exe" -c "import secrets; open(r'%ROOT%\scripts\.ctrlx_token','w').write(secrets.token_hex(16))"
    echo Created scripts\.ctrlx_token
)

if not exist "%ROOT%\scripts\config.bat" (
    copy /y "%ROOT%\scripts\config.example.bat" "%ROOT%\scripts\config.bat" >nul
    >>"%ROOT%\scripts\config.bat" echo.
    >>"%ROOT%\scripts\config.bat" echo rem Added by install_windows.bat: Claude Code runs on this PC, so no tunnel.
    >>"%ROOT%\scripts\config.bat" echo set "TUNNEL=0"
    echo Created scripts\config.bat with TUNNEL=0
)

where claude >nul 2>nul && (
    pushd "%ROOT%"
    claude mcp remove ctrlx-engineering -s local >nul 2>nul
    claude mcp add ctrlx-engineering -s local -e CTRLX_BRIDGE_HOST=127.0.0.1 -e CTRLX_BRIDGE_PORT=8765 -- "%ROOT%\.venv\Scripts\python.exe" "%ROOT%\server\server.py"
    popd
) || (
    echo.
    echo "claude" not on PATH. Register the server yourself, from this folder:
    echo   claude mcp add ctrlx-engineering -s local -- "%ROOT%\.venv\Scripts\python.exe" "%ROOT%\server\server.py"
)

echo.
echo Next: run scripts\start_bridge.bat, then start Claude Code in %ROOT% and ask it to ping.
pause
