@echo off
setlocal EnableDelayedExpansion

:: =============================================================================
:: Huawei Cloud Pricing Tool - Build Script
:: =============================================================================
:: This script builds a standalone Windows executable from the Streamlit
:: application using PyInstaller.
::
:: Requirements:
::   - Python 3.8+ with pip
::   - Windows OS
::
:: Output:
::   - dist/HuaweiCloudPricingTool.exe (standalone executable)
:: =============================================================================

title Huawei Cloud Pricing Tool - Build Executable

:: Colors for output
set "COLOR_RESET="
set "COLOR_GREEN="
set "COLOR_RED="
set "COLOR_YELLOW="
set "COLOR_BLUE="

:: Try to enable colors (Windows 10+)
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (
    set "ESC=%%b"
    set "COLOR_RESET=!ESC![0m"
    set "COLOR_GREEN=!ESC![32m"
    set "COLOR_RED=!ESC![31m"
    set "COLOR_YELLOW=!ESC![33m"
    set "COLOR_BLUE=!ESC![36m"
)

:: =============================================================================
:: Configuration
:: =============================================================================
set "APP_NAME=HuaweiCloudPricingTool"
set "ENTRY_POINT=run_app.py"
set "MAIN_APP=app\huawei_pricing_app.py"
set "DATA_DIR=app\data"
set "BUILD_DIR=build"
set "DIST_DIR=dist"

:: Data files to include
set "DATA_FILES=ecs_pricing.json db_pricing.json storage_pricing.json oss_pricing.json"

:: Hidden imports (packages that PyInstaller might miss)
set "HIDDEN_IMPORTS=streamlit pandas openpyxl numpy mapping_engine pricing_calculator"

:: =============================================================================
:: Helper Functions
:: =============================================================================

goto :main

:print_header
    echo.
    echo %COLOR_BLUE%=============================================================================%COLOR_RESET%
    echo %COLOR_BLUE%  Huawei Cloud Pricing Tool - Executable Builder%COLOR_RESET%
    echo %COLOR_BLUE%=============================================================================%COLOR_RESET%
    echo.
    goto :eof

:print_success
    echo %COLOR_GREEN%[SUCCESS] %~1%COLOR_RESET%
    goto :eof

:print_error
    echo %COLOR_RED%[ERROR] %~1%COLOR_RESET%
    goto :eof

:print_warning
    echo %COLOR_YELLOW%[WARNING] %~1%COLOR_RESET%
    goto :eof

:print_info
    echo [INFO] %~1
    goto :eof

:print_step
    echo.
    echo %COLOR_BLUE%[STEP %~1] %~2%COLOR_RESET%
    goto :eof

:: =============================================================================
:: Main Build Process
:: =============================================================================

:main
call :print_header

:: -----------------------------------------------------------------------------
:: Step 1: Check Python Installation
:: -----------------------------------------------------------------------------
call :print_step 1 "Checking Python installation..."

python --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Python is not installed or not in PATH"
    call :print_info "Please install Python 3.8 or higher from https://python.org"
    goto :error_exit
)

for /f "tokens=2" %%a in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%a"
call :print_success "Found Python %PYTHON_VERSION%"

:: -----------------------------------------------------------------------------
:: Step 2: Check pip Installation
:: -----------------------------------------------------------------------------
call :print_step 2 "Checking pip installation..."

pip --version >nul 2>&1
if errorlevel 1 (
    call :print_error "pip is not installed or not in PATH"
    call :print_info "Please ensure pip is installed with Python"
    goto :error_exit
)

for /f "tokens=2" %%a in ('pip --version') do set "PIP_VERSION=%%a"
call :print_success "Found pip %PIP_VERSION%"

:: -----------------------------------------------------------------------------
:: Step 3: Verify Project Structure
:: -----------------------------------------------------------------------------
call :print_step 3 "Verifying project structure..."

if not exist "%ENTRY_POINT%" (
    call :print_error "Entry point not found: %ENTRY_POINT%"
    call :print_info "Make sure you are running this script from the project root"
    goto :error_exit
)
call :print_success "Found entry point: %ENTRY_POINT%"

