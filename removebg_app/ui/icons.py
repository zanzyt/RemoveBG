from collections.abc import Callable

import customtkinter as ctk
from PIL import Image, ImageDraw


class IconSet:
    """Monochrome icons with a high-resolution source for display scaling."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str, int], ctk.CTkImage] = {}

    def get(self, name: str, color: str, size: int = 18) -> ctk.CTkImage:
        key = (name, color, size)
        if key not in self._cache:
            self._cache[key] = self._render(name, color, size)
        return self._cache[key]

    @staticmethod
    def _render(name: str, color: str, size: int) -> ctk.CTkImage:
        # All geometry uses a 16-unit view box. Keep the supersampled source;
        # CTkImage resizes it directly to the current monitor's physical pixels.
        canvas_size = size * 4
        scale = canvas_size / 16
        image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        stroke = max(1, round(1.35 * scale))

        def line(points, **kwargs) -> None:
            draw.line(
                [(x * scale, y * scale) for x, y in points],
                fill=color,
                width=kwargs.get("width", stroke),
                joint="curve",
            )

        drawers: dict[str, Callable[[], None]] = {
            "folder": lambda: IconSet._folder(draw, color, scale, stroke),
            "open": lambda: IconSet._open(draw, color, scale, stroke),
            "upload": lambda: IconSet._upload(draw, color, scale, stroke),
            "trash": lambda: IconSet._trash(draw, color, scale, stroke),
            "play": lambda: draw.polygon(
                [(5 * scale, 3 * scale), (14 * scale, 8 * scale), (5 * scale, 13 * scale)],
                fill=color,
            ),
            "stop": lambda: draw.rounded_rectangle(
                (4 * scale, 4 * scale, 12 * scale, 12 * scale),
                radius=scale,
                fill=color,
            ),
            "image": lambda: IconSet._image(draw, color, scale, stroke),
            "check": lambda: line([(3, 8), (7, 12), (14, 4)]),
            "warning": lambda: IconSet._warning(draw, color, scale, stroke),
            "eye": lambda: IconSet._eye(draw, color, scale, stroke),
        }
        drawers.get(name, drawers["image"])()
        return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))

    @staticmethod
    def _folder(draw: ImageDraw.ImageDraw, color: str, s: float, w: int) -> None:
        points = [(2, 5), (6, 5), (8, 7), (14, 7), (14, 13), (2, 13), (2, 5)]
        draw.line([(x * s, y * s) for x, y in points], fill=color, width=w, joint="curve")

    @staticmethod
    def _open(draw: ImageDraw.ImageDraw, color: str, s: float, w: int) -> None:
        draw.rectangle((2 * s, 5 * s, 11 * s, 14 * s), outline=color, width=w)
        draw.line((7 * s, 9 * s, 14 * s, 2 * s), fill=color, width=w)
        draw.line((9 * s, 2 * s, 14 * s, 2 * s, 14 * s, 7 * s), fill=color, width=w)

    @staticmethod
    def _upload(draw: ImageDraw.ImageDraw, color: str, s: float, w: int) -> None:
        draw.line((8 * s, 3 * s, 8 * s, 11 * s), fill=color, width=w)
        draw.line((4 * s, 7 * s, 8 * s, 3 * s, 12 * s, 7 * s), fill=color, width=w)
        draw.line((3 * s, 13 * s, 13 * s, 13 * s), fill=color, width=w)

    @staticmethod
    def _trash(draw: ImageDraw.ImageDraw, color: str, s: float, w: int) -> None:
        draw.rectangle((4 * s, 5 * s, 12 * s, 14 * s), outline=color, width=w)
        draw.line((3 * s, 4 * s, 13 * s, 4 * s), fill=color, width=w)
        draw.line((6 * s, 2 * s, 10 * s, 2 * s), fill=color, width=w)

    @staticmethod
    def _image(draw: ImageDraw.ImageDraw, color: str, s: float, w: int) -> None:
        draw.rectangle((2 * s, 3 * s, 14 * s, 13 * s), outline=color, width=w)
        draw.ellipse((4 * s, 5 * s, 6 * s, 7 * s), fill=color)
        draw.line((3 * s, 12 * s, 7 * s, 8 * s, 10 * s, 11 * s, 12 * s, 9 * s, 14 * s, 11 * s), fill=color, width=w)

    @staticmethod
    def _warning(draw: ImageDraw.ImageDraw, color: str, s: float, w: int) -> None:
        draw.line(
            [(8 * s, 2 * s), (15 * s, 14 * s), (1 * s, 14 * s), (8 * s, 2 * s)],
            fill=color,
            width=w,
            joint="curve",
        )
        draw.line((8 * s, 6 * s, 8 * s, 9.5 * s), fill=color, width=w)
        draw.ellipse((7.3 * s, 11 * s, 8.7 * s, 12.4 * s), fill=color)

    @staticmethod
    def _eye(draw: ImageDraw.ImageDraw, color: str, s: float, w: int) -> None:
        draw.arc((1 * s, 4 * s, 15 * s, 12 * s), 180, 360, fill=color, width=w)
        draw.arc((1 * s, 4 * s, 15 * s, 12 * s), 0, 180, fill=color, width=w)
        draw.ellipse((6 * s, 6 * s, 10 * s, 10 * s), fill=color)
