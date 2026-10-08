#!/usr/bin/env python3
"""Download upstream V8 binaries, verifying manifests against committed hashes."""
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
pin = json.loads((ROOT / 'upstream.json').read_text())
target = sys.argv[1]
assert target in ('x86_64-pc-windows-msvc', 'aarch64-pc-windows-msvc', 'aarch64-apple-darwin', 'x86_64-apple-darwin', 'x86_64-unknown-linux-gnu')
version = pin['v8']
base = f'https://github.com/openai/codex/releases/download/rusty-v8-v{version}'
profile = 'ptrcomp_sandbox_release'
archive = f'rusty_v8_{profile}_{target}.lib.gz' if 'windows' in target else f'librusty_v8_{profile}_{target}.a.gz'
binding = f'src_binding_{profile}_{target}.rs'
manifest = f'rusty_v8_{profile}_{target}.sha256'
directory = Path(os.environ.get('RUNNER_TEMP', str(ROOT / 'target'))) / 'rusty_v8'
directory.mkdir(parents=True, exist_ok=True)


def download(name):
    path = directory / name
    urllib.request.urlretrieve(f'{base}/{name}', path)
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


trusted = ROOT / 'third_party/v8' / f"rusty_v8_{version.replace('.', '_')}_release_manifests.sha256"
trusted_hashes = {name: checksum for checksum, name in (line.split() for line in trusted.read_text().splitlines())}
manifest_path = download(manifest)
assert digest(manifest_path) == trusted_hashes[manifest], 'V8 checksum manifest was modified'
hashes = {name: checksum for checksum, name in (line.split() for line in manifest_path.read_text().splitlines())}
assert set(hashes) == {archive, binding}, 'Unexpected V8 manifest entries'
for name in (archive, binding):
    path = download(name)
    assert digest(path) == hashes[name], f'V8 digest mismatch: {name}'
values = {'RUSTY_V8_ARCHIVE': str(directory / archive), 'RUSTY_V8_SRC_BINDING_PATH': str(directory / binding)}
if 'GITHUB_ENV' in os.environ:
    with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as output:
        for name, value in values.items():
            output.write(f'{name}={value}\n')
else:
    print(json.dumps(values, indent=2))
