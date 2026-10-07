#!/usr/bin/env python3
"""Validate stable-only pins; fetch pristine source and materialize minimal patches."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/openai/codex'


def run(*args, cwd=ROOT):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'codex-gui-upstream'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def latest():
    release = json.loads(fetch('https://api.github.com/repos/openai/codex/releases/latest'))
    tag = release['tag_name']
    if release['prerelease'] or release['draft'] or not re.fullmatch(r'rust-v\d+\.\d+\.\d+', tag):
        raise SystemExit(f'Refusing non-stable release: {tag}')
    refs = run('git', 'ls-remote', '--tags', REPO, f'refs/tags/{tag}', f'refs/tags/{tag}^{{}}').splitlines()
    revision = next((line.split()[0] for line in refs if line.endswith('^{}')), refs[0].split()[0])
    return tag, revision


def metadata():
    return json.loads((ROOT / 'upstream.json').read_text())


def check(check_latest=False):
    pin = metadata()
    assert pin['repository'] == REPO
    assert re.fullmatch(r'rust-v\d+\.\d+\.\d+', pin['tag'])
    assert pin['tag'] == 'rust-v' + pin['version']
    assert re.fullmatch(r'[0-9a-f]{40}', pin['revision'])
    patched_crates = {patch['crate'] for patch in pin['patches']}
    assert patched_crates <= {'codex-model-provider', 'codex-core'}, 'Review changes to the minimal patch inventory'
    for patch in pin['patches']:
        assert (ROOT / patch['file']).is_file(), patch['file']
    manifest = tomllib.loads((ROOT / 'Cargo.toml').read_text())
    for name, dependency in manifest['workspace']['dependencies'].items():
        if name.startswith('codex-'):
            assert dependency == {'git': REPO, 'rev': pin['revision']}, name
    overrides = manifest.get('patch', {}).get(REPO, {})
    assert set(overrides) == patched_crates, 'Patch inventory must match Cargo overrides'
    for patch in pin['patches']:
        destination = ROOT / '.patched' / patch['crate']
        assert overrides[patch['crate']] == {'path': f".patched/{patch['crate']}"}
        if destination.exists():
            provenance = json.loads((destination / 'patch-provenance.json').read_text())
            assert provenance == {'revision': pin['revision'], 'patchSha256': hashlib.sha256((ROOT / patch['file']).read_bytes()).hexdigest()}, 'Run upstream.py prepare to refresh generated sources'
    helpers = tomllib.loads((ROOT / 'runtime-helpers/Cargo.toml').read_text())
    assert helpers['package']['version'] == pin['version'], 'Helper metadata must match stable backend'
    for binary in helpers['bin']:
        assert binary['path'].startswith('../.upstream/codex-rs/'), 'Helpers must use pristine stable entrypoints'
    lock = tomllib.loads((ROOT / 'Cargo.lock').read_text())
    for package in lock['package']:
        if package['name'].startswith('codex-') and package['name'] != 'codex-gui':
            if package['name'] in patched_crates:
                assert 'source' not in package, 'Patched crate must use the verified generated path'
            else:
                assert package['source'] == f"git+{REPO}?rev={pin['revision']}#{pin['revision']}", package['name']
            assert package['version'] == pin['version'], package['name']
    forbidden = {'codex-cli', 'codex-tui', 'codex-exec'}
    assert not forbidden.intersection(p['name'] for p in lock['package'])
    toolchain = tomllib.loads((ROOT / 'rust-toolchain.toml').read_text())
    assert toolchain['toolchain']['channel'] == pin['rust']
    if check_latest:
        assert (pin['tag'], pin['revision']) == latest(), 'Run python scripts/upstream.py update for latest stable'
    print(f"Codex {pin['tag']} ({pin['revision']}), patch inventory: {sorted(patched_crates)}")


def prepare(validate_lock=True):
    if validate_lock:
        check()
    pin = metadata()
    directory = ROOT / '.upstream'
    directory.mkdir(exist_ok=True)
    if not (directory / '.git').exists():
        run('git', 'init', cwd=directory)
        run('git', 'remote', 'add', 'origin', REPO, cwd=directory)
    run('git', 'fetch', '--depth=1', 'origin', f"refs/tags/{pin['tag']}:refs/tags/{pin['tag']}", cwd=directory)
    revision = run('git', 'rev-parse', f"{pin['tag']}^{{}}", cwd=directory)
    assert revision == pin['revision'], 'Release tag moved; review before accepting'
    run('git', 'checkout', '--detach', pin['revision'], cwd=directory)
    assert not run('git', 'status', '--porcelain', cwd=directory), 'Helper sources must remain pristine'
    if pin['patches']:
        from materialize_upstream import materialize
        materialize()
    print(directory / 'codex-rs' / 'Cargo.toml')


def update():
    previous = metadata()
    tag, revision = latest()
    base = f'https://raw.githubusercontent.com/openai/codex/{revision}'
    stable = tomllib.loads(fetch(base + '/codex-rs/Cargo.toml').decode())
    toolchain_bytes = fetch(base + '/codex-rs/rust-toolchain.toml')
    toolchain = tomllib.loads(toolchain_bytes.decode())
    version = stable['workspace']['package']['version']
    assert tag == 'rust-v' + version
    v8 = stable['workspace']['dependencies']['v8'].removeprefix('=')
    sums = fetch(base + f"/third_party/v8/rusty_v8_{v8.replace('.', '_')}_release_manifests.sha256")
    manifest = (ROOT / 'Cargo.toml').read_text()
    old_revision = metadata()['revision']
    manifest = manifest.replace(f'rev = "{old_revision}"', f'rev = "{revision}"')
    for name, dependency in stable['patch']['crates-io'].items():
        pattern = rf'(?m)^{re.escape(name)} = \{{ git = "[^"]+", rev = "[^"]+" \}}$'
        replacement = f'{name} = {{ git = "{dependency["git"]}", rev = "{dependency["rev"]}" }}'
        manifest, count = re.subn(pattern, lambda _: replacement, manifest)
        assert count, f'Review new upstream patch: {name}'
    (ROOT / 'Cargo.toml').write_text(manifest)
    helper_manifest = ROOT / 'runtime-helpers/Cargo.toml'
    helper_manifest.write_text(helper_manifest.read_text().replace(f'version = "{previous["version"]}"', f'version = "{version}"'))
    (ROOT / 'rust-toolchain.toml').write_bytes(toolchain_bytes)
    (ROOT / 'third_party/v8' / f"rusty_v8_{v8.replace('.', '_')}_release_manifests.sha256").write_bytes(sums)
    pin = dict(repository=REPO, tag=tag, revision=revision, version=version,
               rust=toolchain['toolchain']['channel'], v8=v8, patches=previous['patches'])
    (ROOT / 'upstream.json').write_text(json.dumps(pin, indent=2) + '\n')
    prepare(validate_lock=False)
    subprocess.run(['cargo', 'update', '--workspace'], cwd=ROOT, check=True)
    check()
    print('Review manifest/lockfile, upstream patches and licenses; adapt GUI APIs; run development checks and Windows tests before committing.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'prepare', 'update'])
    parser.add_argument('--latest', action='store_true', help='Verify against GitHub latest stable release')
    options = parser.parse_args()
    if options.action == 'check':
        check(options.latest)
    elif options.action == 'prepare':
        prepare()
    else:
        update()
