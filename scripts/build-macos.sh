#!/usr/bin/env bash
# Build both supported Mac architectures; headless tests only, never GUI tests.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/upstream.py check --latest
python3 scripts/upstream.py prepare
cargo fmt --all -- --check
rustup target add aarch64-apple-darwin x86_64-apple-darwin
export MACOSX_DEPLOYMENT_TARGET=14.0
# lzma-sys otherwise discovers host package-manager dylibs via pkg-config;
# its supported static switch compiles the bundled codec for each target.
export LZMA_API_STATIC=1
export CARGO_PROFILE_RELEASE_DEBUG=0
export CARGO_PROFILE_RELEASE_LTO=false
export CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-8}"
export CARGO_INCREMENTAL=0
export STABLE_GIT_COMMIT="${GITHUB_SHA:-$(git rev-parse HEAD)}"
for target in aarch64-apple-darwin x86_64-apple-darwin; do
    # Isolated invocation: setup_v8's GITHUB_ENV must not overwrite this job's
    # native build with the second architecture until the next workflow step.
    v8_env="$(env -u GITHUB_ENV python3 scripts/setup_v8.py "$target")"
    export RUSTY_V8_ARCHIVE="$(python3 -c 'import json,sys;print(json.load(sys.stdin)["RUSTY_V8_ARCHIVE"])' <<< "$v8_env")"
    export RUSTY_V8_SRC_BINDING_PATH="$(python3 -c 'import json,sys;print(json.load(sys.stdin)["RUSTY_V8_SRC_BINDING_PATH"])' <<< "$v8_env")"
    if [[ "$target" == aarch64-apple-darwin ]]; then
        cargo test --locked --release --target "$target" --lib -- --skip window_runtime::tests
    fi
    cargo build --locked --release --target "$target" --bin codex-gui
    cargo build --locked --release --target "$target" -p gui-runtime-helpers --bin codex-code-mode-host
    python3 scripts/verify-macos-dependencies.py "target/$target/release/codex-gui" \
        "target/$target/release/codex-code-mode-host"
done
mkdir -p target/universal-release
for binary in codex-gui codex-code-mode-host; do
    lipo -create "target/aarch64-apple-darwin/release/$binary" \
        "target/x86_64-apple-darwin/release/$binary" -output "target/universal-release/$binary"
    bash scripts/verify-macos-architectures.sh "target/universal-release/$binary"
done
