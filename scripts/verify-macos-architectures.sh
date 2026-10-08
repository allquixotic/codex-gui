#!/usr/bin/env bash
# Apple's lipo may parse a second -verify_arch argument as another input file.
# Verify each required slice independently using the actual distribution tool.
set -euo pipefail
(( $# > 0 )) || { echo 'Expected at least one Mach-O file' >&2; exit 2; }
for binary in "$@"; do
    /usr/bin/lipo "$binary" -verify_arch arm64
    /usr/bin/lipo "$binary" -verify_arch x86_64
done
