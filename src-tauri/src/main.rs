#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use rand::{distributions::Alphanumeric, Rng};
use std::{path::PathBuf, process::{Child, Command}, sync::Mutex};
use tauri::{Manager, State};
#[cfg(windows)]
use std::os::windows::process::CommandExt;

struct Runtime { token: String, child: Mutex<Option<Child>> }

#[tauri::command]
fn session_token(runtime: State<Runtime>) -> String { runtime.token.clone() }

fn main() {
    let token: String = rand::thread_rng().sample_iter(&Alphanumeric).take(48).map(char::from).collect();
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(Runtime { token, child: Mutex::new(None) })
        .invoke_handler(tauri::generate_handler![session_token])
        .setup(|app| {
            // Development checkout. Bundled sidecar/installer is explicitly pending.
            let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf();
            let runtime = app.state::<Runtime>();
            let python = root.join(".venv/Scripts/python.exe");
            if !python.exists() { return Err("Prepare .venv según INSTALACION_WINDOWS.md".into()); }
            let mut command = Command::new(python);
            command.current_dir(&root).args(["scripts/launch.py", "--backend-only", "--token", &runtime.token]);
            #[cfg(windows)]
            command.creation_flags(0x08000000);
            let child = command.spawn()?;
            *runtime.child.lock().unwrap() = Some(child);
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("No se pudo iniciar Oficina IA")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                let runtime = app.state::<Runtime>();
                if let Some(mut child) = runtime.child.lock().unwrap().take() {
                    // Terminate launcher and its descendants in a single process tree.
                    #[cfg(windows)]
                    { let mut command = Command::new("taskkill"); command.args(["/PID", &child.id().to_string(), "/T", "/F"]).creation_flags(0x08000000); let _ = command.output(); }
                    let _ = child.kill(); let _ = child.wait();
                };
            }
        });
}