if not exist "%MAIN_APP%" (
    call :print_error "Main application not found: %MAIN_APP%"
    goto :error_exit
)
call :print_success "Found main application: %MAIN_APP%"

if not exist "%DATA_DIR%" (
    call :print_error "Data directory not found: %DATA_DIR%"
    goto :error_exit
)
call :print_success "Found data directory: %DATA_DIR%"

:: Check data files
for %%f in (%DATA_FILES%) do (
    if not exist "%DATA_DIR%\%%f" (
        call :print_warning "Data file not found: %DATA_DIR%\%%f"
    ) else (
        call :print_success "Found data file: %%f"
    )
)

:: -----------------------------------------------------------------------------
:: Step 4: Install/Upgrade PyInstaller
:: -----------------------------------------------------------------------------
call :print_step 4 "Installing/upgrading PyInstaller..."

call :print_info "Upgrading pip..."
python -m pip install --upgrade pip >nul 2>&1

call :print_info "Installing PyInstaller..."
pip install --upgrade pyinstaller >nul 2>&1
if errorlevel 1 (
    call :print_error "Failed to install PyInstaller"
    goto :error_exit
)

pyinstaller --version >nul 2>&1
if errorlevel 1 (
    call :print_error "PyInstaller installation verification failed"
    goto :error_exit
)

for /f "tokens=*" %%a in ('pyinstaller --version 2^>^&1') do set "PYINSTALLER_VERSION=%%a"
call :print_success "PyInstaller %PYINSTALLER_VERSION% installed"

:: -----------------------------------------------------------------------------
:: Step 5: Clean Previous Builds
:: -----------------------------------------------------------------------------
call :print_step 5 "Cleaning previous build directories..."

if exist "%BUILD_DIR%" (
    call :print_info "Removing %BUILD_DIR% directory..."
    rmdir /s /q "%BUILD_DIR%" 2>nul
    if exist "%BUILD_DIR%" (
        call :print_warning "Could not fully remove %BUILD_DIR% (files may be in use)"
    ) else (
        call :print_success "Removed %BUILD_DIR% directory"
    )
)

if exist "%DIST_DIR%" (
    call :print_info "Removing %DIST_DIR% directory..."
    rmdir /s /q "%DIST_DIR%" 2>nul
    if exist "%DIST_DIR%" (
        call :print_warning "Could not fully remove %DIST_DIR% (files may be in use)"
    ) else (
        call :print_success "Removed %DIST_DIR% directory"
    )
)

:: Remove spec file if it exists
if exist "%APP_NAME%.spec" (
    call :print_info "Removing old spec file..."
    del /f /q "%APP_NAME%.spec" 2>nul
    call :print_success "Removed old spec file"
)

:: -----------------------------------------------------------------------------
:: Step 6: Build PyInstaller Command
:: -----------------------------------------------------------------------------
call :print_step 6 "Building PyInstaller command..."

:: Base command
set "PYI_CMD=python -m PyInstaller"

:: Output as single executable
set "PYI_CMD=%PYI_CMD% --onefile"

:: Windowed mode (no console for GUI app)
set "PYI_CMD=%PYI_CMD% --windowed"

:: Executable name
set "PYI_CMD=%PYI_CMD% --name %APP_NAME%"

:: Add icon if available
if exist "icon.ico" (
    set "PYI_CMD=%PYI_CMD% --icon=icon.ico"
    call :print_info "Using icon.ico"
) else if exist "icon.png" (
    call :print_warning "icon.png found but .ico format is recommended for Windows"
)

:: Clean build
set "PYI_CMD=%PYI_CMD% --clean"

:: Add data files - Format: --add-data "source;destination"
set "PYI_CMD=%PYI_CMD% --add-data "%DATA_DIR%;app/data""

:: Add the app module Python files
set "PYI_CMD=%PYI_CMD% --add-data "app\*.py;app""

:: Hidden imports
for %%m in (%HIDDEN_IMPORTS%) do (
    set "PYI_CMD=%PYI_CMD% --hidden-import=%%m"
)

:: Collect all for streamlit (includes all assets)
set "PYI_CMD=%PYI_CMD% --collect-all streamlit"
set "PYI_CMD=%PYI_CMD% --collect-all pandas"
set "PYI_CMD=%PYI_CMD% --collect-all openpyxl"
set "PYI_CMD=%PYI_CMD% --collect-all numpy"

