from __future__ import annotations

import tkinter as tk

import ttkbootstrap as ttk
from PIL import Image, ImageTk
from ttkbootstrap.constants import HORIZONTAL, INFO


class ThumbnailGrid(ttk.Frame):
    def __init__(self, parent, colors, on_select, on_preview) -> None:
        super().__init__(parent)
        self.colors = colors
        self.on_select = on_select
        self.on_preview = on_preview
        self.thumb_cache: dict[int, ImageTk.PhotoImage] = {}
        self.pages = []
        self.selected: set[int] = set()
        self.preview_index: int | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(0, weight=1)

        help_text = "Clic: seleccionar y previsualizar    Ctrl+Clic: multiselección    Doble clic: previsualizar"
        ttk.Label(toolbar, text=help_text).grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(toolbar, text="Zoom").grid(row=0, column=1, sticky="e")

        self.zoom_var = tk.IntVar(value=130)
        zoom = ttk.Scale(toolbar, from_=60, to=220, orient=HORIZONTAL, variable=self.zoom_var, command=lambda _: self._refresh())
        zoom.grid(row=0, column=2, sticky="e", padx=(8, 0))

        grid_box = ttk.Frame(self)
        grid_box.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        grid_box.columnconfigure(0, weight=1)
        grid_box.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(grid_box, highlightthickness=0, bg=self.colors.bg)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        sy = ttk.Scrollbar(grid_box, orient="vertical", command=self.canvas.yview)
        sy.grid(row=0, column=1, sticky="ns")
        sx = ttk.Scrollbar(grid_box, orient="horizontal", command=self.canvas.xview)
        sx.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

        self.inner = ttk.Frame(self.canvas)
        self.inner_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>", self._scroll)
        self.canvas.bind("<Button-4>", self._scroll)
        self.canvas.bind("<Button-5>", self._scroll)

        self.progress_box = ttk.Frame(self)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_label = ttk.Label(self.progress_box, text="Generando miniaturas")
        self.progress_bar = ttk.Progressbar(self.progress_box, variable=self.progress_var, maximum=100, bootstyle=INFO)

    def _on_resize(self, event) -> None:
        self.canvas.itemconfig(self.inner_window, width=event.width)
        self._refresh()

    def _scroll(self, event) -> None:
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def show_progress(self, visible: bool) -> None:
        if visible:
            self.progress_box.grid(row=2, column=0, sticky="ew", pady=(8, 0))
            self.progress_box.columnconfigure(0, weight=1)
            self.progress_label.grid(row=0, column=0, sticky="w")
            self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        else:
            self.progress_label.grid_remove()
            self.progress_bar.grid_remove()
            self.progress_box.grid_remove()

    def set_progress(self, value: int) -> None:
        self.progress_var.set(value)

    def render(self, pages, selected: set[int], preview_index: int | None) -> None:
        self.pages = pages
        self.selected = selected
        self.preview_index = preview_index
        self._refresh()

    def _refresh(self) -> None:
        for child in self.inner.winfo_children():
            child.destroy()
        self.thumb_cache.clear()

        if not self.pages:
            empty = ttk.Label(self.inner, text="Abre un PDF para ver sus páginas", anchor="center")
            empty.pack(expand=True, pady=120)
            return

        thumb_width = self.zoom_var.get()
        thumb_height = int(thumb_width * 1.414)
        available_width = self.canvas.winfo_width() or 700
        cols = max(1, available_width // (thumb_width + 26))

        for idx, page in enumerate(self.pages):
            row = idx // cols
            col = idx % cols
            self._make_thumb(idx, page, row, col, thumb_width, thumb_height)

    def _make_thumb(self, idx: int, page, row: int, col: int, thumb_width: int, thumb_height: int) -> None:
        selected = idx in self.selected
        previewing = idx == self.preview_index

        border = self.colors.primary if previewing else self.colors.danger if selected else self.colors.border
        background = self.colors.light

        frame = tk.Frame(self.inner, bg=background, highlightbackground=border, highlightthickness=2 if selected or previewing else 1, bd=0)
        frame.grid(row=row, column=col, padx=8, pady=8, sticky="n")

        if page.thumb:
            image = page.thumb.rotate(-page.rotation, expand=True) if page.rotation else page.thumb.copy()
            image.thumbnail((thumb_width, thumb_height), Image.LANCZOS)
            tk_image = ImageTk.PhotoImage(image)
            self.thumb_cache[idx] = tk_image
            image_label = tk.Label(frame, image=tk_image, bg=self.colors.bg, cursor="hand2")
        else:
            image_label = tk.Label(
                frame,
                text="PDF",
                bg=self.colors.bg,
                fg=self.colors.secondary,
                width=max(8, thumb_width // 10),
                height=max(8, thumb_height // 20),
                cursor="hand2",
            )
        image_label.pack(padx=4, pady=(4, 2))

        label = tk.Label(
            frame,
            text=f"Pág. {idx + 1}",
            bg=background,
            fg=self.colors.fg,
            font=("Segoe UI", 8, "bold"),
        )
        label.pack(pady=(0, 4))

        for widget in (frame, image_label, label):
            widget.bind("<Button-1>", lambda e, i=idx: self.on_select(e, i))
            widget.bind("<Double-Button-1>", lambda e, i=idx: self.on_preview(i))
