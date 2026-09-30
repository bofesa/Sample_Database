import argparse
import sys
from database_GUI import launch_gui

if __name__ == "__main__":
    print("Launching Database Explorer GUI...")
    try:        # To close the splash screen if using PyInstaller with pyi_splash
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Sample Database Explorer")
    parser.add_argument("-p", "--project", type=str, default=None, help="Database project name to activate")
    parser.add_argument("-s", "--hexcode", "--sample", type=str, default=None, help="Sample hex node ID to select")
    args, _ = parser.parse_known_args()

    launch_gui(project=args.project, hexcode=args.hexcode)

### to build as exe, run:
#   python -m PyInstaller --onedir -w --icon=db.ico --add-data "db.ico;." --add-data "help.json;." --add-data "database_structure.json;." database_explorer.py
# or simply double-click the build.bat file.

# alternative simple build command:
    # pyinstaller --onefile --windowed --splash db.png --icon=db.ico --name DatabaseExplorer database_explorer.py
        # -console or -w (windowed) option
        # -onedir (one folder) or -onefile (single exe file) option