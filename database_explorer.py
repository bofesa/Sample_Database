import argparse
import json
import sys
from pathlib import Path
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
    parser.add_argument("--new-child-proposal", type=str, default=None,
                        help="Open an unsaved, prefilled child form from a TINSEL proposal JSON")
    args, _ = parser.parse_known_args()

    proposal = None
    if args.new_child_proposal:
        proposal_path = Path(args.new_child_proposal).resolve()
        with proposal_path.open("r", encoding="utf-8-sig") as handle:
            proposal = json.load(handle)
        if proposal.get("status") != "open":
            parser.error("The TINSEL proposal is not open")
        args.project = args.project or proposal.get("database_path") or proposal.get("sample_system")
        args.hexcode = args.hexcode or proposal.get("parent_external_id")

    launch_gui(project=args.project, hexcode=args.hexcode,
               new_child_proposal=proposal)

### to build as exe, run:
#   python -m PyInstaller --onedir -w --icon=db.ico --add-data "db.ico;." --add-data "help.json;." --add-data "database_structure.json;." database_explorer.py
# or simply double-click the build.bat file.

# alternative simple build command:
    # pyinstaller --onefile --windowed --splash db.png --icon=db.ico --name DatabaseExplorer database_explorer.py
        # -console or -w (windowed) option
        # -onedir (one folder) or -onefile (single exe file) option
