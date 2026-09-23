#!/usr/bin/env bash

set -e

cd "$(dirname "$0")"

PY_CMD=""
PY_VERSION=""
SUDO=""

if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    fi
fi

find_python() {
    if command -v python3 >/dev/null 2>&1; then
        PY_CMD="python3"
    elif command -v python >/dev/null 2>&1; then
        PY_CMD="python"
    else
        PY_CMD=""
        PY_VERSION=""
        return
    fi

    PY_VERSION="$(
        "$PY_CMD" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")'
    )"
}

install_python() {
    echo
    echo "Installing Python..."
    echo

    if command -v apt-get >/dev/null 2>&1; then
        $SUDO apt-get update
        $SUDO apt-get install -y python3 python3-pip python3-venv python3-tk

    elif command -v dnf >/dev/null 2>&1; then
        $SUDO dnf install -y python3 python3-pip python3-tkinter

    elif command -v yum >/dev/null 2>&1; then
        $SUDO yum install -y python3 python3-pip python3-tkinter

    elif command -v pacman >/dev/null 2>&1; then
        $SUDO pacman -Sy --needed --noconfirm python python-pip tk

    elif command -v zypper >/dev/null 2>&1; then
        $SUDO zypper install -y python3 python3-pip python3-tk

    elif command -v apk >/dev/null 2>&1; then
        $SUDO apk add python3 py3-pip py3-virtualenv tk

    else
        echo "ERROR: Unsupported package manager."
        echo "Install Python 3.11 or newer manually."
        exit 1
    fi

    find_python
}

echo "Checking Python..."
echo

find_python

if [ -z "$PY_CMD" ]; then
    echo "Python is not installed."
    echo "Installing Python automatically..."

    install_python
fi

echo "Found Python $PY_VERSION"

PY_MAJOR="$("$PY_CMD" -c 'import sys; print(sys.version_info.major)')"
PY_MINOR="$("$PY_CMD" -c 'import sys; print(sys.version_info.minor)')"

if [ "$PY_MAJOR" -lt 3 ] || {
    [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]
}; then

    echo
    echo "Your Python version is old: $PY_VERSION"
    echo "Recommended: Python 3.11 or newer."
    echo

    read -r -p "Update Python now? [Y/n]: " ANSWER
    ANSWER="${ANSWER:-Y}"

    if [[ "$ANSWER" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        install_python

        PY_VERSION="$(
            "$PY_CMD" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")'
        )"

        echo
        echo "Using Python $PY_VERSION"
    else
        echo
        echo "Continuing with Python $PY_VERSION."
    fi
fi

VENV_PYTHON=".venv/bin/python"

if [ -e ".venv" ] && [ ! -x "$VENV_PYTHON" ]; then
    echo
    echo "Existing .venv is invalid. Recreating..."
    rm -rf ".venv"
fi

if [ ! -x "$VENV_PYTHON" ]; then
    echo
    echo "Creating virtual environment..."
    "$PY_CMD" -m venv ".venv"
fi

if [ ! -x "$VENV_PYTHON" ]; then
    echo
    echo "ERROR: Failed to create virtual environment."
    exit 1
fi

echo
echo "Using:"
"$VENV_PYTHON" --version
echo

echo "Installing required packages..."
echo

"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements.txt

echo
echo "Starting RemoveBG..."
echo

"$VENV_PYTHON" app.py