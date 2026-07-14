# Sample Database Explorer

A Tkinter desktop app for creating and managing hierarchical sample/process trees, with fully dynamic JSON-driven class structures, JSON persistence, and optional Windows EXE packaging.

## What This Project Contains

- Python source code for the GUI and dynamic data model
- JSON database files (tree data)
- JSON structure schema (`database_structure.json`) defining all components
- PyInstaller build config for creating a Windows executable
- Archived versions of older databases/builds

## Required Folder/File Layout

The program uses relative paths, so keep these files and folders together in the same project root.

```text
Sample_Database/
  database_explorer.py          # main Python entry point
  database_GUI.py               # GUI logic
  database_classes.py           # class model + dynamic JSON generation
  database_explorer.spec        # PyInstaller spec
  database_structure.json       # MASTER SCHEMA: defines all Sample/Processing classes and permitted children
  databases/                    # active JSON trees
    example_tree.json
    TEST_tree.json
    ...
    archive/                    # archived database snapshots
  archive_versions/             # archived zips/exes (manual archive folder)
  build/                        # PyInstaller build artifacts (generated)
  dist/                         # PyInstaller output (generated)
```

## Dependencies

### Runtime dependencies

- Python 3.10+ (recommended)
- treelib
- tkinter (included with standard Windows Python installer)

Install runtime dependency:

```powershell
pip install treelib
```

### Build dependency (only if creating EXE)

- pyinstaller

Install build dependency:

```powershell
pip install pyinstaller
```

## Run From Python (Raw .py workflow)

Run from the project root:

```powershell
python database_explorer.py
```

This launches the GUI (`launch_gui()` in `database_GUI.py`).

## Build the Windows EXE using build.bat file

To compile the application into a standalone Windows executable, simply double-click the `build.bat` file in the project root.

- A terminal will prompt you for a custom output directory.
- If you provide a path (e.g., `C:\MyApps\DatabaseExplorer`), the executable and data files will be built there.
- If you press Enter, it defaults to a `dist/database_explorer` folder.
- The script automatically copies necessary files (`db.ico`, `help.json`, `database_structure.json`) alongside the executable, skipping any that already exist to protect your data.

## Build the exe manually

From the project root:

```powershell
pyinstaller database_explorer.spec
```

This creates:

- one-file style output: `dist/database_explorer.exe`
- one-dir style output: `dist/database_explorer/` (with `_internal`)

If you prefer direct command (without using the spec), your project also documents:

```powershell
pyinstaller --onedir -w database_explorer.py
```

## How to Distribute/Place the EXE

### Recommended

Distribute the `dist/database_explorer/` folder as-is (keep all files inside it together).

### If using `dist/database_explorer.exe`

Place and run it from a working folder that contains (or can create) these alongside it:

- `databases/` (auto-created if missing)
- `database_structure.json` (auto-created if missing, but REQUIRED to configure custom samples/processing steps)

## How To Use The Program

1. Launch the app (`python database_explorer.py` or EXE).
2. Use the **Advanced -> Import Legacy Keys** dropdown if you are upgrading from an older version that used `.txt` files.
3. Manage database structure via **Structure Browser**:
   - Add new properties on the fly.
   - Use the **Advanced -> Add New Structure** menu to build completely custom `Samples` or `Processing Steps` directly in the GUI!
4. Create a new tree:
   - click **File -> New Tree**
   - enter a sample system name
   - save JSON in `databases/`
5. Add nodes:
   - select a parent node
   - choose a child class from allowed options
   - fill required/optional properties
   - click **Create Node**
6. Save progress:
   - click **File -> Save Tree** for normal save
   - click **File -> Save, Archive and Close** to version it locally and copy it to your secondary backup folder. This also creates a monthly rolling backup of your `database_structure.json` schema!
7. Load existing data:
   - **File -> Load Tree** for one JSON file
   - **File -> Load Multiple Trees** to browse and open several JSON files in `databases/`
8. Search and inspect:
   - use **Tools -> Search** to find properties across loaded tree(s)
   - use **Edit Node** on selected items in the bottom action bar
9. Help & Settings:
   - **Settings -> Auto-Load Databases on Startup**: Toggles whether the app opens your last active workspace automatically.
   - **Settings -> Backup Settings**: Setup a secondary folder path to maintain remote/cloud backups.
   - **Help -> Help Documentation**: Provides a quick overview of how the program works via `help.json`.

## JSON Tree File Format

Tree JSON files in `databases/` use this schema:

```json
{
  "root": {
    "id": "SYSTEM",
    "sample_system": "EXAMPLE_PUBLIC"
  },
  "nodes": [
    {
      "id": "w1a2b3",
      "parent": "SYSTEM",
      "class": "Wafer",
      "entry_created_date": "20260423_090000",
      "properties": {
        "material": "Si"
      }
    }
  ]
}
```

A complete public-safe example is included at `databases/example_tree.json`.

## Notes

- The class hierarchy (what subclasses what, and what children are permitted) is entirely defined by `database_structure.json`. Python classes are built dynamically at runtime!
- Unknown properties are accepted but logged with warnings and auto-added to `database_structure.json`.
- Required properties are class-specific and enforced through the Structure JSON.
- IDs and creation timestamps are immutable once created.
