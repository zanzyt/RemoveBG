# RemoveBG

A compact desktop application for removing image backgrounds locally with AI models.

The dashboard keeps processing queue, project folders, model
selection, and live activity log visible in one window.

## Getting started

### Windows

Run `start.bat`. The script checks Python, creates a local `.venv`, installs the
required dependencies, and starts the application.

To start it manually:

```powershell
python -m pip install -r requirements.txt
python -m app.py
```

### Linux

Make the launcher executable:

```bash
chmod +x start.sh
```

Then run:

```bash
./start.sh
```

The script checks Python, creates a local `.venv`, installs the required
dependencies, and starts the application.

To start it manually:

```bash
python3 -m pip install -r requirements.txt
python3 -m app.py
```

Some Linux distributions may require Tkinter to be installed separately.

Ubuntu / Debian:

```bash
sudo apt install python3-tk python3-venv
```

Fedora:

```bash
sudo dnf install python3-tkinter
```

Arch Linux:

```bash
sudo pacman -S tk
```

## Usage

* Drag images into the window or click the file selection area.
* Select the **Fast**, **Balanced**, or **Maximum** model preset.
* On first use, the selected model is downloaded automatically. Its preparation
  status is shown in the application.
* Processed images are saved as PNG files in `output`.

Files placed in `input` are processed automatically while the watcher is active.
After successful processing, source files are moved to `done`; failed files are
moved to `error`.


## Supported Formats

The application accepts the following input file formats:

* **JPEG** (`.jpg`, `.jpeg`)
* **PNG** (`.png`)
* **WebP** (`.webp`)
* **HEIC / HEIF** (`.heic`, `.heif`)

> **Note:** All processed images are exported as **PNG** files with an alpha channel to preserve background transparency.


## Project structure

```text
app.py                     application entry point
start.bat                  Windows launcher
start.sh                   Linux launcher
requirements.txt           Python dependencies
pyproject.toml             package metadata and version constraints
assets/                    application icon assets
removebg_app/
  __main__.py              module entry point (`python -m removebg_app`)
  config.py                paths, supported formats, and model settings
  processing.py            worker queue, model sessions, and image processing
  watcher.py               stable-file detection for the input folder
  ui/
    dashboard.py           application controller and dashboard layout
    components.py          reusable panels, buttons, and folder rows
    icons.py               local monochrome icon renderer
    theme.py               colors and typography
  main.py                  application initialization
input/                     watched source folder
output/                    processed PNG files
done/                      successfully processed source files
error/                     source files that could not be processed
tests/                     watcher and processing regression tests
```

## Built With

This project is built on top of the following open-source libraries:

* **[rembg](https://github.com/danielgatis/rembg)** — The core neural network tool used for high-quality background removal.
* **[Pillow](https://python-pillow.org/)** — The Python Imaging Library used for reading, manipulating, and saving the image files.

