# Sample Database Explorer

A Tkinter desktop app for creating and managing hierarchical sample/process trees, with JSON persistence and optional Windows EXE packaging.

## What This Project Contains

- Python source code for the GUI and data model
- JSON database files (tree data)
- PyInstaller build config for creating a Windows executable
- Archived versions of older databases/builds

## Required Folder/File Layout

The program uses relative paths, so keep these files and folders together in the same project root.

```text
Sample_Database/
  database_explorer.py          # main Python entry point
  database_GUI.py               # GUI logic
  database_classes.py           # class model + validation
  database_explorer.spec        # PyInstaller spec
  required_properties.txt       # required property map per class (recommended)
  database_keys.txt             # discovered property keys (auto-created if missing)
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

## Build the Windows EXE

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
- `database_keys.txt` (auto-created if missing)
- `required_properties.txt` (recommended; app can run without it, but required-field prompts may be less strict)

## How To Use The Program

1. Launch the app (`python database_explorer.py` or EXE).
2. Create a new tree:
   - click **New Tree**
   - enter a sample system name
   - save JSON in `databases/`
3. Add nodes:
   - select a parent node
   - choose a child class from allowed options
   - fill required/optional properties
   - click **Create Node**
4. Save progress:
   - click **Save Tree** for normal save
   - click **Save with Timestamp and Close** to version and close
5. Load existing data:
   - **Load Tree** for one JSON file
   - **Open All Trees** to browse all JSON files in `databases/`
6. Search and inspect:
   - use **Search** to find properties across loaded tree(s)
   - use **View Properties** / **Edit Node** on selected items

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

- Unknown properties are accepted but logged with warnings.
- Required properties are class-specific and sourced from `required_properties.txt` in current GUI flows.
- IDs and creation timestamps are immutable once created.
