@echo off
rem Starts the SSH tunnel to the Linux box and ctrlX PLC Engineering with the MCP bridge loaded.
rem
rem Setup: copy scripts\config.example.bat to scripts\config.bat and edit it, and put the shared
rem token (the Linux box's .ctrlx_token, made by scripts/install_token.sh) in scripts\.ctrlx_token.
rem
rem The bridge script returns at once, so the IDE finishes loading and stays usable.
rem If loading it at startup misbehaves, set AUTORUN=0 in config.bat and run it from the menu:
rem   Tools > Scripting > Execute Script File   (the path is copied to the clipboard)

setlocal
set "HERE=%~dp0"

rem ---- defaults, overridden by config.bat ----------------------------------------------------
set "PORT=8765"
set "IDE_EXE=C:\Program Files\Bosch Rexroth\ctrlX PLC Engineering\Common\ctrlX PLC Engineering.exe"
set "TUNNEL=1"
set "LINUX_USER="
set "LINUX_HOST="
set "PROJECT="
set "AUTORUN=1"
set "TOKEN_FILE=%HERE%.ctrlx_token"
if exist "%HERE%config.bat" call "%HERE%config.bat"
rem --------------------------------------------------------------------------------------------

set "BRIDGE=%HERE%..\bridge\bridge.py"

if not exist "%IDE_EXE%" (echo IDE not found: %IDE_EXE% & echo Set IDE_EXE in scripts\config.bat. & pause & exit /b 1)
if not exist "%BRIDGE%" (echo bridge.py not found: %BRIDGE% & pause & exit /b 1)
if not exist "%TOKEN_FILE%" (echo Token file missing: %TOKEN_FILE% & echo Put the token from the Linux box's .ctrlx_token in it. & pause & exit /b 1)
if "%TUNNEL%"=="1" if "%LINUX_USER%%LINUX_HOST%"=="" (echo Set LINUX_USER and LINUX_HOST in scripts\config.bat, or TUNNEL=0. & pause & exit /b 1)

rem Resolve BRIDGE to a clean absolute path (no "..").
for %%I in ("%BRIDGE%") do set "BRIDGE=%%~fI"

set /p CTRLX_MCP_TOKEN=<"%TOKEN_FILE%"
set "CTRLX_MCP_PORT=%PORT%"
set "CTRLX_MCP_PROJECT=%PROJECT%"

if "%TUNNEL%"=="1" (
    rem Own window; closes with Ctrl+C. Exits if the forward fails (for example the port is taken).
    start "ctrlX MCP tunnel" ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -R %PORT%:127.0.0.1:%PORT% %LINUX_USER%@%LINUX_HOST%
)

if "%AUTORUN%"=="1" (
    echo Starting PLC Engineering with the bridge ...
    start "" "%IDE_EXE%" --runscript="%BRIDGE%"
    echo.
    echo When the IDE has loaded, the bridge log should say "loop started":
    echo   %%TEMP%%\ctrlx_bridge.log
) else (
    <nul set /p "=%BRIDGE%" | clip
    echo Starting PLC Engineering ...
    start "" "%IDE_EXE%"
    echo.
    echo When the IDE has loaded:
    echo   Tools ^> Scripting ^> Execute Script File, paste the path ^(already on the clipboard^):
    echo   %BRIDGE%
)
echo.
pause
