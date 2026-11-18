@echo off
rem Windows setup when the MCP client (the agent) runs on the same PC as ctrlX PLC Engineering.
rem Safe to re-run. Usage: scripts\install_windows.bat [/nopause]
rem
rem Checks Python 3.10+, git, the IDE and (optionally) the claude CLI, then:
rem   1. creates .venv and installs requirements
rem   2. creates scripts\.ctrlx_token if missing (read by start_bridge.bat and by the MCP server)
rem   3. creates scripts\config.bat with TUNNEL=0 if missing
rem   4. checks for the skills the ladder and HMI tools need and prints how to install any that are missing
rem      (it does not install them: that is up to you)
rem   5. registers the MCP server with Claude Code (local scope, this folder only) when the claude CLI is
rem      present, otherwise prints the configuration to add to your MCP client
rem   6. checks that the server imports
rem Skills are looked for in %CTRLX_SKILLS_DIR% or %USERPROFILE%\.claude\skills.
setlocal EnableDelayedExpansion
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "VENVPY=%ROOT%\.venv\Scripts\python.exe"
set "SKILLS_DIR=%CTRLX_SKILLS_DIR%"
if "%SKILLS_DIR%"=="" set "SKILLS_DIR=%USERPROFILE%\.claude\skills"
set "PAUSE=1"
for %%A in (%*) do (
    if /i "%%A"=="/nopause" set "PAUSE=0"
)

echo === Checking what is installed ===

set "PY="
where py >nul 2>nul && py -3 -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && python -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)" >nul 2>nul && set "PY=python"
if not defined PY (
    echo ERROR: Python 3.10 or newer was not found. Install it from python.org ^(tick "Add python.exe to PATH"^) and run this again.
    if "%PAUSE%"=="1" pause
    exit /b 1
)
echo   Python:  %PY%

set "HAVE_GIT=1"
where git >nul 2>nul || set "HAVE_GIT=0"
if "%HAVE_GIT%"=="1" (echo   git:     found) else (echo   git:     NOT FOUND - needed to clone the skills, get it from git-scm.com)

set "HAVE_CLAUDE=1"
where claude >nul 2>nul || set "HAVE_CLAUDE=0"
if "%HAVE_CLAUDE%"=="1" (echo   claude:  found, the server will be registered with Claude Code) else (echo   claude:  not found, fine for another MCP client: a configuration to add to it is printed at the end)

echo.
echo === Python environment ===
if not exist "%VENVPY%" (
    echo Creating .venv ...
    %PY% -m venv "%ROOT%\.venv" || (echo ERROR: could not create the venv. & if "%PAUSE%"=="1" pause & exit /b 1)
)
"%VENVPY%" -m pip install -q -r "%ROOT%\requirements.txt" || (echo ERROR: pip install failed. & if "%PAUSE%"=="1" pause & exit /b 1)
echo   requirements installed

if not exist "%ROOT%\scripts\.ctrlx_token" (
    "%VENVPY%" -c "import secrets; open(r'%ROOT%\scripts\.ctrlx_token','w').write(secrets.token_hex(16))"
    echo   created scripts\.ctrlx_token
)

if not exist "%ROOT%\scripts\config.bat" (
    copy /y "%ROOT%\scripts\config.example.bat" "%ROOT%\scripts\config.bat" >nul
    >>"%ROOT%\scripts\config.bat" echo.
    >>"%ROOT%\scripts\config.bat" echo rem Added by install_windows.bat: the MCP client runs on this PC, so no tunnel.
    >>"%ROOT%\scripts\config.bat" echo set "TUNNEL=0"
    echo   created scripts\config.bat with TUNNEL=0
)

rem The IDE: the path in config.bat, else the ctrlX WORKS install (any version), else the old default
set "IDE_FOUND="
set "IDE_EXE="
call "%ROOT%\scripts\config.bat"
if defined IDE_EXE if exist "!IDE_EXE!" set "IDE_FOUND=!IDE_EXE!"
if not defined IDE_FOUND for /d %%D in ("%ProgramFiles%\ctrlX WORKS\ctrlX PLC Engineering\*") do (
    if exist "%%D\Studio\Common\ctrlX-PLC-Engineering.exe" set "IDE_FOUND=%%D\Studio\Common\ctrlX-PLC-Engineering.exe"
)
if not defined IDE_FOUND if exist "%ProgramFiles%\Bosch Rexroth\ctrlX PLC Engineering\Common\ctrlX PLC Engineering.exe" set "IDE_FOUND=%ProgramFiles%\Bosch Rexroth\ctrlX PLC Engineering\Common\ctrlX PLC Engineering.exe"
echo.
if defined IDE_FOUND (
    echo   IDE:     !IDE_FOUND!
) else (
    echo   IDE:     NOT FOUND - install ctrlX PLC Engineering, or set IDE_EXE in scripts\config.bat
)

