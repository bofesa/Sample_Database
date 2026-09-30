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
  database_lock.py              # per-database locking, fingerprints, and atomic JSON writes
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
- **Custom Compilation Possibility**: If you provide a custom path (e.g., `C:\MyApps\DatabaseExplorer`), the executable and necessary data files will be built and placed directly there, making it portable.
- If you press Enter, it defaults to placing the output in a `dist/database_explorer` folder.
- The script automatically copies necessary resources (`db.ico`, `help.json`, `database_structure.json`) alongside the executable, skipping any that already exist to protect your custom data.

## Build the exe manually

From the project root:

```powershell
pyinstaller database_explorer.spec
```

This creates:

- one-file style output: `dist/database_explorer.exe`
- one-dir style output: `dist/database_explorer/` (with `_internal`)

If you prefer direct commands without using the spec, choose either build type below.

One-directory build:

```powershell
pyinstaller --onedir -w --splash db.png --icon=db.ico database_explorer.py
```

One-file build:

```powershell
pyinstaller --onefile -w --splash db.png --icon=db.ico --name DatabaseExplorer database_explorer.py
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
6. Copy / Paste nodes:
   - select a node to copy
   - click **Copy Node** or press `Ctrl+C`
   - select one or multiple destination nodes (using `Shift` or `Ctrl` click)
   - click **Paste Node** or press `Ctrl+V`
   - edit the properties for the pasted node and click **Paste**
7. Save progress:
   - click **File -> Save Tree** for normal save
   - click **File -> Save, Archive and Close** to version it locally and copy it to your secondary backup folder. This also creates a monthly rolling backup of your `database_structure.json` schema!
8. Load existing data:
   - **File -> Load Tree(s)** to browse and open one or multiple JSON files in `databases/`.
   - Loading large files runs in the background, keeping the UI responsive.
   - All open trees share a unified multi-tree workspace. You can manage them simultaneously and use **File -> Close Selected Trees** to close specific ones.
9. Search and inspect:
   - use **Tools -> Search** to find properties across loaded tree(s)
   - use **Edit Node** on selected items in the bottom action bar
10. Help & Settings:
   - **Settings -> Auto-Load Databases on Startup**: Toggles whether the app opens your last active workspace automatically.
   - **Settings -> Backup Settings**: Setup a secondary folder path to maintain remote/cloud backups.
   - **Help -> Help Documentation**: Provides a quick overview of how the program works via `help.json`.

## Concurrent Access And Read-Only Mode

The application prevents two instances from editing the same database file simultaneously.

- The first instance to open a database obtains editable access.
- Additional instances can still browse, search, expand, collapse, and copy from that database, but it opens as **read-only**.
- Read-only trees are marked with `[READ-ONLY]`. Selecting the system root shows the access state and, when available, who opened the editable instance and when.
- Editing, deleting, creating children, pasting properties or nodes, and saving are disabled for read-only trees.
- After the editing instance closes the database, close and reopen it in the read-only instance to obtain editable access and reload the latest contents. Read-only trees are never promoted automatically because their in-memory data may be outdated.

Locking is maintained through a sidecar file named `.<database-name>.lock` beside each database. These files contain owner information and may remain after the application closes; their presence alone does not mean a database is locked. Windows holds the actual lock and releases it automatically when the owning database is closed or if the application terminates unexpectedly. Do not delete sidecar files while the application is running.

This protection requires every user to open the same underlying file on a Windows shared or mapped drive. It also works when the same network location has different drive letters on different computers. It cannot reliably coordinate separate local copies that are synchronized later through OneDrive, Dropbox, or similar tools.

If the application cannot create or access the sidecar, it opens the database read-only rather than risking conflicting changes. Before saving, it also checks whether the database changed outside the application. JSON saves use atomic replacement so a failed write does not truncate the previous database file.

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

## Tests

Run the automated locking and persistence tests from the project root:

```powershell
python -m unittest discover -v
python -m py_compile database_lock.py database_GUI.py database_classes.py database_explorer.py
```


## Development Acknowledgement

This program was developed with the assistance of AI coding tools, including Google Gemini, OpenAI Codex/ChatGPT, and GitHub Copilot. These tools were used to help draft, refactor, test, and document code under human direction and review.
