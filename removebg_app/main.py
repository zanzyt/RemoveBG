from pillow_heif import register_heif_opener
from tkinterdnd2 import TkinterDnD

from .config import ensure_working_directories
from .ui import RemoveBGApp


def main() -> None:
    register_heif_opener()
    ensure_working_directories()
    root = TkinterDnD.Tk()
    RemoveBGApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
