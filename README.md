# RemoveBG

A compact desktop application for removing image backgrounds locally with AI models.

The dashboard keeps the watcher status, processing queue, project folders, model
selection, and live activity log visible in one window.

## Getting started

On Windows, run `start.bat`. The script installs the required dependencies and
starts the application.

To start it manually:

```powershell
python -m pip install -r requirements.txt
python -m removebg_app
```

## Usage

- Drag images into the window or click the file selection area.
- Select the **Fast**, **Balanced**, or **Maximum** model preset.
- Use **Start/Stop Watcher** to control automatic monitoring of the `input` folder.
- On first use, the selected model is downloaded automatically. Its preparation
  status is shown in the application.
- Processed images are saved as PNG files in `output`.

Files placed in `input` are processed automatically while the watcher is active.
After successful processing, source files are moved to `done`; failed files are
moved to `error`.

## Project structure

```text
app.py                     application entry point
start.bat                  Windows launcher
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

Runtime folders are created automatically when the application starts.
