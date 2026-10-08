# Signed releases

Windows main-push builds use GitHub-hosted runners, Azure OIDC login and the
`allquixotic-signing/windows-public` certificate profile. PR builds remain
unsigned. Verify all four EXEs with `Get-AuthenticodeSignature`: status `Valid`,
publisher `CN=Sean McNamara, O=Sean McNamara, L=Pasadena, S=MD, C=US`, and a
timestamp certificate. Packaging follows signing; the ZIP is then attested.

Mac releases use `.github/workflows/macos-release.yml`, dispatched on main
only, and a temporary ARM64 Mac Actions runner labeled `codex-gui-signing`.
Register it with `--ephemeral --disableupdate`, run it interactively for one
job, and confirm GitHub removes it afterward. Do not install a runner service
or export private keys. The runner checkout is separate from the working repo.
Only register/dispatch this runner for an explicitly requested release.

The Mac must have Xcode tools, Python 3.11+, Rust 1.95.0, the two Mac Rust
targets, the pinned 2031 Application signing identity/private key, and the
`AC_NOTARY` keychain profile. `scripts/build-macos.sh` builds a universal
arm64/x86_64 GUI plus the pristine upstream code-mode helper for macOS 14+.
Mac tests explicitly skip `window_runtime::tests`; never launch the GUI there.

`scripts/package-macos.py` inventories native code, rejects non-system dynamic
dependencies, signs the helper and GUI inside out, and enables hardened runtime.
Only the V8 helper receives `com.apple.security.cs.allow-jit`; no blanket memory,
library-validation or debugger entitlements. An IPC smoke test runs JavaScript
in that signed helper without starting the GUI. Sign with Application SHA-1
`9A3CFFC04D3472208A62C48E707EA6D4261998A1`, team `B6XDYNLMPU`, expiring
September 17, 2031; never select an ambiguous certificate by name. No PKG is built.

The script notarizes a temporary app ZIP, records its submission ID and checks
Apple's Accepted status and log. It staples and validates the app and passes
Gatekeeper before constructing the DMG. It then signs, notarizes, staples and
assesses the DMG, mounting it read-only with `-nobrowse` to verify the contained
app's signature, ticket and version. Evidence contains public metadata only.
If interrupted, use `notarytool info/wait/log` with the recorded submission ID;
never upload an unchanged rejected artifact again.

GitHub's pinned `actions/attest` creates build provenance for each final ZIP/DMG,
after all platform signing/stapling. Both workflows export Sigstore bundles;
retain them beside release packages for offline verification. Attestations
prove workflow/source provenance; platform signatures identify the publisher.
Checksums are computed after all mutations. Do not claim a self-hosted build
has the isolation guarantees of a GitHub-hosted runner.

Before publication, download artifacts from successful runs of the exact same
commit and verify checksums, build.json version/upstream/commit, platform
signatures and provenance:

```sh
gh attestation verify codex-gui-VERSION-windows-x64.zip --repo allquixotic/codex-gui
gh attestation verify codex-gui-VERSION-macos-universal.dmg --repo allquixotic/codex-gui
```

Also constrain verification to the expected source digest and signer workflow
using `--source-digest` and `--signer-workflow`. Save verified JSON with
`--format json`. Mac provenance uses a self-hosted runner: do not require the
`--deny-self-hosted-runners` policy for that package. Verify the Windows package
with that policy. Test the signed Windows package on Windows, never on the Mac.

Create a draft release pinned to the successful full SHA, upload both packages,
checksums and platform Sigstore bundles, and verify GitHub asset digests against
local bytes before publishing. Recheck latest stable upstream. Remove temporary
runner registration/credentials; clean only this project's regenerable build
outputs after all assets are verified. Preserve signing/notarization evidence.