echo.
echo === Skills for the ladder and HMI tools ===
rem folder name, then repository. The folder names matter: the converter looks for codesys-lad next to ctrlx-engineer.
set "SK_1=ctrlx-engineer https://github.com/rduffy190/CtrlxPlcSkill"
set "SK_2=codesys-lad https://github.com/rduffy190/CtrlxLadderSkill"
set "SK_3=ctrlx-hmi https://github.com/rduffy190/ctrlx-hmi-skill"

set "MISSING="
for %%N in (1 2 3) do for /f "tokens=1,2" %%A in ("!SK_%%N!") do (
    if exist "%SKILLS_DIR%\%%A\" (
        echo   found    %%A
    ) else (
        echo   MISSING  %%A
        set "MISSING=1"
    )
)
if defined MISSING (
    echo.
    echo   Not installed by this script. The ladder and HMI tools need them; everything else works without.
    echo   To install the missing ones, run ^(into "%SKILLS_DIR%"^):
    for %%N in (1 2 3) do for /f "tokens=1,2" %%A in ("!SK_%%N!") do (
        if not exist "%SKILLS_DIR%\%%A\" echo     git clone %%B "%SKILLS_DIR%\%%A"
    )
    echo   See the README section Required skills.
)

echo.
echo === Registering the MCP server ===
set "REG=no"
if "%HAVE_CLAUDE%"=="1" (
    pushd "%ROOT%"
    call claude mcp remove ctrlx-engineering -s local >nul 2>nul
    call claude mcp add ctrlx-engineering -s local -e CTRLX_BRIDGE_HOST=127.0.0.1 -e CTRLX_BRIDGE_PORT=8765 -- "%VENVPY%" "%ROOT%\server\server.py" && set "REG=yes"
    popd
)
if "%REG%"=="yes" (
    echo   registered with Claude Code ^(local scope, this folder only^)
) else (
    echo   Not registered with a client. Add this to your MCP client's configuration:
)
set "VPJ=%VENVPY:\=\\%"
set "SPJ=%ROOT:\=\\%\\server\\server.py"
if "%REG%"=="no" echo.
if "%REG%"=="no" echo     {
if "%REG%"=="no" echo       "mcpServers": {
if "%REG%"=="no" echo         "ctrlx-engineering": {
if "%REG%"=="no" echo           "command": "%VPJ%",
if "%REG%"=="no" echo           "args": ["%SPJ%"],
if "%REG%"=="no" echo           "env": { "CTRLX_BRIDGE_HOST": "127.0.0.1", "CTRLX_BRIDGE_PORT": "8765" }
if "%REG%"=="no" echo         }
if "%REG%"=="no" echo       }
if "%REG%"=="no" echo     }
if "%REG%"=="no" echo   The token is read from scripts\.ctrlx_token, so the client does not need to set CTRLX_MCP_TOKEN.
if "%REG%"=="no" echo   For Claude Code: claude mcp add ctrlx-engineering -s local -- "%VENVPY%" "%ROOT%\server\server.py"

echo.
echo === Checking the server ===
"%VENVPY%" -c "import sys; sys.path.insert(0, r'%ROOT%\server'); import server; print('  server imports, bridge port', server.PORT)" || echo   ERROR: the server did not import, see above.

echo.
echo Next:
echo   1. Run scripts\start_bridge.bat to start the IDE with the bridge.
echo   2. Restart your MCP client so it picks up the server ^(a new session in Claude Code^), then ask it to ping.
echo   If the client reports a connection error, the server is not registered with Windows paths: .mcp.json in this
echo   folder is for Linux ^(.venv/bin/python^).
if "%PAUSE%"=="1" pause
