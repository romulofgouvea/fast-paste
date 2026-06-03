import os
import shutil

def main():
    print("=== Organizing FastPaste directories ===")
    
    # Create directories
    os.makedirs("configs", exist_ok=True)
    os.makedirs("screens", exist_ok=True)
    os.makedirs("assets", exist_ok=True)
    os.makedirs("core", exist_ok=True)
    os.makedirs("scripts", exist_ok=True)
    
    # Map files to their destination directories
    moves = {
        "configs": ["config.py", "settings_manager.py"],
        "screens": ["popup.py", "settings_ui.py", "tray.py"],
        "assets": ["fast_paste.png", "fast_paste.ico"],
        "core": ["history.py", "monitor.py", "platform_handler.py", "autostart.py", "clip_handler.py"],
        "scripts": ["build.py", "setup.sh"]
    }
    
    for dest, files in moves.items():
        for filename in files:
            if os.path.exists(filename):
                src_path = filename
                dest_path = os.path.join(dest, filename)
                # Overwrite if target already exists (since we wrote updated files in subdirs)
                if os.path.exists(dest_path):
                    os.remove(filename)
                    print(f"[OK] Removed redundant root file: {filename} (already exists in {dest}/)")
                else:
                    shutil.move(src_path, dest_path)
                    print(f"[OK] Moved {filename} -> {dest}/")
            else:
                if os.path.exists(os.path.join(dest, filename)):
                    print(f"[Info] {filename} is already in {dest}/")
                else:
                    print(f"[Warning] File {filename} not found in root")
                    
    # Create __init__.py files
    for d in ["configs", "screens", "core"]:
        init_file = os.path.join(d, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write(f"# Package for {d}\n")
            print(f"[OK] Created {init_file}")

    print("\n=== Reorganization complete! ===")

if __name__ == "__main__":
    main()
