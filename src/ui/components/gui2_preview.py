from __future__ import annotations

import tkinter as tk

import ttkbootstrap as ttk
from PIL import Image, ImageTk
from ttkbootstrap.constants import BOTH, OUTLINE, SECONDARY, WARNING


class PreviewPanel(ttk.Labelframe):
    def __init__(self, parent, colors, on_prev, on_next, on_resize) -> None:
        super().__init__(parent, text="Vista previa", padding=10)
        self.colors = colors
        self.on_resize = on_resize
        self.preview_image: ImageTk.PhotoImage | None = None

        self.pack(fill=BOTH, expand=True)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.lbl_preview_info = ttk.Label(self, text="Selecciona una página para previsualizar", anchor="center")
        self.lbl_preview_info.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        preview_box = ttk.Frame(self)
        preview_box.grid(row=1, column=0, sticky="nsew")
        preview_box.columnconfigure(0, weight=1)
        preview_box.rowconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(preview_box, highlightthickness=0, bg=self.colors.light)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")

        preview_scroll = ttk.Scrollbar(preview_box, orient="vertical", command=self.preview_canvas.yview)
        preview_scroll.grid(row=0, column=1, sticky="ns")
        self.preview_canvas.configure(yscrollcommand=preview_scroll.set)
        self.preview_canvas.bind("<MouseWheel>", self._scroll)
        self.preview_canvas.bind("<Button-4>", self._scroll)
        self.preview_canvas.bind("<Button-5>", self._scroll)
        self.preview_canvas.bind("<Configure>", lambda e: self.on_resize())

        self.lbl_spinner = ttk.Label(self, text="", bootstyle=WARNING)
        self.lbl_spinner.grid(row=2, column=0, sticky="ew", pady=(8, 6))

        nav = ttk.Frame(self)
        nav.grid(row=3, column=0, sticky="ew")
        nav.columnconfigure(1, weight=1)

        ttk.Button(nav, text="Anterior", command=on_prev, bootstyle=SECONDARY).grid(row=0, column=0, sticky="w")
        self.lbl_nav = ttk.Label(nav, text="0 / 0", anchor="center")
        self.lbl_nav.grid(row=0, column=1, sticky="ew")
        ttk.Button(nav, text="Siguiente", command=on_next, bootstyle=SECONDARY).grid(row=0, column=2, sticky="e")

        self.clear(0)

    def _scroll(self, event) -> None:
        if event.num == 4:
            self.preview_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.preview_canvas.yview_scroll(1, "units")
        else:
            self.preview_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def clear(self, total_pages: int) -> None:
        self.preview_canvas.delete("all")
        self.preview_canvas.create_text(160, 180, text="Sin vista previa", font=("Segoe UI", 13), fill=self.colors.secondary)
        self.lbl_preview_info.configure(text="Selecciona una página para previsualizar")
        self.lbl_spinner.configure(text="")
        self.preview_image = None
        self.lbl_nav.configure(text=f"0 / {total_pages}")

    def set_page_info(self, index: int, total_pages: int) -> None:
        self.lbl_preview_info.configure(text=f"Página {index + 1} de {total_pages}")
        self.lbl_nav.configure(text=f"{index + 1} / {total_pages}")

    def set_status(self, text: str) -> None:
        self.lbl_spinner.configure(text=text)

    def display_image(self, image: Image.Image, rotation: int, fast: bool) -> None:
        if rotation:
            image = image.rotate(-rotation, expand=True)

        canvas_width = self.preview_canvas.winfo_width() or 330
        target_width = max(220, canvas_width - 10)
        ratio = target_width / image.width
        target_height = int(image.height * ratio)
        image = image.resize((target_width, target_height), Image.LANCZOS)

        tk_image = ImageTk.PhotoImage(image)
        self.preview_image = tk_image

        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, anchor="nw", image=tk_image)
        self.preview_canvas.configure(scrollregion=(0, 0, target_width, target_height))
        self.preview_canvas.yview_moveto(0)

        if not fast:
            self.lbl_spinner.configure(text="Vista previa lista")
