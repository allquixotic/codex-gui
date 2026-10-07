param([string]$BuildDirectory = 'target/x86_64-pc-windows-msvc/release')
$ErrorActionPreference = 'Stop'
$version = (Select-String -Path Cargo.toml -Pattern '^version = "([^"]+)"').Matches[0].Groups[1].Value
$directory = "dist/codex-gui-$version-windows-x64"
New-Item -ItemType Directory -Force $directory | Out-Null
$names = @('codex-gui.exe', 'codex-code-mode-host.exe', 'codex-windows-sandbox-setup.exe', 'codex-command-runner.exe')
foreach ($name in $names) {
    $source = Join-Path $BuildDirectory $name
    if (!(Test-Path $source)) { throw "Missing helper or GUI: $source" }
    Copy-Item $source $directory
}
Copy-Item LICENSE, NOTICE, README.md, upstream.json $directory
Copy-Item docs/gui.md "$directory/USER-GUIDE.md"
New-Item -ItemType Directory -Force "$directory/third-party" | Out-Null
Copy-Item third_party/slint/i-slint-core/LICENSES "$directory/third-party/slint" -Recurse
@{ version = $version; commit = $env:GITHUB_SHA; upstream = (Get-Content upstream.json -Raw | ConvertFrom-Json) } | ConvertTo-Json -Depth 5 | Set-Content "$directory/build.json"
$archive = "$directory.zip"
Compress-Archive -Path $directory -DestinationPath $archive -Force
$hash = (Get-FileHash -Algorithm SHA256 $archive).Hash.ToLowerInvariant()
"$hash  $(Split-Path -Leaf $archive)" | Set-Content -Encoding ascii "$archive.sha256"
Write-Output "Packaged $archive ($hash)"
