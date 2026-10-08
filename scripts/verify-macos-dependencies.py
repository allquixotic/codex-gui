#!/usr/bin/env python3
"""Reject machine-local dynamic dependencies in distributable Mach-O code."""
import subprocess
import sys

if len(sys.argv) < 2:
    raise SystemExit('Expected at least one Mach-O file')
for path in sys.argv[1:]:
    dependencies = subprocess.check_output(['otool', '-L', path], text=True)
    unsupported = [line.strip().split(' (')[0] for line in dependencies.splitlines()
                   if line.startswith('\t') and not line.strip().startswith(('/System/Library/', '/usr/lib/'))]
    if unsupported:
        raise SystemExit(f'Non-system dynamic dependencies in {path}: {unsupported}')
    print(f'PASS V10: {path} links only Apple system libraries')
