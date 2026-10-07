// No console window on Windows; errors are shown in a message box and logged.
#![cfg_attr(windows, windows_subsystem = "windows")]

use std::time::Duration;

fn main() -> anyhow::Result<()> {
    codex_build_info::initialize!();
    // Public upstream dispatch handles helper re-execs before GUI setup.
    let guard = codex_arg0::arg0_dispatch();
    codex_gui::prepare_process_env();
    let current_exe = std::env::current_exe().ok();
    let paths = codex_arg0::Arg0DispatchPaths {
        codex_self_exe: current_exe.clone(),
        codex_linux_sandbox_exe: if cfg!(target_os = "linux") {
            guard
                .as_ref()
                .and_then(|g| g.paths().codex_linux_sandbox_exe.clone())
                .or(current_exe)
        } else {
            None
        },
        main_execve_wrapper_exe: guard
            .as_ref()
            .and_then(|g| g.paths().main_execve_wrapper_exe.clone()),
    };
    // Preserve helper-alias priority after importing the macOS login-shell PATH.
    if let Some(alias_dir) = guard
        .as_ref()
        .and_then(|g| {
            g.paths()
                .main_execve_wrapper_exe
                .as_ref()
                .or(g.paths().codex_linux_sandbox_exe.as_ref())
        })
        .and_then(|p| p.parent())
    {
        let current = std::env::var_os("PATH").unwrap_or_default();
        let entries =
            std::iter::once(alias_dir.to_path_buf()).chain(std::env::split_paths(&current));
        let path = std::env::join_paths(entries)?;
        // SAFETY: GUI setup and upstream dispatch have not spawned worker threads.
        unsafe {
            std::env::set_var("PATH", path);
        }
    }
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .thread_stack_size(codex_async_utils::THREAD_STACK_SIZE_BYTES)
        .build()?;
    // Slint owns the original main thread. Keep aliases alive until tasks stop.
    let result = codex_gui::run_main(paths, runtime.handle().clone());
    runtime.shutdown_timeout(Duration::from_secs(5));
    drop(guard);
    result
}
