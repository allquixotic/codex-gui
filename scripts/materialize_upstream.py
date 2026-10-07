#!/usr/bin/env python3
"""Create standalone crates from stable source plus minimal Bedrock tier patches.
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
    upstream = tomllib.loads((stable / 'codex-rs/Cargo.toml').read_text())
    temporary = ROOT / '.patched' / 'source'
    if temporary.exists():
        shutil.rmtree(temporary)
    for item in pin['patches']:
        name = item['crate']
        relative = Path(upstream['workspace']['dependencies'][name]['path'])
        source = temporary / 'codex-rs' / relative
        shutil.copytree(stable / 'codex-rs' / relative, source)
        patch = ROOT / item['file']
        subprocess.run(['git', 'apply', '--check', '--unsafe-paths', '--directory', temporary.as_posix(), patch.as_posix()], cwd=ROOT, check=True)
        subprocess.run(['git', 'apply', '--unsafe-paths', '--directory', temporary.as_posix(), patch.as_posix()], cwd=ROOT, check=True)
        manifest = (source / 'Cargo.toml').read_text()
        # Some crates declare internal path dependencies directly rather than via workspace.
        def git_dependency(match):
            package = re.search(r'package = "([^"\n]+)"', match.group())
            fields = {'git': pin['repository'], 'rev': pin['revision']}
            if package:
                fields['package'] = package[1]
            return match[1] + ' = ' + inline(fields)
        manifest = re.sub(r'(?m)^([\w-]+) = \{ [^}\n]*path = "[^"\n]+"[^}\n]*\}', git_dependency, manifest)
        workspace = '\n[workspace]\nresolver = "2"\n\n[workspace.package]\n'
        for key, value in upstream['workspace']['package'].items():
            workspace += f'{key} = {inline(value)}\n'
        workspace += '\n[workspace.dependencies]\n'
        for dependency in dict.fromkeys(re.findall(r'^([\w-]+) = \{ workspace = true', manifest, re.M)):
            value = upstream['workspace']['dependencies'][dependency]
            if isinstance(value, dict) and 'path' in value:
                value = {key: val for key, val in value.items() if key != 'path'}
                value.update(git=pin['repository'], rev=pin['revision'])
            workspace += f'{dependency} = {inline(value)}\n'
        workspace += '\n[workspace.lints.rust]\n\n[workspace.lints.clippy]\n'
        for lint, value in upstream['workspace']['lints']['clippy'].items():
            workspace += f'{lint} = {inline(value)}\n'
        for table, values in upstream['patch'].items():
            workspace += f'\n[patch.{inline(table)}]\n'
            for dependency, value in values.items():
                workspace += f'{dependency} = {inline(value)}\n'
        workspace += '\n[patch."https://github.com/openai/codex"]\n'
        for other in pin['patches']:
            location = '.' if other['crate'] == name else '../' + other['crate']
            workspace += f"{other['crate']} = {{ path = {inline(location)} }}\n"
        workspace += '\n[profile.dev]\ndebug = "line-tables-only"\n'
        (source / 'Cargo.toml').write_text(manifest + workspace)
        destination = ROOT / '.patched' / name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(source, destination)
        shutil.copy2(ROOT / 'LICENSE', destination / 'LICENSE')
        shutil.copy2(ROOT / 'NOTICE', destination / 'NOTICE')
        stamp = {'revision': pin['revision'], 'patchSha256': hashlib.sha256(patch.read_bytes()).hexdigest()}
        (destination / 'patch-provenance.json').write_text(json.dumps(stamp, indent=2) + '\n')
        print(f'Materialized stable {name} with the Bedrock tier backport')
    shutil.rmtree(temporary)


if __name__ == '__main__':
    materialize()
