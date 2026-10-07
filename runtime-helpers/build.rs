// Upstream's library build script scopes these flags to its own setup binary.
// Our consumer owns that binary target, so preserve the same stable manifest here.
fn main() {
    let stable = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../.upstream/codex-rs/windows-sandbox-rs");
    let manifest = stable.join("codex-windows-sandbox-setup.manifest");
    println!("cargo:rerun-if-changed={}", manifest.display());
    println!(
        "cargo:rerun-if-changed={}",
        stable.join("build.rs").display()
    );
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() != Ok("windows") {
        return;
    }
    let binary = "codex-windows-sandbox-setup";
    match (
        std::env::var("CARGO_CFG_TARGET_ENV").as_deref(),
        std::env::var("CARGO_CFG_TARGET_ABI").as_deref(),
    ) {
        (Ok("msvc"), _) => {
            println!("cargo:rustc-link-arg-bin={binary}=/MANIFEST:EMBED");
            println!(
                "cargo:rustc-link-arg-bin={binary}=/MANIFESTINPUT:{}",
                manifest.display()
            );
        }
        (Ok("gnu"), Ok("llvm")) => {
            println!("cargo:rustc-link-arg-bin={binary}=-Wl,-Xlink=/manifest:embed");
            println!(
                "cargo:rustc-link-arg-bin={binary}=-Wl,-Xlink=/manifestinput:{}",
                manifest.display()
            );
        }
        _ => {}
    }
}
