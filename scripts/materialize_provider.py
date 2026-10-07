#!/usr/bin/env python3
"""Create a standalone provider crate from stable source plus the catalog-only patch.
Generated sources stay ignored; all other Codex crates remain Git dependencies.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def inline(value):
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        return '[' + ', '.join(map(inline, value)) + ']'
    if isinstance(value, dict):
        return '{ ' + ', '.join(f'{key} = {inline(item)}' for key, item in value.items()) + ' }'
    return str(value)


def materialize():
    pin = json.loads((ROOT / 'upstream.json').read_text())
    stable = ROOT / '.upstream'
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=stable, text=True).strip() == pin['revision']
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=stable, text=True), 'Stable helper tree must stay pristine'
    patch = ROOT / pin['patches'][0]['file']
    # Apply the minimal patch to a temporary copy of only the patched crate.
    temporary = ROOT / '.patched' / 'source'
    source = temporary / 'codex-rs' / 'model-provider'
    if temporary.exists():
        shutil.rmtree(temporary)
    shutil.copytree(stable / 'codex-rs/model-provider', source)
    # No repository discovery: this directory must not inherit product Git state.
    subprocess.run(['git', 'apply', '--check', '--unsafe-paths', '--directory', temporary.as_posix(), patch.as_posix()], cwd=ROOT, check=True)
    subprocess.run(['git', 'apply', '--unsafe-paths', '--directory', temporary.as_posix(), patch.as_posix()], cwd=ROOT, check=True)
    manifest = (source / 'Cargo.toml').read_text()
    upstream = tomllib.loads((stable / 'codex-rs/Cargo.toml').read_text())
    workspace = '\n[workspace]\nresolver = "2"\n\n[workspace.package]\n'
    for key, value in upstream['workspace']['package'].items():
        workspace += f'{key} = {inline(value)}\n'
    workspace += '\n[workspace.dependencies]\n'
    for name in dict.fromkeys(re.findall(r'^([\w-]+) = \{ workspace = true', manifest, re.M)):
        value = upstream['workspace']['dependencies'][name]
        if isinstance(value, dict) and 'path' in value:
            value = {'git': pin['repository'], 'rev': pin['revision']}
        workspace += f'{name} = {inline(value)}\n'
    workspace += '\n[workspace.lints.rust]\n\n[workspace.lints.clippy]\n'
    for name, value in upstream['workspace']['lints']['clippy'].items():
        workspace += f'{name} = {inline(value)}\n'
    # Root patches are necessary when testing this generated crate on its own.
    for table, values in upstream['patch'].items():
        workspace += f'\n[patch.{inline(table)}]\n'
        for name, value in values.items():
            workspace += f'{name} = {inline(value)}\n'
    # Its transitive Git dependencies can themselves refer back to this crate.
    workspace += '\n[patch."https://github.com/openai/codex"]\ncodex-model-provider = { path = "." }\n'
    workspace += '\n[profile.dev]\ndebug = "line-tables-only"\n'
    (source / 'Cargo.toml').write_text(manifest + workspace)
    destination = ROOT / '.patched/codex-model-provider'
    if destination.exists():
        shutil.rmtree(destination)
    shutil.move(source, destination)
    shutil.rmtree(temporary)
    shutil.copy2(ROOT / 'LICENSE', destination / 'LICENSE')
    shutil.copy2(ROOT / 'NOTICE', destination / 'NOTICE')
    stamp = {'revision': pin['revision'], 'patchSha256': hashlib.sha256(patch.read_bytes()).hexdigest()}
    (destination / 'patch-provenance.json').write_text(json.dumps(stamp, indent=2) + '\n')
    print('Materialized stable codex-model-provider with the Bedrock catalog backport')


if __name__ == '__main__':
    materialize()
