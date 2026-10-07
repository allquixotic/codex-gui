$ErrorActionPreference = 'Stop'
python scripts/upstream.py prepare
if ($LASTEXITCODE -ne 0) { throw 'Stable upstream source verification failed' }
# These are runtime helpers, built unchanged from the same stable release.
# The CLI/TUI binaries and a separate app-server process are not built.
cargo build --locked --release --target x86_64-pc-windows-msvc --manifest-path .upstream/codex-rs/Cargo.toml -p codex-code-mode-host -p codex-windows-sandbox --bin codex-code-mode-host --bin codex-windows-sandbox-setup --bin codex-command-runner
if ($LASTEXITCODE -ne 0) { throw 'Runtime helper build failed' }
