// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.iter().any(|arg| arg == "--self-test") {
        match anxin_legal_desktop_lib::desktop_runtime_self_test_json() {
            Ok(report) => {
                println!("{report}");
                return;
            }
            Err(error) => {
                eprintln!("desktop runtime self-test failed: {error}");
                std::process::exit(1);
            }
        }
    }

    if args.iter().any(|arg| arg == "--runtime-smoke") {
        println!("desktop runtime smoke starting: exit_after_ms=1500");
        anxin_legal_desktop_lib::run_with_options(
            anxin_legal_desktop_lib::DesktopRunOptions::runtime_smoke(1500),
        );
        return;
    }

    if args.iter().any(|arg| arg == "--runtime-ui-smoke") {
        println!("desktop runtime UI smoke starting: timeout_after_ms=10000");
        anxin_legal_desktop_lib::run_with_options(
            anxin_legal_desktop_lib::DesktopRunOptions::runtime_ui_smoke(10_000),
        );
        return;
    }

    if args
        .iter()
        .any(|arg| arg == "--secure-db-installed-profile-smoke")
    {
        match anxin_legal_desktop_lib::desktop_secure_db_installed_profile_smoke_json() {
            Ok(report) => {
                println!("{report}");
                return;
            }
            Err(error) => {
                eprintln!("desktop secure DB installed-profile smoke failed: {error}");
                std::process::exit(1);
            }
        }
    }

    if args
        .iter()
        .any(|arg| arg == "--secure-db-performance-smoke")
    {
        match anxin_legal_desktop_lib::desktop_secure_db_performance_smoke_json() {
            Ok(report) => {
                println!("{report}");
                return;
            }
            Err(error) => {
                eprintln!("desktop secure DB performance smoke failed: {error}");
                std::process::exit(1);
            }
        }
    }

    if args.iter().any(|arg| arg == "--secure-db-delete-smoke-key") {
        match anxin_legal_desktop_lib::delete_desktop_secure_db_smoke_key() {
            Ok(()) => return,
            Err(error) => {
                eprintln!("desktop secure DB smoke key cleanup failed: {error}");
                std::process::exit(1);
            }
        }
    }

    anxin_legal_desktop_lib::run()
}