:: Additional options for better compatibility
set "PYI_CMD=%PYI_CMD% --noupx"

:: Entry point
set "PYI_CMD=%PYI_CMD% %ENTRY_POINT%"

call :print_info "Command: %PYI_CMD%"

:: -----------------------------------------------------------------------------
:: Step 7: Run PyInstaller
:: -----------------------------------------------------------------------------
call :print_step 7 "Running PyInstaller (this may take several minutes)..."
echo.

%PYI_CMD%

if errorlevel 1 (
    echo.
    call :print_error "PyInstaller build failed"
    goto :error_exit
)

echo.
call :print_success "PyInstaller completed successfully"

:: -----------------------------------------------------------------------------
:: Step 8: Verify Build
:: -----------------------------------------------------------------------------
call :print_step 8 "Verifying build output..."

set "EXE_PATH=%DIST_DIR%\%APP_NAME%.exe"

if not exist "%EXE_PATH%" (
    call :print_error "Executable not found: %EXE_PATH%"
    call :print_info "Checking for alternative locations..."
    
    if exist "%DIST_DIR%" (
        call :print_info "Contents of %DIST_DIR%:"
        dir /b "%DIST_DIR%"
    )
    goto :error_exit
)

:: Get file size
for %%F in ("%EXE_PATH%") do set "FILE_SIZE=%%~zF"
call :print_success "Executable created: %EXE_PATH%"
call :print_info "File size: %FILE_SIZE% bytes"

:: -----------------------------------------------------------------------------
:: Step 9: Copy Additional Files (Optional)
:: -----------------------------------------------------------------------------
call :print_step 9 "Copying additional files to dist..."

:: Copy README if it exists
if exist "README.md" (
    copy /y "README.md" "%DIST_DIR%\" >nul 2>&1
    call :print_success "Copied README.md"
)

:: Copy requirements.txt if it exists
if exist "requirements.txt" (
    copy /y "requirements.txt" "%DIST_DIR%\" >nul 2>&1
    call :print_success "Copied requirements.txt"
)

:: -----------------------------------------------------------------------------
:: Step 10: Final Summary
:: -----------------------------------------------------------------------------
call :print_step 10 "Build Summary"
echo.
echo %COLOR_GREEN%=============================================================================%COLOR_RESET%
echo %COLOR_GREEN%  BUILD SUCCESSFUL!%COLOR_RESET%
echo %COLOR_GREEN%=============================================================================%COLOR_RESET%
echo.
echo   Executable: %EXE_PATH%
echo   File size:  %FILE_SIZE% bytes
echo.
echo %COLOR_BLUE%  Next Steps:%COLOR_RESET%
echo   1. Test the executable: %EXE_PATH%
echo   2. Distribute the entire '%DIST_DIR%' folder
echo   3. The executable can be run on Windows without Python installed
echo.
echo %COLOR_YELLOW%  Note: The first launch may take longer as it extracts files.%COLOR_RESET%
echo %COLOR_YELLOW%  Note: Windows Defender may scan the executable on first run.%COLOR_RESET%
echo.
echo %COLOR_GREEN%=============================================================================%COLOR_RESET%
echo.

goto :end

:: =============================================================================
:: Error Handler
:: =============================================================================

:error_exit
echo.
echo %COLOR_RED%=============================================================================%COLOR_RESET%
echo %COLOR_RED%  BUILD FAILED!%COLOR_RESET%
echo %COLOR_RED%=============================================================================%COLOR_RESET%
echo.
echo %COLOR_YELLOW%  Troubleshooting:%COLOR_RESET%
echo   1. Ensure Python 3.8+ is installed and in PATH
echo   2. Run this script from the project root directory
echo   3. Check that all required files exist (run_app.py, app/huawei_pricing_app.py)
echo   4. Ensure you have sufficient disk space
echo   5. Try running with administrator privileges
echo   6. Check the PyInstaller output above for specific errors
echo.
echo %COLOR_RED%=============================================================================%COLOR_RESET%
echo.
goto :end

:: =============================================================================
:: End
:: =============================================================================

:end
echo.
echo Press any key to exit...
pause >nul
endlocal
