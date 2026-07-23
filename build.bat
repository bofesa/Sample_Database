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
    set FINAL_DIR=dist\database_explorer
    echo Building to default 'dist' directory...
) else (
    if not exist "%OUT_DIR%" (
        echo Directory does not exist. Creating it now...
        mkdir "%OUT_DIR%"
    )
    set FINAL_DIR=%OUT_DIR%\database_explorer
    echo Building to custom directory: "%OUT_DIR%"...
)
echo.

:: Build to a temporary distpath to avoid PyInstaller wiping the final directory
python -m PyInstaller --noconfirm --onedir -w --icon=db.ico --distpath "pyinstaller_temp" database_explorer.py

echo.
echo Updating application files in the output folder...

if not exist "%FINAL_DIR%" (
    mkdir "%FINAL_DIR%"
)

:: Remove old internal PyInstaller files to avoid stale libraries
if exist "%FINAL_DIR%\_internal" rmdir /S /Q "%FINAL_DIR%\_internal"
if exist "%FINAL_DIR%\database_explorer.exe" del /F /Q "%FINAL_DIR%\database_explorer.exe"

:: Copy the newly built application files (leaves user files like .json untouched)
xcopy /E /Y /I "pyinstaller_temp\database_explorer\*" "%FINAL_DIR%\" >nul

:: Clean up the temporary build directory
rmdir /S /Q "pyinstaller_temp"

echo.
echo Copying necessary data files to the output folder...

if exist "%FINAL_DIR%\db.ico" (
    echo  - [SKIP] db.ico already exists.
) else (
    copy /Y db.ico "%FINAL_DIR%\" >nul
    echo  - [OK] db.ico copied successfully.
)

if exist "%FINAL_DIR%\help.json" (
    echo  - [SKIP] help.json already exists.
) else (
    copy /Y help.json "%FINAL_DIR%\" >nul
    echo  - [OK] help.json copied successfully.
)

if exist "%FINAL_DIR%\database_structure.json" (
    echo  - [SKIP] database_structure.json already exists.
) else (
    copy /Y database_structure.json "%FINAL_DIR%\" >nul
    echo  - [OK] database_structure.json copied successfully.
)

echo.
echo Build complete! You can find the compiled application in:
echo "%FINAL_DIR%"
pause
endlocal
