$ErrorActionPreference = 'Stop'
python scripts/upstream.py prepare
if ($LASTEXITCODE -ne 0) { throw 'Stable upstream source verification failed' }
# These entrypoints are unchanged from the stable release; their backend libraries
# use our root lockfile, never the unrelated full upstream workspace lockfile.
# The CLI/TUI binaries and a separate app-server process are not built.
cargo build --locked --release --target x86_64-pc-windows-msvc -p gui-runtime-helpers --bin codex-code-mode-host --bin codex-windows-sandbox-setup --bin codex-command-runner
if ($LASTEXITCODE -ne 0) { throw 'Runtime helper build failed' }
