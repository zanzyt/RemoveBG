import ctypes
import os
import queue
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from PIL import Image
from tkinterdnd2 import DND_FILES

from ..config import (
    DONE_DIR,
    ERROR_DIR,
    INPUT_DIR,
    MODELS,
    OUTPUT_DIR,
    PROJECT_ROOT,
    SUPPORTED_EXTENSIONS,
)
from ..processing import ImageProcessor, ProcessingJob
from ..watcher import InputFolderWatcher
from .components import FolderRow, MetricRow, Panel, action_button
from .icons import IconSet
from .theme import COLORS, body_font, heading_font, mono_font


class RemoveBGApp:
    ACTIVE_STATES = {"Queued", "Loading model", "Model ready", "Processing"}

    def __init__(self, root: tk.Tk) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = root
        self.root.title("AI Background Removal")
        self.root.geometry("1024x640")
        self.root.minsize(940, 600)
        self.root.configure(bg=COLORS.background)

        self.icons = IconSet()
        self.ui_queue: queue.Queue[tuple] = queue.Queue()
        self.queued_sources: set[str] = set()
        self.output_by_item: dict[str, Path] = {}
        self.path_by_item: dict[str, Path] = {}
        self.source_type_by_item: dict[str, str] = {}
        self.started_by_item: dict[str, float] = {}
        self.loaded_models: set[str] = set()
        self.loading_model_key: str | None = None
        self.maximum_confirmed = False
        self.closed = False
        self.watcher_enabled = True
        self.completed_total = 0
        self.error_total = 0
        self.total_processing_seconds = 0.0
        self.total_input_bytes = 0
        self.session_started_at = time.monotonic()
        self.log_line_count = 0
        self.current_model_key = "fast"

        self.input_watcher = InputFolderWatcher(INPUT_DIR, stability_seconds=1.0)
        self.processor = ImageProcessor(self.emit, self.log)

        self._load_brand_assets()
        self._setup_tree_style()
        self._build_ui()
        self._bind_shortcuts()
        self._update_watcher_ui()
        self._update_metrics()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(50, self.process_ui_queue)
        self.root.after(200, self._enable_dark_titlebar)
        self.root.after(1000, self.scan_input_folder)
        self.processor.start()

        self.log("Watcher started. Monitoring the input folder.")
        self.log(f"Output directory: {OUTPUT_DIR}")

    def _load_brand_assets(self) -> None:
        icon_path = PROJECT_ROOT / "assets" / "app_icon.png"
        self.window_icon: tk.PhotoImage | None = None
        self.brand_image: ctk.CTkImage | None = None
        if not icon_path.exists():
            return
        try:
            self.window_icon = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, self.window_icon)
            source = Image.open(icon_path)
            self.brand_image = ctk.CTkImage(
                light_image=source,
                dark_image=source,
                size=(29, 29),
            )
        except (OSError, tk.TclError):
            self.window_icon = None
            self.brand_image = None

    def _enable_dark_titlebar(self) -> None:
        if not sys.platform.startswith("win") or self.closed:
            return
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            enabled = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(enabled), ctypes.sizeof(enabled)
            )
        except (AttributeError, OSError):
            pass

    def _setup_tree_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Pipeline.Treeview",
            background=COLORS.field,
            fieldbackground=COLORS.field,
            foreground=COLORS.text,
            rowheight=36,
            borderwidth=0,
            relief="flat",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Pipeline.Treeview.Heading",
            background=COLORS.panel_alt,
            foreground=COLORS.muted,
            borderwidth=0,
            relief="flat",
            padding=(6, 8),
            font=("Bahnschrift SemiCondensed", 9, "bold"),
        )
        style.map(
            "Pipeline.Treeview",
            background=[("selected", "#26384D")],
            foreground=[("selected", COLORS.text)],
        )
        style.map(
            "Pipeline.Treeview.Heading",
            background=[("active", COLORS.panel_alt)],
        )
        style.layout(
            "Pipeline.Treeview",
            [("Pipeline.Treeview.treearea", {"sticky": "nswe"})],
        )

    def _build_ui(self) -> None:
        shell = ctk.CTkFrame(self.root, fg_color=COLORS.background, corner_radius=0)
        shell.pack(fill="both", expand=True, padx=12, pady=10)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)

        self._build_header(shell)

        workspace = ctk.CTkFrame(shell, fg_color="transparent")
        workspace.grid(row=1, column=0, sticky="nsew", pady=(9, 0))
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(0, weight=13)
        workspace.grid_rowconfigure(1, weight=7)

        top = ctk.CTkFrame(workspace, fg_color="transparent")
        top.grid(row=0, column=0, sticky="nsew")
        top.grid_columnconfigure(0, weight=27)
        top.grid_columnconfigure(1, weight=42)
        top.grid_columnconfigure(2, weight=31)
        top.grid_rowconfigure(0, weight=1)

        self._build_service_panel(top)

        center = ctk.CTkFrame(top, fg_color="transparent")
        center.grid(row=0, column=1, sticky="nsew", padx=6)
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(0, weight=2)
        center.grid_rowconfigure(1, weight=3)
        self._build_current_panel(center)
        self._build_configuration_panel(center)

        self._build_pipeline_panel(top)

        bottom = ctk.CTkFrame(workspace, fg_color="transparent")
        bottom.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        bottom.grid_columnconfigure((0, 1), weight=1, uniform="bottom")
        bottom.grid_rowconfigure(0, weight=1)
        self._build_log_panel(bottom)
        self._build_folder_actions_panel(bottom)

    def _build_header(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color="transparent", height=34)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(2, weight=1)

        if self.brand_image is not None:
            ctk.CTkLabel(header, text="", image=self.brand_image, width=32).grid(
                row=0, column=0, padx=(1, 8)
            )
        ctk.CTkLabel(
            header,
            text="AI BACKGROUND REMOVAL",
            text_color=COLORS.text,
            font=heading_font(17),
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            header,
            text="AUTOMATION CONSOLE  /  LOCAL PROCESSING",
            text_color=COLORS.subdued,
            font=mono_font(8),
        ).grid(row=0, column=2, sticky="e", padx=(10, 1))

    def _build_service_panel(self, parent: ctk.CTkFrame) -> None:
        panel = Panel(parent, "Background Removal", icon=self.icons.get("image", COLORS.accent))
        panel.grid(row=0, column=0, sticky="nsew")
        body = panel.body
        body.grid_columnconfigure(0, weight=1)

        status = ctk.CTkFrame(body, fg_color="transparent")
        status.grid(row=0, column=0, sticky="ew", padx=11, pady=(9, 6))
        status.grid_columnconfigure(1, weight=1)
        self.watcher_dot = ctk.CTkLabel(
            status,
            text="●",
            text_color=COLORS.success,
            width=14,
            font=body_font(10, "bold"),
        )
        self.watcher_dot.grid(row=0, column=0, sticky="w")
        self.watcher_status_label = ctk.CTkLabel(
            status,
            text="RUNNING · MONITORING INPUT",
            text_color=COLORS.text,
            font=heading_font(10),
            anchor="w",
        )
        self.watcher_status_label.grid(row=0, column=1, sticky="w")

        self.watcher_button = action_button(
            body,
            self.icons,
            "Stop watcher",
            "stop",
            self.toggle_watcher,
            primary=True,
        )
        self.watcher_button.grid(row=1, column=0, sticky="ew", padx=11, pady=(0, 9))

        ctk.CTkFrame(body, fg_color=COLORS.border_soft, height=1, corner_radius=0).grid(
            row=2, column=0, sticky="ew", padx=10
        )

        folders = (
            ("Input", INPUT_DIR, COLORS.accent),
            ("Output", OUTPUT_DIR, COLORS.success),
            ("Done", DONE_DIR, COLORS.warning),
            ("Error", ERROR_DIR, COLORS.danger),
        )
        for index, (title, path, color) in enumerate(folders, start=3):
            row = FolderRow(
                body,
                self.icons,
                title,
                path,
                lambda folder=path: self.open_path(folder),
                color=color,
            )
            row.grid(row=index, column=0, sticky="ew", padx=9)
            if index < 6:
                ctk.CTkFrame(
                    body, fg_color=COLORS.border_soft, height=1, corner_radius=0
                ).grid(row=index, column=0, sticky="sew", padx=10)

    def _build_current_panel(self, parent: ctk.CTkFrame) -> None:
        panel = Panel(parent, "Current Item", icon=self.icons.get("image", COLORS.muted))
        panel.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        body = panel.body
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.drop_target = ctk.CTkFrame(
            body,
            fg_color=COLORS.field,
            corner_radius=4,
            border_width=1,
            border_color=COLORS.border_soft,
        )
        self.drop_target.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=9, pady=9)
        self.drop_target.grid_columnconfigure(1, weight=1)
        self.drop_target.grid_rowconfigure(0, weight=1)

        self.current_icon_label = ctk.CTkLabel(
            self.drop_target,
            text="",
            image=self.icons.get("upload", COLORS.accent),
            width=32,
        )
        self.current_icon_label.grid(row=0, column=0, rowspan=2, padx=(13, 9), pady=10)
        self.current_name_label = ctk.CTkLabel(
            self.drop_target,
            text="No item is being processed",
            text_color=COLORS.text,
            font=body_font(11, "bold"),
            anchor="w",
        )
        self.current_name_label.grid(row=0, column=1, sticky="sw", pady=(10, 0))
        self.current_detail_label = ctk.CTkLabel(
            self.drop_target,
            text="Drop files here or use Browse",
            text_color=COLORS.muted,
            font=body_font(9),
            anchor="w",
        )
        self.current_detail_label.grid(row=1, column=1, sticky="nw", pady=(1, 10))

        browse = action_button(
            self.drop_target,
            self.icons,
            "Browse",
            "upload",
            self.select_files,
        )
        browse.grid(row=0, column=2, rowspan=2, padx=11, pady=11)

        for widget in (self.drop_target, self.current_name_label, self.current_detail_label):
            self._register_drop_target(widget)
        self.drop_target.bind("<Enter>", self._drop_hover_on)
        self.drop_target.bind("<Leave>", self._drop_hover_off)

    def _build_configuration_panel(self, parent: ctk.CTkFrame) -> None:
        panel = Panel(parent, "Model & Performance")
        panel.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        body = panel.body
        body.grid_columnconfigure((0, 1), weight=1, uniform="config")
        body.grid_rowconfigure(0, weight=1)

        controls = ctk.CTkFrame(body, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="nsew", padx=(11, 8), pady=9)
        controls.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            controls,
            text="MODEL",
            text_color=COLORS.muted,
            font=heading_font(9),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.model_labels = {spec.title: key for key, spec in MODELS.items()}
        self.model_label_var = tk.StringVar(value=MODELS[self.current_model_key].title)
        self.model_selector = ctk.CTkOptionMenu(
            controls,
            values=list(self.model_labels),
            variable=self.model_label_var,
            command=self.on_model_changed,
            height=31,
            corner_radius=4,
            fg_color=COLORS.field,
            button_color=COLORS.border_soft,
            button_hover_color=COLORS.border,
            dropdown_fg_color=COLORS.panel_alt,
            dropdown_hover_color="#2A3A4F",
            text_color=COLORS.text,
            font=body_font(10),
        )
        self.model_selector.grid(row=1, column=0, sticky="ew", pady=(4, 10))

        delay_header = ctk.CTkFrame(controls, fg_color="transparent")
        delay_header.grid(row=2, column=0, sticky="ew")
        delay_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            delay_header,
            text="FILE STABILITY DELAY",
            text_color=COLORS.muted,
            font=heading_font(9),
        ).grid(row=0, column=0, sticky="w")
        self.delay_value_label = ctk.CTkLabel(
            delay_header,
            text="1.0 SEC",
            text_color=COLORS.text,
            font=mono_font(8),
        )
        self.delay_value_label.grid(row=0, column=1, sticky="e")

        self.delay_slider = ctk.CTkSlider(
            controls,
            from_=0.5,
            to=5.0,
            number_of_steps=9,
            command=self.on_delay_changed,
            height=14,
            fg_color=COLORS.border_soft,
            progress_color=COLORS.accent,
            button_color=COLORS.text,
            button_hover_color="#FFFFFF",
            button_length=13,
        )
        self.delay_slider.set(1.0)
        self.delay_slider.grid(row=3, column=0, sticky="ew", pady=(6, 9))

        self.model_state_label = ctk.CTkLabel(
            controls,
            text="Model loads on first use",
            text_color=COLORS.subdued,
            font=body_font(8),
            anchor="w",
        )
        self.model_state_label.grid(row=4, column=0, sticky="w")
        self.model_progress = ctk.CTkProgressBar(
            controls,
            height=4,
            corner_radius=0,
            mode="determinate",
            fg_color=COLORS.border_soft,
            progress_color=COLORS.accent,
        )
        self.model_progress.set(0)
        self.model_progress.grid(row=5, column=0, sticky="ew", pady=(4, 0))

        stats = ctk.CTkFrame(
            body,
            fg_color=COLORS.panel_alt,
            corner_radius=4,
            border_width=1,
            border_color=COLORS.border_soft,
        )
        stats.grid(row=0, column=1, sticky="nsew", padx=(8, 11), pady=9)
        stats.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            stats,
            text="SESSION STATS",
            text_color=COLORS.text,
            font=heading_font(10),
        ).grid(row=0, column=0, sticky="w", padx=9, pady=(7, 4))
        self.metric_rows = {
            "processed": MetricRow(stats, "Processed", "0"),
            "rate": MetricRow(stats, "Processing rate"),
            "average": MetricRow(stats, "Average time"),
            "data": MetricRow(stats, "Total data", "0 B"),
            "errors": MetricRow(stats, "Errors", "0"),
        }
        for index, row in enumerate(self.metric_rows.values(), start=1):
            row.grid(row=index, column=0, sticky="ew", padx=9, pady=1)

    def _build_pipeline_panel(self, parent: ctk.CTkFrame) -> None:
        panel = Panel(parent, "Processing Pipeline")
        panel.grid(row=0, column=2, sticky="nsew")
        panel.body.grid_columnconfigure(0, weight=1)
        panel.body.grid_rowconfigure(0, weight=1)

        tree_box = tk.Frame(panel.body, bg=COLORS.field, bd=0, highlightthickness=0)
        tree_box.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 5))
        tree_box.grid_columnconfigure(0, weight=1)
        tree_box.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_box,
            columns=("status", "name", "source", "action"),
            show="headings",
            selectmode="browse",
            style="Pipeline.Treeview",
        )
        self.tree.heading("status", text="STATUS")
        self.tree.heading("name", text="FILE")
        self.tree.heading("source", text="SOURCE")
        self.tree.heading("action", text="ACTION")
        self.tree.column("status", width=76, minwidth=64, anchor="w", stretch=False)
        self.tree.column("name", width=145, minwidth=90, anchor="w")
        self.tree.column("source", width=62, minwidth=55, anchor="w", stretch=False)
        self.tree.column("action", width=52, minwidth=45, anchor="w", stretch=False)
        self.tree.tag_configure("done", foreground=COLORS.success)
        self.tree.tag_configure("error", foreground=COLORS.danger)
        self.tree.tag_configure("active", foreground=COLORS.accent)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self.open_selected_result)

        scrollbar = ctk.CTkScrollbar(
            tree_box,
            orientation="vertical",
            command=self.tree.yview,
            width=9,
            corner_radius=0,
            fg_color=COLORS.field,
            button_color=COLORS.border,
            button_hover_color=COLORS.accent_dark,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        actions = ctk.CTkFrame(panel.body, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=8, pady=(1, 8))
        actions.grid_columnconfigure((0, 1, 2), weight=1, uniform="pipeline-actions")
        action_button(actions, self.icons, "Add", "upload", self.select_files, height=29).grid(
            row=0, column=0, sticky="ew", padx=(0, 3)
        )
        action_button(
            actions, self.icons, "View", "eye", self.open_selected_result, height=29
        ).grid(row=0, column=1, sticky="ew", padx=3)
        action_button(
            actions, self.icons, "Clear", "trash", self.clear_completed, height=29
        ).grid(row=0, column=2, sticky="ew", padx=(3, 0))

    def _build_log_panel(self, parent: ctk.CTkFrame) -> None:
        panel = Panel(parent, "Activity Log")
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(
            panel.header,
            text="SESSION",
            text_color=COLORS.subdued,
            font=mono_font(8),
        ).grid(row=0, column=2, sticky="e")
        ctk.CTkButton(
            panel.header,
            text="",
            image=self.icons.get("trash", COLORS.muted),
            width=27,
            height=27,
            corner_radius=4,
            fg_color="transparent",
            hover_color=COLORS.panel_alt,
            command=self.clear_log,
        ).grid(row=0, column=3, padx=(5, 0))

        self.log_area = tk.Text(
            panel.body,
            height=6,
            wrap=tk.WORD,
            bg=COLORS.field,
            fg="#D9E1EB",
            insertbackground=COLORS.text,
            selectbackground="#2B4662",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=9,
            pady=7,
            font=("Cascadia Mono", 8),
            state="disabled",
        )
        self.log_area.tag_configure("timestamp", foreground=COLORS.subdued)
        self.log_area.tag_configure("success", foreground=COLORS.success)
        self.log_area.tag_configure("error", foreground=COLORS.danger)
        self.log_area.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        panel.body.grid_columnconfigure(0, weight=1)
        panel.body.grid_rowconfigure(0, weight=1)

    def _build_folder_actions_panel(self, parent: ctk.CTkFrame) -> None:
        panel = Panel(parent, "Folder Management", icon=self.icons.get("folder", COLORS.accent))
        panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        body = panel.body
        body.grid_columnconfigure((0, 1), weight=1, uniform="folder-actions")
        body.grid_rowconfigure((0, 1), weight=1)

        buttons = (
            ("Open Input", INPUT_DIR, "folder"),
            ("Open Output", OUTPUT_DIR, "folder"),
            ("Open Done", DONE_DIR, "check"),
            ("Open Errors", ERROR_DIR, "warning"),
        )
        for index, (label, path, icon_name) in enumerate(buttons):
            row, column = divmod(index, 2)
            button = action_button(
                body,
                self.icons,
                label,
                icon_name,
                lambda folder=path: self.open_path(folder),
                height=36,
            )
            button.grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=(9 if column == 0 else 4, 4 if column == 0 else 9),
                pady=(9 if row == 0 else 4, 4 if row == 0 else 9),
            )

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-o>", lambda _event: self.select_files())
        self.root.bind("<Control-Shift-O>", lambda _event: self.open_output_folder())

    def _register_drop_target(self, widget: tk.Misc) -> None:
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind("<<Drop>>", self.handle_drop)

    def _drop_hover_on(self, _event: tk.Event) -> None:
        self.drop_target.configure(border_color=COLORS.accent, fg_color="#172536")

    def _drop_hover_off(self, _event: tk.Event) -> None:
        self.drop_target.configure(border_color=COLORS.border_soft, fg_color=COLORS.field)

    def on_delay_changed(self, value: float) -> None:
        rounded = round(float(value) * 2) / 2
        self.input_watcher.stability_seconds = rounded
        self.delay_value_label.configure(text=f"{rounded:.1f} SEC")

    def on_model_changed(self, label: str) -> None:
        new_key = self.model_labels[label]
        if new_key == "maximum" and not self.confirm_maximum_quality():
            self.model_label_var.set(MODELS[self.current_model_key].title)
            return
        self.current_model_key = new_key
        state = "ready" if new_key in self.loaded_models else "loads on first use"
        self.model_state_label.configure(
            text=f"{MODELS[new_key].title} · {state}",
            text_color=COLORS.success if new_key in self.loaded_models else COLORS.subdued,
        )

    def confirm_maximum_quality(self) -> bool:
        if self.maximum_confirmed:
            return True
        accepted = messagebox.askyesno(
            "Maximum quality model",
            "The Maximum model requires a download of approximately 1 GB on first use.\n\n"
            "The downloaded model is kept locally for future jobs. Continue?",
            parent=self.root,
        )
        if accepted:
            self.maximum_confirmed = True
        return accepted

    def toggle_watcher(self) -> None:
        self.watcher_enabled = not self.watcher_enabled
        if self.watcher_enabled:
            self.input_watcher.reset()
        self._update_watcher_ui()
        self.log("Input monitoring resumed." if self.watcher_enabled else "Input monitoring paused.")

    def _update_watcher_ui(self) -> None:
        if self.watcher_enabled:
            self.watcher_dot.configure(text_color=COLORS.success)
            self.watcher_status_label.configure(text="RUNNING · MONITORING INPUT")
            self.watcher_button.configure(
                text="STOP WATCHER",
                image=self.icons.get("stop", "#FFFFFF"),
                fg_color=COLORS.accent,
                hover_color=COLORS.accent_hover,
            )
        else:
            self.watcher_dot.configure(text_color=COLORS.warning)
            self.watcher_status_label.configure(text="PAUSED · MONITORING DISABLED")
            self.watcher_button.configure(
                text="START WATCHER",
                image=self.icons.get("play", "#FFFFFF"),
                fg_color=COLORS.accent,
                hover_color=COLORS.accent_hover,
            )

    def handle_drop(self, event: tk.Event) -> None:
        self.add_paths(self.root.tk.splitlist(event.data))

    def select_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Choose images",
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.webp *.heic *.heif"),
                ("All files", "*.*"),
            ],
        )
        if files:
            self.add_paths(files)

    def add_paths(self, paths: tuple[str, ...] | list[str]) -> None:
        found: list[Path] = []
        for value in paths:
            path = Path(value)
            if path.is_dir():
                found.extend(
                    child
                    for child in path.rglob("*")
                    if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS
                )
            elif path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                found.append(path)
            elif path.is_file():
                self.log(f"Unsupported file type: {path.name}")

        if not found:
            return
        if self.current_model_key == "maximum" and not self.confirm_maximum_quality():
            return
        for path in found:
            self.enqueue_file(
                path,
                model_key=self.current_model_key,
                move_after=self._is_input_path(path),
            )
        self.update_summary()

    @staticmethod
    def _is_input_path(path: Path) -> bool:
        try:
            return path.resolve().is_relative_to(INPUT_DIR.resolve())
        except OSError:
            return False

    def enqueue_file(self, path: Path, model_key: str, move_after: bool = False) -> None:
        try:
            source_key = str(path.resolve())
        except OSError:
            source_key = str(path)
        if source_key in self.queued_sources:
            return

        self.queued_sources.add(source_key)
        spec = MODELS[model_key]
        source_type = "Input" if move_after else "Manual"
        item_id = self.tree.insert(
            "",
            "end",
            values=("Queued", path.name, source_type, "—"),
        )
        self.path_by_item[item_id] = path
        self.source_type_by_item[item_id] = source_type
        try:
            self.total_input_bytes += path.stat().st_size
        except OSError:
            pass
        self.processor.submit(
            ProcessingJob(
                item_id=item_id,
                source_path=path,
                source_key=source_key,
                model_key=model_key,
                move_after=move_after,
            )
        )
        self.log(f"File queued: {path.name} [{spec.title}]")

    def emit(self, event_type: str, *payload: object) -> None:
        self.ui_queue.put((event_type, *payload))

    def log(self, message: str) -> None:
        self.emit("log", time.strftime("%H:%M:%S"), message)

    def process_ui_queue(self) -> None:
        try:
            while True:
                self._handle_ui_event(self.ui_queue.get_nowait())
        except queue.Empty:
            pass
        if not self.closed:
            self.root.after(50, self.process_ui_queue)

    def _handle_ui_event(self, event: tuple) -> None:
        event_type = event[0]
        if event_type == "log":
            self._append_log(event[1], event[2])
            return

        if event_type == "model_loading":
            _, item_id, model_key = event
            self.loading_model_key = model_key
            self._set_item_status(item_id, "Loading model", "active")
            self._show_model_loader(model_key)
        elif event_type == "model_ready":
            _, item_id, model_key = event
            self.loaded_models.add(model_key)
            self.loading_model_key = None
            self._set_item_status(item_id, "Model ready", "active")
            self._finish_model_loader(model_key)
        elif event_type == "processing":
            _, item_id, model_key = event
            self.started_by_item[item_id] = time.monotonic()
            self._set_item_status(item_id, "Processing", "active")
            self._show_current_item(item_id, model_key)
        elif event_type == "success":
            _, item_id, output_path, source_key = event
            self.queued_sources.discard(source_key)
            self.output_by_item[item_id] = Path(output_path)
            self.completed_total += 1
            self._record_duration(item_id)
            self._set_item_status(item_id, "Done", "done", action="View")
            self._clear_current_item(item_id)
            self.check_processing_state()
        elif event_type == "error":
            _, item_id, error_text, source_key, model_key = event
            self.queued_sources.discard(source_key)
            self.error_total += 1
            self._record_duration(item_id)
            self._set_item_status(item_id, "Error", "error")
            self._clear_current_item(item_id)
            if model_key == self.loading_model_key:
                self.loading_model_key = None
                self.model_progress.stop()
                self.model_progress.configure(mode="determinate")
                self.model_progress.set(0)
                self.model_selector.configure(state="normal")
                self.model_state_label.configure(text="Model loading failed", text_color=COLORS.danger)
            self.log(f"Error details: {error_text}")
            self.check_processing_state()

        self.update_summary()
        self._update_metrics()

    def _append_log(self, timestamp: str, message: str) -> None:
        self.log_area.configure(state="normal")
        self.log_area.insert(tk.END, timestamp, "timestamp")
        tag = "error" if "error" in message.lower() else "success" if "done" in message.lower() or "success" in message.lower() else None
        self.log_area.insert(tk.END, f"  {message}\n", tag)
        self.log_line_count += 1
        if self.log_line_count > 500:
            self.log_area.delete("1.0", "101.0")
            self.log_line_count -= 100
        self.log_area.see(tk.END)
        self.log_area.configure(state="disabled")

    def _set_item_status(
        self,
        item_id: str,
        status: str,
        tag: str = "",
        *,
        action: str | None = None,
    ) -> None:
        if not self.tree.exists(item_id):
            return
        values = list(self.tree.item(item_id, "values"))
        values[0] = status
        if action is not None:
            values[3] = action
        self.tree.item(item_id, values=values, tags=(tag,) if tag else ())

    def _show_current_item(self, item_id: str, model_key: str) -> None:
        path = self.path_by_item.get(item_id)
        self.current_icon_label.configure(image=self.icons.get("image", COLORS.accent))
        self.current_name_label.configure(text=path.name if path else "Processing image")
        self.current_detail_label.configure(text=f"Processing · {MODELS[model_key].title} model")

    def _clear_current_item(self, item_id: str) -> None:
        active = [
            child
            for child in self.tree.get_children()
            if child != item_id
            and self.tree.item(child, "values")
            and self.tree.item(child, "values")[0] in self.ACTIVE_STATES
        ]
        if not active:
            self.current_icon_label.configure(image=self.icons.get("upload", COLORS.accent))
            self.current_name_label.configure(text="No item is being processed")
            self.current_detail_label.configure(text="Drop files here or use Browse")

    def _record_duration(self, item_id: str) -> None:
        started = self.started_by_item.pop(item_id, None)
        if started is not None:
            self.total_processing_seconds += time.monotonic() - started

    def _show_model_loader(self, model_key: str) -> None:
        self.model_selector.configure(state="disabled")
        self.model_state_label.configure(
            text=f"Loading {MODELS[model_key].title} model…",
            text_color=COLORS.accent,
        )
        self.model_progress.configure(mode="indeterminate")
        self.model_progress.start()

    def _finish_model_loader(self, model_key: str) -> None:
        self.model_progress.stop()
        self.model_progress.configure(mode="determinate")
        self.model_progress.set(1)
        self.model_selector.configure(state="normal")
        self.model_state_label.configure(
            text=f"{MODELS[model_key].title} model ready",
            text_color=COLORS.success,
        )

    def check_processing_state(self) -> None:
        active = any(
            values and values[0] in self.ACTIVE_STATES
            for item_id in self.tree.get_children()
            if (values := self.tree.item(item_id, "values"))
        )
        if active or self.loading_model_key is not None:
            return
        self.model_progress.stop()
        self.model_progress.configure(mode="determinate")
        self.model_progress.set(0)
        state = "ready" if self.current_model_key in self.loaded_models else "loads on first use"
        self.model_state_label.configure(
            text=f"{MODELS[self.current_model_key].title} · {state}",
            text_color=COLORS.success if state == "ready" else COLORS.subdued,
        )

    def update_summary(self) -> None:
        active = 0
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, "values")
            if values and values[0] in self.ACTIVE_STATES:
                active += 1
        if hasattr(self, "metric_rows"):
            self.metric_rows["processed"].value_label.configure(text=str(self.completed_total))
        self._active_jobs = active

    def _update_metrics(self) -> None:
        if not hasattr(self, "metric_rows"):
            return
        elapsed_hours = max((time.monotonic() - self.session_started_at) / 3600, 1 / 3600)
        rate = self.completed_total / elapsed_hours if self.completed_total else 0
        average = (
            self.total_processing_seconds / self.completed_total
            if self.completed_total
            else 0
        )
        self.metric_rows["processed"].value_label.configure(text=str(self.completed_total))
        self.metric_rows["rate"].value_label.configure(
            text=f"{rate:.1f}/hr" if self.completed_total else "—"
        )
        self.metric_rows["average"].value_label.configure(
            text=f"{average:.1f} sec" if self.completed_total else "—"
        )
        self.metric_rows["data"].value_label.configure(text=self._format_bytes(self.total_input_bytes))
        self.metric_rows["errors"].value_label.configure(text=str(self.error_total))

    @staticmethod
    def _format_bytes(value: int) -> str:
        size = float(value)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"

    def scan_input_folder(self) -> None:
        if self.closed:
            return
        if self.watcher_enabled:
            for path in self.input_watcher.scan(self.queued_sources):
                self.enqueue_file(path, model_key=self.current_model_key, move_after=True)
            self.update_summary()
        self.root.after(1000, self.scan_input_folder)

    def clear_completed(self) -> None:
        for item_id in list(self.tree.get_children()):
            values = self.tree.item(item_id, "values")
            if values and values[0] in ("Done", "Error"):
                self.tree.delete(item_id)
                self.output_by_item.pop(item_id, None)
                self.path_by_item.pop(item_id, None)
                self.source_type_by_item.pop(item_id, None)
        self.update_summary()

    def clear_log(self) -> None:
        self.log_area.configure(state="normal")
        self.log_area.delete("1.0", tk.END)
        self.log_area.configure(state="disabled")
        self.log_line_count = 0

    def open_selected_result(self, _event: tk.Event | None = None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        output_path = self.output_by_item.get(selection[0])
        if output_path and output_path.exists():
            self.open_path(output_path)

    def open_output_folder(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.open_path(OUTPUT_DIR)

    def open_path(self, path: Path) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as error:
            self.log(f"Could not open path: {error}")

    def on_close(self) -> None:
        self.closed = True
        self.processor.close()
        self.root.destroy()
