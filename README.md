# Codex GUI

An independent native desktop front end for Codex, built with [Slint](https://slint.dev).
Tabbed conversations, approvals and questions, file/diff viewers, cross-tab messaging,
provider settings, and inference speed selection run on an embedded Codex app-server.
There is one GUI process and no listening socket by default. Optional daemon and remote
connections remain available.

This community project is maintained by allquixotic. It is a derivative work,
independent of the OpenAI Codex CLI project and not an official OpenAI application.

## Download

Get the Windows x64 ZIP from [Releases](https://github.com/allquixotic/codex-gui/releases).
Extract the whole directory and run `codex-gui.exe`; keep all three helper executables
beside it. Windows builds are also uploaded as artifacts by
[GitHub Actions](https://github.com/allquixotic/codex-gui/actions/workflows/windows.yml)
after every push to `main`. macOS and Linux source builds remain supported;
macOS release builds and signing are deferred.

[GUI.md](GUI.md) is the product specification. [The user guide](docs/gui.md)
explains everyday use; [AGENTS.md](AGENTS.md) describes maintenance.

## Stable upstream dependency

Codex GUI 0.2.0 embeds **Codex 0.161.0**, stable tag `rust-v0.161.0`, pinned to
`979011409de0a60b52f179721948e65531d26144`. `upstream.json`, the Cargo Git dependencies
and `Cargo.lock` record the exact backend. No Codex source patches are required.
The GUI owns its process bootstrap and uses public upstream APIs. It does not build
Codex's CLI, TUI or exec frontend.

The three runtime helpers are built unchanged from that same stable tag by
`scripts/build-helpers.ps1`, using an ignored `.upstream/` checkout. This checkout
is only a build input: product code never lives in or modifies upstream's tree.
The package does not need a separately installed Codex CLI.

Upgrade with `python scripts/upstream.py update`. This selects GitHub's latest stable
release, rejects prereleases, updates immutable pins and toolchain/V8 metadata, and
refreshes the lockfile. Review upstream Cargo patches, licenses, and API changes;
then adapt the GUI and verify before committing. `python scripts/upstream.py check`
validates local pin consistency; `--latest` also verifies the latest stable release.
CI refuses an outdated pin. After a toolchain update, also update the matching
Windows workflow toolchain input. Changes on `main`/`master` are never a dependency target.

## Build and run

On Windows, enable `git config --global core.longpaths true` and use a short
Cargo cache path (for example `$env:CARGO_HOME = 'C:/c'` in PowerShell) if Git
reports a path-length error while checking out upstream. CI sets both.


```bash
cd codex-gui
cargo run -p codex-gui                 # opens the New Tab page
cargo run -p codex-gui -- ~/src/proj   # starts a thread in a folder
cargo run -p codex-gui -- --resume <thread-id>
cargo run -p codex-gui -- --renderer software   # force the CPU renderer
cargo run -p codex-gui -- --remote ws://127.0.0.1:4500   # use an external app-server
```

`codex-gui` is also the `apply_patch` / sandbox helper executable for the
threads it runs (arg0 dispatch happens before any UI code), exactly like the
`codex` multitool.

## Architecture

```
main thread                         Tokio runtime (worker threads)
┌───────────────────────────┐       ┌──────────────────────────────────────┐
│ Slint event loop          │ batch │ backend pump: owns AppServerClient,   │
│ AppController (app.rs)    │◄──────│ drains events, coalesces deltas per   │
│  tabs, feature state,     │ post  │ 16 ms frame, one UI post per batch    │
│  Slint models/globals     │       │                                      │
│ Slint callbacks ──────────┼──────►│ request tasks: Backend::call/fire     │
│   ui_thread::with_app     │ spawn │ embedded app-server + codex-core      │
└───────────────────────────┘       └──────────────────────────────────────┘
```

| Module | Responsibility |
|---|---|
| `main.rs`, `lib.rs` | arg0 dispatch that keeps the main thread for the UI, CLI (`--help` and errors shown without a console on Windows), renderer selection, window-system event hooks, event loop, shutdown |
| `platform.rs` | OS integration Slint lacks: Cmd+Q / Dock › Quit / logout on macOS, the login-shell `PATH` for Finder launches, the app bundle id for notifications, the parent console on Windows, the OpenGL probe on Linux |
| `startup.rs` | embedded app-server startup (config, cloud bundle, environments, state DB, tracing) and restart after provider changes; file logging for startup failures and remote mode |
| `connection.rs` | opt-in daemon (`unix://`) or remote (`ws://`, `wss://`) app-server targets, resolved from `--remote` or Settings › Connection |
| `backend.rs` | `Backend` handle: typed requests, server-request answers, restart, reconnect, shutdown; the event pump and delta coalescing |
| `ui_thread.rs` | access to the UI-thread `AppController` from callbacks (`with_app`) and from Tokio (`post`) |
| `app.rs` | tabs, event routing to features, tab strip, drawers, dialogs, toasts, theme, window lifecycle, command-line startup (sign-in and trust checks) |
| `threads.rs`, `threads/` | thread start/resume/fork/close and the input path (start, steer, or queue a turn); `recap`, `side` chats, `worktree` |
| `session.rs` | request builders for common app-server RPCs |
| `transcript/` | block model, markdown rendering, streaming, paged history, copy/export |
| `composer/` | input, `@` mentions, `/` palette, attachments, file drops, model/effort/permission pickers |
| `approvals/` | approvals, user-input questions, MCP elicitations |
| `settings/` | settings tab: common, schema-driven "all settings", raw TOML, import, account, MCP, skills, plugins, hooks, features, appearance, keyboard, connection, Windows sandbox, diagnostics, feedback; `settings/bedrock` is the providers page (Amazon Bedrock, local models) |
| `files/` | file viewer and diff viewer tabs, find, open externally |
| `sidebar.rs`, `info.rs` + `info/`, `newtab.rs` | thread list, info pane (`info/terminals`: background terminals), new-tab page (folder trust check) |
| `xtab/` | cross-tab messaging tools, mailbox, wait-for-reply |
| `notify.rs` | desktop notifications while the window is in the background |
| `shortcuts.rs` | global keymap (user-overridable) |
| `prefs.rs` | GUI-only preferences in `$CODEX_HOME/gui.json` (invalid values are reported and replaced one by one) |
| `automation.rs` | scripted UI runs for tests (`CODEX_GUI_AUTOMATION`) |
| `ui/*.slint` | one view + one global per feature; `ui/app.slint` places them and re-exports every global |

Rules that keep the UI responsive:

- The UI thread never blocks on I/O. Slint callbacks call
  `ui_thread::with_app(|app| ...)`; work runs through `Backend::call`, whose
  completion closure runs back on the UI thread.
- Every server request (approval, question, dynamic tool call) is answered,
  even on error, so turns never hang.
- Streaming deltas are coalesced per frame in the backend, and the transcript
  only re-renders the unfinished trailing block.

## Testing

```bash
# Safe headless checks on Sean's Mac (never run GUI or rendering tests there):
cargo test --locked --lib -- --skip window_runtime::tests
cargo check --locked --all-targets
cargo clippy --locked --all-targets --no-deps -- -D warnings

# On Windows only: full tests including software-rendered regression fixture.
cargo test --locked --lib
```

GUI launches and GUI tests are prohibited on Sean's Mac. Run the following
end-to-end example on an authorized Windows or other non-Mac test host. It uses a
mock Responses API server and a scripted UI session:

```bash
SP=$(mktemp -d); mkdir -p $SP/home $SP/project
python3 dev/mock_responses.py --port 18080 --write-config $SP/home &
cat > $SP/script.json <<EOF
[{"wait_ready": 60000}, {"new_thread": "$SP/project"}, {"wait_idle": 30000},
 {"send": "markdown please"}, {"wait": 300}, {"wait_idle": 30000},
 {"snapshot": "$SP/shot.png"}, {"quit": true}]
EOF
CODEX_HOME=$SP/home CODEX_GUI_AUTOMATION=$SP/script.json cargo run -p codex-gui
```

The mock's reply depends on the message prefix (`markdown`, `run <cmd>`,
`patch`, `plan`, `ask`, `tab`, `slow`); see the docstring in
`dev/mock_responses.py`. Automation steps are documented in
`src/automation.rs`.

## Packaging

- macOS: `packaging/macos/bundle-app.sh <binary> <out-dir> <version>
  [--bundle-id ID] [--helper PATH]...` builds an unsigned `Codex.app`;
  helpers are copied next to `codex-gui` in `Contents/MacOS`.
- `.github/workflows/windows.yml` builds and tests Windows x64 on hosted
  GitHub runners for pushes to main and pull requests. The ZIP holds `codex-gui` plus the helper
  executables the embedded runtime finds next to it: `codex-code-mode-host`,
  and on Windows `codex-windows-sandbox-setup` and `codex-command-runner`.
  Linux sandboxing uses the system `bwrap` (bubblewrap).
- The window icon is `ui/assets/icon.png`, embedded with `include_bytes!`
  from `src/app.rs` (not a Slint `@image-url`, which would embed the build
  script's absolute path and break Bazel's sandboxed compile).

## License note

Slint is used under the Slint Royalty-free Desktop License 2.0, which requires
the "Made with Slint" attribution: **Help › About Codex** shows the
`AboutSlint` widget. This derivative project uses Apache-2.0, the same license as Codex CLI.
Vendored Slint sources retain their own licenses. The packaged `NOTICE` preserves
upstream attribution; this project has its own informal [contribution guidelines](CONTRIBUTING.md).

Use targeted development checks while implementing. Full release builds wait
until all requested work and relevant checks are complete; macOS release builds
and signing are deferred. For completed packages, `packaging/publish-release.sh`
uploads to an existing GitHub release, verifies SHA-256 asset digests, then cleans
local Cargo outputs and the published packages. See GUI.md §7 for memory and
interaction priorities and when to investigate performance.
