#!/usr/bin/env bash
# V10: validate real Apple lipo semantics without executing code or opening UI.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import plistlib
from pathlib import Path
assert plistlib.loads(Path('packaging/macos/code-mode.entitlements').read_bytes()) == {
    'com.apple.security.cs.allow-jit': True,
    'com.apple.security.cs.allow-unsigned-executable-memory': True,
}
PY
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
echo 'int main(void) { return 0; }' > "$stage/probe.c"
xcrun clang -arch arm64 -mmacosx-version-min=14.0 "$stage/probe.c" -o "$stage/arm64"
xcrun clang -arch x86_64 -mmacosx-version-min=14.0 "$stage/probe.c" -o "$stage/x86_64"
lipo -create "$stage/arm64" "$stage/x86_64" -output "$stage/universal"
bash scripts/verify-macos-architectures.sh "$stage/universal"
python3 scripts/verify-macos-dependencies.py "$stage/universal"
for arch in arm64 x86_64; do
    if bash scripts/verify-macos-architectures.sh "$stage/$arch" >/dev/null 2>&1; then
        echo "V10: accepted incomplete $arch-only payload" >&2
        exit 1
    fi
done
echo 'int borrowed(void) { return 0; }' > "$stage/borrowed.c"
echo 'extern int borrowed(void); int main(void) { return borrowed(); }' > "$stage/dependent.c"
xcrun clang -arch arm64 -dynamiclib "$stage/borrowed.c" -install_name "$stage/libborrowed.dylib" -o "$stage/libborrowed.dylib"
xcrun clang -arch arm64 "$stage/dependent.c" "$stage/libborrowed.dylib" -o "$stage/dependent"
if python3 scripts/verify-macos-dependencies.py "$stage/dependent" >/dev/null 2>&1; then
    echo 'V10: accepted a machine-local dynamic library' >&2
    exit 1
fi
echo 'PASS V10: universal payload accepted; both single-architecture payloads rejected'
echo 'PASS V10: Apple-system payload accepted; machine-local dylib rejected'
