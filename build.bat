@echo off
echo Building Database Explorer...

:: --noconfirm overwrites previous builds without prompting
:: --onedir bundles everything into a single folder
:: -w hides the console window
:: --icon sets the executable's external icon
:: --add-data copies the specified files into the output directory (syntax is "source;destination")

setlocal
echo.
echo By default, the compiled application will be placed in a 'dist' folder in this directory.
set /p OUT_DIR="Enter a custom output path (or press Enter to use default): "

if "%OUT_DIR%"=="" (
    set DIST_ARG=
    set FINAL_DIR=dist\database_explorer
    echo Building to default 'dist' directory...
) else (
    if not exist "%OUT_DIR%" (
        echo Directory does not exist. Creating it now...
        mkdir "%OUT_DIR%"
    )
    set DIST_ARG=--distpath "%OUT_DIR%"
    set FINAL_DIR=%OUT_DIR%\database_explorer
    echo Building to custom directory: "%OUT_DIR%"...
)
echo.

python -m PyInstaller --noconfirm --onedir -w --icon=db.ico %DIST_ARG% database_explorer.py

echo.
echo Copying necessary data files to the output folder...
copy /Y db.ico "%FINAL_DIR%\"
copy /Y help.json "%FINAL_DIR%\"
copy /Y database_structure.json "%FINAL_DIR%\"

echo.
echo Build complete! You can find the compiled application in:
echo "%FINAL_DIR%"
pause
endlocal
