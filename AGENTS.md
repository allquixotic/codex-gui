# Codex GUI maintenance

This independent Apache-2.0 project embeds Codex and owns its Slint GUI. It is
not the Codex CLI project. Preserve `GUI.md` as our product specification and
all working features; `SPEC.md` records focused invariants and regressions.

## Upstream policy

- Always target GitHub's latest **stable** `openai/codex` release. Never consume
  upstream main/master, a development branch, or a prerelease.
- `upstream.json` is the pin inventory. All Codex Git dependencies and lockfile
  entries must match its full commit and stable version. Run
  `python scripts/upstream.py check --latest` before publishing.
- Update with `python scripts/upstream.py update`; review release API changes,
  Cargo transport patches, toolchain, V8 digests, lockfile, and license notices.
  CI's toolchain input must also match `rust-toolchain.toml` after an update.
- Prefer public upstream APIs and GUI-side adapters. The Bedrock backport has
  two small patches: provider catalogs and the core request builder. `patches/`
  is the inventory; `.patched/` is ignored generated source. Before Cargo commands,
  run `python scripts/upstream.py prepare`. For each patch document its stable base,
  reason, application/verification process and removal condition, keep it minimal,
  and update pin validation consistently. Remove the backport when a stable release
  provides it and V5 native provider tests pass. Helpers stay pristine. Never restore a fork.
- `.upstream/` is ignored, pristine stable source for runtime helpers and
  materializing the backport. Do not add product code there or commit its contents.
- The Slint vendor directory carries a wrapped-link fix and narrow rich-text
  selection/cursor bridges; see third_party/slint/README.md. Preserve licenses.
  Remove each change only when upstream public APIs cover it and Windows
  rendering/link/selection tests verify it. GUI crates do not link CLI/TUI/exec frontends.

## Development and verification

- Never launch this project's GUI, open test windows, or run GUI/rendering tests
  on Sean's Mac. Only the exact instruction "test the GUI on this Mac" overrides
  this. Requests to build, fix, verify, commit, push or release do not.
- Safe Mac checks: `cargo fmt --all -- --check`, `cargo check --locked --all-targets`,
  `cargo test --locked --lib -- --skip window_runtime::tests`, and
  `cargo clippy --locked --all-targets --no-deps -- -D warnings`.
- Use Windows for rendering/interaction tests. Sean's `games` or `avd` tailnet
  hosts are available through SSH; read their AGENTS.md before remote changes.
  Hosted Windows CI also runs the complete software-rendered unit fixture.
- Run targeted checks during development. Full release builds follow completed
  source changes and development verification. Defer Mac release builds/signing.
- Keep UI-thread callbacks free of blocking I/O; use the existing backend pump
  and typed requests. Keep transcript virtualization and memory limits.
- Purpose summaries consume completed user requests only; use the existing fast
  model selector with normal-model fallback. Never persist their temporary
  conversations, overwrite manual names, or summarize assistant/tool output.
  Cache results in resolved CODEX_HOME; debounce visible-row resize updates ten
  seconds using cached tooltips only. Preserve restart/stale-result safeguards
  and sticky manual-name history when changing the cache format.
- Conversation selection must follow shaped glyphs, wrapping, clipping and UTF-8
  graphemes. Keep native text input selection and rich links working. Run both
  dev/windows-smoke.py and dev/windows-purpose-selection-smoke.py on Windows.
- Answer every synchronous server request exactly once. Async questions use
  ordinary user messages and remain answerable after the requesting turn ends.
- Use supported RTK filters when they reduce verbose output; machine-readable
  commands, scripts and concise commands run directly. Use `rg` first for search.
- Agentlocks is retired: never invoke, repair or install it, including hooks.
  Coordinate one writer per file using the harness when delegation is explicitly
  requested; preserve unrelated work.

## Distribution

- `.github/workflows/windows.yml` builds Windows x64 ZIP/SHA-256 artifacts on
  pushes to `main` and pull requests. Keep it usable on ordinary hosted runners.
  Hosted Windows release builds disable whole-program LTO and use 16 codegen
  units to bound compilation time/memory; ordinary release optimization and
  static backend linking remain enabled. Keep the short Windows Cargo cache
  path and Git `core.longpaths` setting:
  Cargo checks out upstream's long snapshot filenames even without linking TUI.
- Ship `codex-gui.exe`, `codex-code-mode-host.exe`,
  `codex-windows-sandbox-setup.exe` and `codex-command-runner.exe` together.
  Helpers must use the same stable backend as the GUI. `runtime-helpers/Cargo.toml`
  compiles pristine upstream entrypoints using our root lockfile and exact Git
  dependencies. Never build against the full upstream workspace lockfile.
  Preserve the setup helper’s scoped asInvoker manifest in runtime-helpers/build.rs.
  Keep helper package version/source paths, manifest link flags and Windows API features in sync
  when updating the stable backend.
- Keep Apache LICENSE, upstream attribution in NOTICE, third-party licenses,
  user guide and exact build/pin metadata in packages.
- Publish from a successful workflow for the exact commit; verify GitHub asset
  digests before deleting local artifacts/build outputs. Do not commit target,
  dist, cached upstream sources or machine-specific credentials.
- Contributions are informal; see CONTRIBUTING.md. Do not copy upstream's CLA,
  organization-specific workflows or assume direct affiliation.
