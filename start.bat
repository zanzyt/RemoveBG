@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"
title RemoveBG

set "PY_CMD="
set "PY_VERSION="
set "PYTHON_VERSION="
set "PYTHON_INSTALLER="
set "PYTHON_URL="
set "INSTALLER_PATH="
set "INSTALLED_PYTHON="
set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"

echo Checking Python...
echo.

for /f "delims=" %%V in ('python -c "import sys; print(str(sys.version_info.major)+'.'+str(sys.version_info.minor)+'.'+str(sys.version_info.micro))" 2^>nul') do (
    set "PY_VERSION=%%V"
)

if defined PY_VERSION (
    set "PY_CMD=python"
    goto check_version
)

for /f "delims=" %%V in ('py -c "import sys; print(str(sys.version_info.major)+'.'+str(sys.version_info.minor)+'.'+str(sys.version_info.micro))" 2^>nul') do (
    set "PY_VERSION=%%V"
)

if defined PY_VERSION (
    set "PY_CMD=py"
    goto check_version
)

echo Python is not installed.
echo Installing Python automatically...
echo.

goto install_python


:check_version

echo Found Python %PY_VERSION%

for /f "tokens=1,2 delims=." %%A in ("%PY_VERSION%") do (
    set "PY_MAJOR=%%A"
    set "PY_MINOR=%%B"
)

if "%PY_MAJOR%"=="3" (
    if %PY_MINOR% GEQ 11 (
        goto python_ready
    )
)

echo.
echo Your Python version is old: %PY_VERSION%
echo Recommended: Python 3.11 or newer.
echo.

set "ANSWER="
set /p "ANSWER=Update Python now? [Y/n]: "

if /I "%ANSWER%"=="n" goto python_ready
if /I "%ANSWER%"=="no" goto python_ready

goto install_python


:install_python

echo.
echo Finding latest stable Python version...
echo.

for /f "usebackq delims=" %%V in (`powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "$page=(Invoke-WebRequest -UseBasicParsing 'https://www.python.org/downloads/windows/').Content;" ^
    "$match=[regex]::Match($page,'Latest Python 3 Release - Python ([0-9]+\.[0-9]+\.[0-9]+)');" ^
    "if(-not $match.Success){exit 1};" ^
    "Write-Output $match.Groups[1].Value"`) do (
    set "PYTHON_VERSION=%%V"
)

if not defined PYTHON_VERSION (
    echo ERROR: Could not determine latest Python version.
    echo Check your internet connection.
    pause
    exit /b 1
)

echo Latest Python: %PYTHON_VERSION%
echo.

set "PYTHON_INSTALLER=python-%PYTHON_VERSION%-amd64.exe"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_INSTALLER%"
set "INSTALLER_PATH=%TEMP%\%PYTHON_INSTALLER%"

echo Downloading Python %PYTHON_VERSION%...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "$ProgressPreference='SilentlyContinue';" ^
    "Invoke-WebRequest -UseBasicParsing -Uri '%PYTHON_URL%' -OutFile '%INSTALLER_PATH%'"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to download Python.
    pause
    exit /b 1
)

if not exist "%INSTALLER_PATH%" (
    echo.
    echo ERROR: Python installer was not downloaded.
    pause
    exit /b 1
)

for /f "tokens=1,2 delims=." %%A in ("%PYTHON_VERSION%") do (
    set "NEW_MAJOR=%%A"
    set "NEW_MINOR=%%B"
)

set "PYTHON_FOLDER=Python%NEW_MAJOR%%NEW_MINOR%"
set "INSTALLED_PYTHON=%LocalAppData%\Programs\Python\%PYTHON_FOLDER%\python.exe"

echo.
echo Installing Python %PYTHON_VERSION%...
echo.

"%INSTALLER_PATH%" /quiet ^
    InstallAllUsers=0 ^
    PrependPath=1 ^
    Include_launcher=1 ^
    Include_pip=1 ^
    Include_test=0

if errorlevel 1 (
    echo.
    echo ERROR: Python installation failed.
    pause
    exit /b 1
)

del "%INSTALLER_PATH%" >nul 2>&1

if exist "%INSTALLED_PYTHON%" (
    set PY_CMD="%INSTALLED_PYTHON%"
    goto python_ready
)

set "PY_VERSION="

for /f "delims=" %%V in ('python -c "import sys; print(str(sys.version_info.major)+'.'+str(sys.version_info.minor)+'.'+str(sys.version_info.micro))" 2^>nul') do (
    set "PY_VERSION=%%V"
)

if defined PY_VERSION (
    set "PY_CMD=python"
    goto python_ready
)

for /f "delims=" %%V in ('py -c "import sys; print(str(sys.version_info.major)+'.'+str(sys.version_info.minor)+'.'+str(sys.version_info.micro))" 2^>nul') do (
    set "PY_VERSION=%%V"
)

if defined PY_VERSION (
    set "PY_CMD=py"
    goto python_ready
)

echo.
echo ERROR: Python was installed but could not be found.
pause
exit /b 1


:python_ready

if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" --version >nul 2>&1

    if not errorlevel 1 (
        goto venv_ready
    )
)

if exist ".venv" (
    echo.
    echo Existing .venv is invalid. Recreating...
    rmdir /s /q ".venv"
)

echo.
echo Creating virtual environment...
echo.

%PY_CMD% -m venv ".venv"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

if not exist "%VENV_PYTHON%" (
    echo.
    echo ERROR: Virtual environment was not created correctly.
    pause
    exit /b 1
)


:venv_ready

echo.
echo Using:
"%VENV_PYTHON%" --version
echo.

echo Installing required packages...
echo.

"%VENV_PYTHON%" -m pip install --upgrade pip
"%VENV_PYTHON%" -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install required packages.
    pause
    exit /b 1
)

echo.
echo Starting RemoveBG...
echo.

"%VENV_PYTHON%" app.py

if errorlevel 1 (
    echo.
    echo RemoveBG stopped with an error.
    pause
)

endlocal
exit /b 0