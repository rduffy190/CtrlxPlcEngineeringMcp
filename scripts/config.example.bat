rem Copy to config.bat and edit. Read by start_bridge.bat (batch "set" lines, keep the quotes).

rem Linux box that runs Claude Code. The tunnel forwards the bridge port there.
rem Use SSH keys (ssh-keygen, then ssh-copy-id) or the tunnel waits for a password.
set "LINUX_USER=your-linux-user"
set "LINUX_HOST=your-linux-host-or-ip"
set "PORT=8765"

rem 0 = no tunnel (Claude Code runs on this machine or you tunnel some other way).
set "TUNNEL=1"

rem ctrlX PLC Engineering executable.
set "IDE_EXE=C:\Program Files\Bosch Rexroth\ctrlX PLC Engineering\Common\ctrlX PLC Engineering.exe"

rem Optional: a .project to open when the bridge starts.
set "PROJECT="

rem 1 = load the bridge when the IDE starts, 0 = load it from Tools > Scripting yourself.
set "AUTORUN=1"
