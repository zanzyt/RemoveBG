from collections.abc import Callable
import os
from pathlib import Path
import tkinter as tk

import customtkinter as ctk

from .icons import IconSet
from .theme import COLORS, body_font, heading_font, mono_font


class Panel(ctk.CTkFrame):
    def __init__(
        self,
        master: tk.Misc,
        title: str,
        *,
        icon: ctk.CTkImage | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=COLORS.panel,
            corner_radius=6,
            border_width=1,
            border_color=COLORS.border,
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.header = ctk.CTkFrame(self, fg_color="transparent", height=38)
        self.header.grid(row=0, column=0, sticky="ew", padx=10)
        self.header.grid_columnconfigure(1, weight=1)
        if icon is not None:
            ctk.CTkLabel(self.header, text="", image=icon, width=18).grid(
                row=0, column=0, padx=(0, 7)
            )
        ctk.CTkLabel(
            self.header,
            text=title,
            text_color=COLORS.text,
            font=heading_font(15),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=8)

        ctk.CTkFrame(self, fg_color=COLORS.border, height=1, corner_radius=0).grid(
            row=1, column=0, sticky="ew"
        )
        self.body = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.body.grid(row=2, column=0, sticky="nsew", padx=1, pady=(0, 1))


def action_button(
    parent: tk.Misc,
    icons: IconSet,
    text: str,
    icon_name: str,
    command: Callable[[], None],
    *,
    primary: bool = False,
    danger: bool = False,
    height: int = 38,
) -> ctk.CTkButton:
    if primary:
        fg_color = COLORS.accent
        hover_color = COLORS.accent_hover
        border_width = 0
        text_color = "#FFFFFF"
        icon_color = "#FFFFFF"
    else:
        fg_color = COLORS.panel_alt
        hover_color = "#26374B" if not danger else "#402732"
        border_width = 1
        text_color = COLORS.text if not danger else COLORS.danger
        icon_color = COLORS.muted if not danger else COLORS.danger

    return ctk.CTkButton(
        parent,
        text=text,
        image=icons.get(icon_name, icon_color),
        compound="left",
        width=1,
        height=height,
        corner_radius=4,
        fg_color=fg_color,
        hover_color=hover_color,
        border_width=border_width,
        border_color=COLORS.border,
        text_color=text_color,
        font=body_font(13, "bold"),
        command=command,
    )


class FolderRow(ctk.CTkFrame):
    def __init__(
        self,
        master: tk.Misc,
        icons: IconSet,
        title: str,
        path: Path,
        command: Callable[[], None],
        *,
        color: str = COLORS.muted,
    ) -> None:
        super().__init__(master, fg_color="transparent", corner_radius=0, height=54)
        self.grid_columnconfigure(1, weight=1)
        path_parts = path.parts[-2:]
        short_path = f"…{os.sep}{os.sep.join(path_parts)}"
        ctk.CTkLabel(
            self,
            text="",
            image=icons.get("folder", color),
            width=26,
        ).grid(row=0, column=0, rowspan=2, padx=(2, 8), pady=7)
        ctk.CTkLabel(
            self,
            text=f"{title}/",
            text_color=COLORS.text,
            font=body_font(13, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", pady=(6, 0))
        ctk.CTkLabel(
            self,
            text=short_path,
            text_color=COLORS.subdued,
            font=mono_font(12),
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", pady=(0, 6))
        ctk.CTkButton(
            self,
            text="",
            image=icons.get("open", COLORS.muted),
            width=28,
            height=28,
            corner_radius=4,
            fg_color="transparent",
            hover_color=COLORS.panel_alt,
            command=command,
        ).grid(row=0, column=2, rowspan=2, padx=(5, 1))


class MetricRow(ctk.CTkFrame):
    def __init__(self, master: tk.Misc, label: str, value: str = "—") -> None:
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self,
            text=label,
            text_color=COLORS.muted,
            font=body_font(13),
        ).grid(row=0, column=0, sticky="w")
        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            text_color=COLORS.text,
            font=mono_font(13),
        )
        self.value_label.grid(row=0, column=1, sticky="e")
