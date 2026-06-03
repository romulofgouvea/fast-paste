import os
import sys

def main():
    print("=== FastPaste Diagnostic Import Checkup ===")
    
    # Ensure project root is in path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    os.chdir(repo_root)
    
    # Modules to check
    modules = [
        "configs.config",
        "configs.settings_manager",
        "core.history",
        "core.monitor",
        "core.platform_handler",
        "core.autostart",
        "core.clip_handler",
        "screens.settings_ui",
        "screens.popup",
        "screens.tray",
    ]
    
    success = True
    for mod in modules:
        print(f"Testing import of '{mod}'...", end=" ")
        try:
            # We use importlib to dynamically check
            import importlib
            importlib.import_module(mod)
            print("✅ OK")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
            success = False
            
    print("\nTesting syntax & structure of main entrypoint 'main'...")
    try:
        # Mock sys.argv so it doesn't run the application or block during check
        sys.argv = ["main.py", "status"]
        
        # Check syntax using py_compile
        import py_compile
        py_compile.compile("main.py", doraise=True)
        print("✅ main.py syntax OK")
        
        # Load main module
        import main
        print("✅ main.py load OK")
    except Exception as e:
        print(f"❌ main.py verification FAILED: {e}")
        import traceback
        traceback.print_exc()
        success = False

    if success:
        print("\n🎉 ALL SYSTEM CHECKS PASSED! Codebase is healthy.")
        sys.exit(0)
    else:
        print("\n❌ SOME SYSTEM CHECKS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
