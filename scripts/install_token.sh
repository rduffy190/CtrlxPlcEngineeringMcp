#!/usr/bin/env bash
# Make CTRLX_MCP_TOKEN permanent: create .ctrlx_token if missing and load it from ~/.bashrc.
# Safe to re-run. Usage: scripts/install_token.sh [rcfile]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOKEN_FILE="$ROOT/.ctrlx_token"
RC="${1:-$HOME/.bashrc}"
BEGIN="# >>> ctrlx-mcp token >>>"
END="# <<< ctrlx-mcp token <<<"

if [ ! -s "$TOKEN_FILE" ]; then
    (umask 077; openssl rand -hex 16 > "$TOKEN_FILE")
    echo "created $TOKEN_FILE"
fi
chmod 600 "$TOKEN_FILE"

touch "$RC"
if grep -qF "$BEGIN" "$RC"; then
    # replace the existing block so a moved project path stays correct
    sed -i "/$BEGIN/,/$END/d" "$RC"
fi
cat >> "$RC" <<BLOCK
$BEGIN
export CTRLX_MCP_TOKEN=\$(cat "$TOKEN_FILE")
$END
BLOCK

echo "installed in $RC"
echo "token (use the same value on Windows): $(cat "$TOKEN_FILE")"
echo "open a new terminal, or run: source $RC"
