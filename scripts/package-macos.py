#!/usr/bin/env python3
"""Sign, notarize and staple the app before its signed/notarized/stapled DMG.

Uses the existing login keychain and AC_NOTARY profile. No private key export,
GUI launches or credential files. Final bytes are ready for Actions attestation.
"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = '9A3CFFC04D3472208A62C48E707EA6D4261998A1'
TEAM = 'B6XDYNLMPU'
PROFILE = os.environ.get('NOTARY_PROFILE', 'AC_NOTARY')
BUNDLE = 'com.allquixotic.codex-gui'


def run(*args, capture=False):
    print('+', ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def notarize(path, evidence, name):
    submission = json.loads(run('xcrun', 'notarytool', 'submit', path,
                                 '--keychain-profile', PROFILE, '--output-format', 'json', capture=True))
    evidence.joinpath(f'{name}-submit.json').write_text(json.dumps(submission, indent=2))
    identifier = submission['id']
    # Preserve the ID immediately. On interruption resume this submission by ID.
    print(f'Notarization submission: {identifier}', flush=True)
    run('xcrun', 'notarytool', 'wait', identifier, '--keychain-profile', PROFILE, '--timeout', '20m')
    info = json.loads(run('xcrun', 'notarytool', 'info', identifier,
                         '--keychain-profile', PROFILE, '--output-format', 'json', capture=True))
    evidence.joinpath(f'{name}-info.json').write_text(json.dumps(info, indent=2))
    log_path = evidence / f'{name}-log.json'
    run('xcrun', 'notarytool', 'log', identifier, '--keychain-profile', PROFILE, log_path)
    log = json.loads(log_path.read_text())
    if info['status'] != 'Accepted' or log['status'] != 'Accepted':
        raise RuntimeError(f'Notarization rejected; inspect {log_path}; do not resubmit unchanged')
    if any(issue.get('severity') == 'error' for issue in log.get('issues') or []):
        raise RuntimeError(f'Notarization errors in {log_path}')
    return identifier


def verify_code(path):
    run('codesign', '--verify', '--deep', '--strict', '--verbose=4', path)
    result = subprocess.run(['codesign', '--display', '--verbose=4', str(path)],
                            check=True, capture_output=True, text=True)
    if f'TeamIdentifier={TEAM}' not in result.stderr or 'runtime' not in result.stderr:
        raise RuntimeError(f'Unexpected team or missing hardened runtime: {path}')


def main():
    if sys.platform != 'darwin':
        raise RuntimeError('macOS signing requires macOS')
    os.chdir(ROOT)
    version = tomllib.loads((ROOT / 'Cargo.toml').read_text())['package']['version']
    commit = os.environ.get('GITHUB_SHA') or run('git', 'rev-parse', 'HEAD', capture=True).strip()
    run(sys.executable, 'scripts/upstream.py', 'check', '--latest')
    identities = run('security', 'find-identity', '-v', '-p', 'codesigning', capture=True)
    if IDENTITY not in identities:
        raise RuntimeError('Pinned 2031 Developer ID Application identity unavailable')
    entitlements = plistlib.loads((ROOT / 'packaging/macos/code-mode.entitlements').read_bytes())
    upstream_entitlements = plistlib.loads((ROOT / '.upstream/.github/scripts/macos-signing/codex-code-mode-host.entitlements.plist').read_bytes())
    if entitlements != upstream_entitlements:
        raise RuntimeError('Review V8 entitlements against the pinned stable upstream helper')
    run('xcrun', 'notarytool', 'history', '--keychain-profile', PROFILE, '--output-format', 'json', capture=True)
    dist = ROOT / 'dist'
    stage = dist / 'macos-stage'
    evidence = dist / 'macos-signing-evidence'
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    evidence.mkdir(parents=True, exist_ok=True)
    run('bash', 'packaging/macos/bundle-app.sh', 'target/universal-release/codex-gui', stage, version,
        '--bundle-id', BUNDLE, '--helper', 'target/universal-release/codex-code-mode-host')
    app = stage / 'Codex GUI.app'
    resources = app / 'Contents/Resources'
    for name in ('LICENSE', 'NOTICE', 'README.md', 'upstream.json'):
        shutil.copy2(ROOT / name, resources / name)
    shutil.copy2(ROOT / 'docs/gui.md', resources / 'USER-GUIDE.md')
    shutil.copytree(ROOT / 'third_party/slint/i-slint-core/LICENSES', resources / 'third-party/slint')
    (resources / 'build.json').write_text(json.dumps({
        'version': version, 'commit': commit, 'architectures': ['arm64', 'x86_64'],
        'upstream': json.loads((ROOT / 'upstream.json').read_text())}, indent=2))
    # Inventory all native payloads; fail closed if the bundle layout changes.
    native = []
    for path in app.rglob('*'):
        if path.is_file() and not path.is_symlink():
            description = run('file', '-b', path, capture=True)
            if 'Mach-O' in description:
                native.append(path)
    expected = {app / 'Contents/MacOS' / name for name in ('codex-gui', 'codex-code-mode-host')}
    if set(native) != expected:
        raise RuntimeError(f'Unexpected native inventory: {native}; review nested signing order')
    for path in sorted(native):
        run('bash', 'scripts/verify-macos-architectures.sh', path)
        run(sys.executable, 'scripts/verify-macos-dependencies.py', path)
        args = ['codesign', '--force', '--timestamp', '--options', 'runtime', '--sign', IDENTITY,
                '--identifier', BUNDLE + '.' + path.name]
        if path.name == 'codex-code-mode-host':
            args += ['--entitlements', 'packaging/macos/code-mode.entitlements']
        run(*args, path)
        verify_code(path)
    run('codesign', '--force', '--timestamp', '--options', 'runtime', '--sign', IDENTITY, app)
    verify_code(app)
    for arch in ('arm64', 'x86_64'):
        run(sys.executable, 'dev/code-mode-signing-smoke.py', app / 'Contents/MacOS/codex-code-mode-host', '--arch', arch)
    temporary_zip = dist / 'macos-app-notary.zip'
    run('ditto', '-c', '-k', '--keepParent', app, temporary_zip)
    app_id = notarize(temporary_zip, evidence, 'app')
    run('xcrun', 'stapler', 'staple', app)
    run('xcrun', 'stapler', 'validate', app)
    verify_code(app)
    run('spctl', '--assess', '--type', 'execute', '--verbose=4', app)
    temporary_zip.unlink()
    # The stapled inner app is now immutable input to the final container.
    (stage / 'Applications').symlink_to('/Applications')
    shutil.copy2(ROOT / 'LICENSE', stage / 'LICENSE.txt')
    dmg = dist / f'codex-gui-{version}-macos-universal.dmg'
    if dmg.exists():
        raise RuntimeError(f'Refusing to overwrite existing distribution {dmg}')
    run('hdiutil', 'create', '-volname', 'Codex GUI', '-srcfolder', stage, '-format', 'UDZO', dmg)
    run('codesign', '--force', '--timestamp', '--sign', IDENTITY, dmg)
    run('codesign', '--verify', '--verbose=4', dmg)
    dmg_id = notarize(dmg, evidence, 'dmg')
    run('xcrun', 'stapler', 'staple', dmg)
    run('xcrun', 'stapler', 'validate', dmg)
    run('codesign', '--verify', '--verbose=4', dmg)
    run('spctl', '--assess', '--type', 'open', '--context', 'context:primary-signature', '--verbose=4', dmg)
    mount = dist / 'macos-verify-mount'
    mount.mkdir(exist_ok=True)
    run('hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', mount, dmg)
    try:
        mounted_app = mount / app.name
        verify_code(mounted_app)
        run('xcrun', 'stapler', 'validate', mounted_app)
        run('spctl', '--assess', '--type', 'execute', '--verbose=4', mounted_app)
        assert plistlib.loads((mounted_app / 'Contents/Info.plist').read_bytes())['CFBundleShortVersionString'] == version
    finally:
        run('hdiutil', 'detach', mount)
    checksum = hashlib.sha256(dmg.read_bytes()).hexdigest()
    dmg.with_suffix('.dmg.sha256').write_text(f'{checksum}  {dmg.name}\n')
    record = {'version': version, 'commit': commit, 'identity_sha1': IDENTITY, 'team_id': TEAM,
              'app_submission': app_id, 'dmg_submission': dmg_id, 'status': 'Accepted',
              'stapling': 'app and DMG validated', 'gatekeeper': 'app, DMG and mounted app accepted',
              'sha256': checksum, 'architectures': ['arm64', 'x86_64']}
    (evidence / 'verification.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
