from dataclasses import dataclass

import customtkinter as ctk


@dataclass(frozen=True, slots=True)
class Palette:
    background: str = "#111827"
    panel: str = "#1C2738"
    panel_alt: str = "#162131"
    field: str = "#111A28"
    border: str = "#435168"
    border_soft: str = "#2E3B50"
    text: str = "#F3F6FA"
    muted: str = "#A5B0BF"
    subdued: str = "#9CAABD"
    accent: str = "#52A5E5"
    accent_hover: str = "#67B2EA"
    accent_dark: str = "#214E72"
    success: str = "#55D59A"
    warning: str = "#F1BA63"
    danger: str = "#F27582"


COLORS = Palette()


def heading_font(size: int = 15) -> ctk.CTkFont:
    return ctk.CTkFont(family="Segoe UI", size=size, weight="bold")


def body_font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)


def mono_font(size: int = 12) -> ctk.CTkFont:
    return ctk.CTkFont(family="Consolas", size=size)
