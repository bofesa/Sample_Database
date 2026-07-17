from database_GUI import launch_gui
launch_gui()

### to build as exe, run:
#   python -m PyInstaller --onedir -w --icon=db.ico --add-data "db.ico;." --add-data "help.json;." --add-data "database_structure.json;." database_explorer.py
# or simply double-click the build.bat file.

# alternative simple build command:
    # pyinstaller --onedir -w --icon=db.ico --name DatabaseExplorer 'database_explorer.py'