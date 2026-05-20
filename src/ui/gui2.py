from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import ttkbootstrap as ttk
from PIL import Image, ImageTk
from ttkbootstrap.constants import BOTH, DANGER, HORIZONTAL, INFO, LEFT, LIGHT, OUTLINE, PRIMARY, SECONDARY, SUCCESS, WARNING, X

from core.pdf_backend import PDFEditorBackend, PageItem
from core.pdf_renderer import close_all_fitz_docs, render_page


class PDFEditorBootstrapApp(ttk.Window):
    def __init__(self) -> None:
        super().__init__(themename="litera")
        self.title("PDF Editor Local")
        self.geometry("1400x820")
        self.minsize(1100, 700)
        self.colors = self.style.colors

        self.backend = PDFEditorBackend()
        self.thumb_cache: dict[int, ImageTk.PhotoImage] = {}
        self.preview_index: int | None = None
        self.preview_image: ImageTk.PhotoImage | None = None
        self.preview_cancel = threading.Event()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        ttk.Style("superhero")
        self._build_ui()
        self._bind_keys()
        
    @property
    def pages(self) -> list[PageItem]:
        return self.backend.pages

    @property
    def selected(self) -> set[int]:
        return self.backend.selected

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_topbar()

        body = ttk.Frame(self, padding=12)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=0)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, width=240)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.grid_propagate(False)
        self._build_left_panel(left)

        center = ttk.Frame(body)
        center.grid(row=0, column=1, sticky="nsew")
        center.columnconfigure(0, weight=1)
        center.rowconfigure(1, weight=1)
        self._build_center_panel(center)

        right = ttk.Frame(body, width=360)
        right.grid(row=0, column=2, sticky="nse", padx=(12, 0))
        right.grid_propagate(False)
        self._build_preview_panel(right)

        self.status_var = tk.StringVar(value="Abre un PDF para comenzar")
        status = ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(12, 8), bootstyle=LIGHT)
        status.grid(row=2, column=0, sticky="ew")

    def _build_topbar(self) -> None:
        bar = ttk.Frame(self, padding=(12, 12, 12, 8))
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)

        title_box = ttk.Frame(bar)
        title_box.grid(row=0, column=0, sticky="w")

        ttk.Label(title_box, text="PDF Editor Local", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(title_box, text="Abrir, reordenar, rotar, insertar y guardar páginas PDF").pack(anchor="w", pady=(2, 0))

        actions = ttk.Frame(bar)
        actions.grid(row=0, column=1, sticky="e")

        ttk.Button(actions, text="Abrir PDF", command=self.open_pdf, bootstyle=PRIMARY).pack(side=LEFT, padx=4)
        ttk.Button(actions, text="Insertar PDF", command=self.insert_pdf, bootstyle=INFO).pack(side=LEFT, padx=4)
        ttk.Button(actions, text="Guardar", command=self.save_pdf, bootstyle=SUCCESS).pack(side=LEFT, padx=4)

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        ops = ttk.Labelframe(parent, text="Operaciones", padding=10)
        ops.pack(fill=X)

        ttk.Button(ops, text="Eliminar selección", command=self.delete_selected, bootstyle=DANGER).pack(fill=X, pady=3)
        ttk.Button(ops, text="Mover arriba", command=self.move_up, bootstyle=SECONDARY).pack(fill=X, pady=3)
        ttk.Button(ops, text="Mover abajo", command=self.move_down, bootstyle=SECONDARY).pack(fill=X, pady=3)
        ttk.Button(ops, text="Mover a posición", command=self.move_to_position, bootstyle=SECONDARY).pack(fill=X, pady=3)
        ttk.Button(ops, text="Rotar a la derecha", command=self.rotate_right, bootstyle=SECONDARY).pack(fill=X, pady=3)
        ttk.Button(ops, text="Rotar a la izquierda", command=self.rotate_left, bootstyle=SECONDARY).pack(fill=X, pady=3)

        sel = ttk.Labelframe(parent, text="Selección", padding=10)
        sel.pack(fill=X, pady=(12, 0))

        ttk.Button(sel, text="Seleccionar todo", command=self.select_all, bootstyle=SECONDARY).pack(fill=X, pady=3)
        ttk.Button(sel, text="Deseleccionar todo", command=self.deselect_all, bootstyle=SECONDARY).pack(fill=X, pady=3)
        ttk.Button(sel, text="Invertir selección", command=self.invert_selection, bootstyle=SECONDARY).pack(fill=X, pady=3)

        doc = ttk.Labelframe(parent, text="Documento", padding=10)
        doc.pack(fill=X, pady=(12, 0))

        self.lbl_pages = ttk.Label(doc, text="0", font=("Segoe UI", 24, "bold"), bootstyle=PRIMARY)
        self.lbl_pages.pack(anchor="center")
        ttk.Label(doc, text="páginas totales").pack(anchor="center")

        self.lbl_sel = ttk.Label(doc, text="0 seleccionadas", bootstyle=WARNING)
        self.lbl_sel.pack(anchor="center", pady=(8, 0))

        self.lbl_fname = ttk.Label(doc, text="", wraplength=200, justify=LEFT)
        self.lbl_fname.pack(anchor="w", pady=(10, 0))

    def _build_center_panel(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(0, weight=1)

        help_text = "Clic: seleccionar y previsualizar    Ctrl+Clic: multiselección    Doble clic: previsualizar"
        ttk.Label(toolbar, text=help_text).grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(toolbar, text="Zoom").grid(row=0, column=1, sticky="e")

        self.zoom_var = tk.IntVar(value=130)
        zoom = ttk.Scale(toolbar, from_=60, to=220, orient=HORIZONTAL, variable=self.zoom_var, command=lambda _: self._refresh_grid())
        zoom.grid(row=0, column=2, sticky="e", padx=(8, 0))

        grid_box = ttk.Frame(parent)
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
        self.canvas.bind("<Configure>", self._on_grid_resize)
        self.canvas.bind("<MouseWheel>", self._grid_scroll)
        self.canvas.bind("<Button-4>", self._grid_scroll)
        self.canvas.bind("<Button-5>", self._grid_scroll)

        self.progress_box = ttk.Frame(parent)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_label = ttk.Label(self.progress_box, text="Generando miniaturas")
        self.progress_bar = ttk.Progressbar(self.progress_box, variable=self.progress_var, maximum=100, bootstyle=INFO)

    def _build_preview_panel(self, parent: ttk.Frame) -> None:
        card = ttk.Labelframe(parent, text="Vista previa", padding=10)
        card.pack(fill=BOTH, expand=True)
        card.rowconfigure(1, weight=1)
        card.columnconfigure(0, weight=1)

        self.lbl_preview_info = ttk.Label(card, text="Selecciona una página para previsualizar", anchor="center")
        self.lbl_preview_info.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        preview_box = ttk.Frame(card)
        preview_box.grid(row=1, column=0, sticky="nsew")
        preview_box.columnconfigure(0, weight=1)
        preview_box.rowconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(preview_box, highlightthickness=0, bg=self.colors.light)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")

        preview_scroll = ttk.Scrollbar(preview_box, orient="vertical", command=self.preview_canvas.yview)
        preview_scroll.grid(row=0, column=1, sticky="ns")
        self.preview_canvas.configure(yscrollcommand=preview_scroll.set)
        self.preview_canvas.bind("<MouseWheel>", self._preview_scroll)
        self.preview_canvas.bind("<Button-4>", self._preview_scroll)
        self.preview_canvas.bind("<Button-5>", self._preview_scroll)
        self.preview_canvas.bind("<Configure>", lambda e: self._redraw_preview())

        self.preview_canvas.create_text(
            160,
            180,
            text="Sin vista previa",
            font=("Segoe UI", 13),
            fill=self.colors.secondary,
        )

        self.lbl_spinner = ttk.Label(card, text="", bootstyle=WARNING)
        self.lbl_spinner.grid(row=2, column=0, sticky="ew", pady=(8, 6))

        nav = ttk.Frame(card)
        nav.grid(row=3, column=0, sticky="ew")
        nav.columnconfigure(1, weight=1)

        ttk.Button(nav, text="Anterior", command=self._preview_prev, bootstyle=SECONDARY).grid(row=0, column=0, sticky="w")
        self.lbl_nav = ttk.Label(nav, text="0 / 0", anchor="center")
        self.lbl_nav.grid(row=0, column=1, sticky="ew")
        ttk.Button(nav, text="Siguiente", command=self._preview_next, bootstyle=SECONDARY).grid(row=0, column=2, sticky="e")

    def _bind_keys(self) -> None:
        self.bind("<Delete>", lambda e: self.delete_selected())
        self.bind("<Control-a>", lambda e: self.select_all())
        self.bind("<Control-s>", lambda e: self.save_pdf())
        self.bind("<Control-o>", lambda e: self.open_pdf())
        self.bind("<Left>", lambda e: self._preview_prev())
        self.bind("<Right>", lambda e: self._preview_next())

    def _on_close(self) -> None:
        self.preview_cancel.set()
        close_all_fitz_docs()
        self.destroy()

    def _reset_session(self) -> None:
        self.preview_cancel.set()
        close_all_fitz_docs()
        self.backend.reset_document()
        self.thumb_cache.clear()
        self.preview_index = None
        self.preview_image = None
        self.preview_cancel = threading.Event()

    def _on_grid_resize(self, event) -> None:
        self.canvas.itemconfig(self.inner_window, width=event.width)
        self._refresh_grid()

    def _grid_scroll(self, event) -> None:
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _preview_scroll(self, event) -> None:
        if event.num == 4:
            self.preview_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.preview_canvas.yview_scroll(1, "units")
        else:
            self.preview_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _show_progress(self, visible: bool) -> None:
        if visible:
            self.progress_box.grid(row=2, column=0, sticky="ew", pady=(8, 0))
            self.progress_box.columnconfigure(0, weight=1)
            self.progress_label.grid(row=0, column=0, sticky="w")
            self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        else:
            self.progress_label.grid_remove()
            self.progress_bar.grid_remove()
            self.progress_box.grid_remove()

    def _status(self, message: str) -> None:
        self.status_var.set(message)
        self.update_idletasks()

    def _update_document_labels(self) -> None:
        total = len(self.pages)
        selected_count = len(self.selected)

        self.lbl_pages.configure(text=str(total))
        suffix = "seleccionada" if selected_count == 1 else "seleccionadas"
        self.lbl_sel.configure(text=f"{selected_count} {suffix}")
        self.lbl_fname.configure(text=self.backend.get_filename())

        if self.preview_index is None or self.preview_index >= total:
            self.lbl_nav.configure(text=f"0 / {total}")
        else:
            self.lbl_nav.configure(text=f"{self.preview_index + 1} / {total}")

    def _refresh_grid(self) -> None:
        for child in self.inner.winfo_children():
            child.destroy()
        self.thumb_cache.clear()

        if not self.pages:
            empty = ttk.Label(self.inner, text="Abre un PDF para ver sus páginas", anchor="center")
            empty.pack(expand=True, pady=120)
            self._update_document_labels()
            return

        thumb_width = self.zoom_var.get()
        thumb_height = int(thumb_width * 1.414)
        available_width = self.canvas.winfo_width() or 700
        cols = max(1, available_width // (thumb_width + 26))

        for idx, page in enumerate(self.pages):
            row = idx // cols
            col = idx % cols
            self._make_thumb(idx, page, row, col, thumb_width, thumb_height)

        self._update_document_labels()

    def _make_thumb(self, idx: int, page: PageItem, row: int, col: int, thumb_width: int, thumb_height: int) -> None:
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
            widget.bind("<Button-1>", lambda e, i=idx: self._thumb_click(e, i))
            widget.bind("<Double-Button-1>", lambda e, i=idx: self.show_preview(i))

    def _thumb_click(self, event, idx: int) -> None:
        ctrl = (event.state & 0x4) != 0
        shift = (event.state & 0x1) != 0

        if ctrl:
            self.backend.toggle_selection(idx)
        elif shift:
            self.backend.select_range_from_last(idx)
        else:
            self.backend.set_single_selection(idx)
            self.show_preview(idx)

        self._refresh_grid()

    def _clear_preview(self) -> None:
        self.preview_canvas.delete("all")
        self.preview_canvas.create_text(160, 180, text="Sin vista previa", font=("Segoe UI", 13), fill=self.colors.secondary)
        self.lbl_preview_info.configure(text="Selecciona una página para previsualizar")
        self.lbl_spinner.configure(text="")
        self.preview_image = None
        self.lbl_nav.configure(text=f"0 / {len(self.pages)}")

    def show_preview(self, idx: int) -> None:
        if not self.pages or idx < 0 or idx >= len(self.pages):
            return

        self.preview_index = idx
        page = self.pages[idx]

        self.lbl_preview_info.configure(text=f"Página {idx + 1} de {len(self.pages)}")
        self.lbl_nav.configure(text=f"{idx + 1} / {len(self.pages)}")
        self.lbl_spinner.configure(text="Renderizando vista previa...")

        self.preview_cancel.set()
        cancel = threading.Event()
        self.preview_cancel = cancel

        if page.thumb:
            self._display_preview(page.thumb, page.rotation, fast=True)

        threading.Thread(
            target=self._preview_worker,
            args=(page.from_file, page.original_index, page.rotation, cancel),
            daemon=True,
        ).start()

    def _preview_worker(self, pdf_path: str, page_index: int, rotation: int, cancel: threading.Event) -> None:
        try:
            image = render_page(pdf_path, page_index, dpi=130)
            if cancel.is_set():
                return

            if image is None:
                self.after(0, lambda: self.lbl_spinner.configure(text="Vista previa no disponible"))
                return

            self.after(0, lambda: self._display_preview(image, rotation, fast=False))
        except Exception as ex:
            self.after(0, lambda: self.lbl_spinner.configure(text=f"Error: {ex}"))

    def _display_preview(self, image: Image.Image, rotation: int, fast: bool) -> None:
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
            self.after(2000, lambda: self.lbl_spinner.configure(text=""))

    def _redraw_preview(self) -> None:
        if self.preview_index is not None:
            self.show_preview(self.preview_index)

    def _preview_prev(self) -> None:
        if self.preview_index is not None and self.preview_index > 0:
            self.show_preview(self.preview_index - 1)

    def _preview_next(self) -> None:
        if self.preview_index is not None and self.preview_index < len(self.pages) - 1:
            self.show_preview(self.preview_index + 1)

    def _require_pdf(self) -> bool:
        if self.backend.has_document:
            return True
        messagebox.showwarning("Sin PDF", "Primero abre un PDF.")
        return False

    def _require_selection(self) -> bool:
        if self.backend.has_selection:
            return True
        messagebox.showwarning("Sin selección", "Selecciona al menos una página.")
        return False

    def open_pdf(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not path:
            return

        self._reset_session()
        self._clear_preview()
        self._show_progress(True)
        self._status(f"Cargando {Path(path).name}...")
        threading.Thread(target=self._load_worker, args=(path,), daemon=True).start()

    def _load_worker(self, path: str) -> None:
        try:
            total = self.backend.open_pdf(path, progress_callback=lambda pct: self.after(0, lambda p=pct: self.progress_var.set(p)))
            self.after(0, lambda: self._load_done(total))
        except Exception as ex:
            self.after(0, lambda: self._show_progress(False))
            self.after(0, lambda: messagebox.showerror("Error al abrir", f"No se pudo abrir el PDF:\n{ex}"))

    def _load_done(self, total: int) -> None:
        self._show_progress(False)
        self._refresh_grid()
        self._status(f"Cargado {self.backend.get_filename()} con {total} páginas")
        if self.pages:
            self.show_preview(0)

    def delete_selected(self) -> None:
        if not self._require_pdf() or not self._require_selection():
            return

        total = len(self.selected)
        if not messagebox.askyesno("Confirmar", f"¿Eliminar {total} página(s) seleccionada(s)?"):
            return

        self.backend.delete_selected()
        self.preview_index = min(self.preview_index or 0, max(0, len(self.pages) - 1)) if self.pages else None
        self._refresh_grid()

        if self.preview_index is not None and self.pages:
            self.show_preview(self.preview_index)
        else:
            self._clear_preview()

        self._status(f"Se eliminaron {total} página(s)")

    def move_up(self) -> None:
        if not self._require_pdf() or not self._require_selection():
            return

        if not self.backend.move_up():
            return

        if self.preview_index is not None:
            self.preview_index = max(0, self.preview_index - 1)
        self._refresh_grid()

    def move_down(self) -> None:
        if not self._require_pdf() or not self._require_selection():
            return

        if not self.backend.move_down():
            return

        if self.preview_index is not None:
            self.preview_index = min(len(self.pages) - 1, self.preview_index + 1)
        self._refresh_grid()

    def move_to_position(self) -> None:
        if not self._require_pdf() or not self._require_selection():
            return

        index = self.backend.get_single_selected_index()
        if index is None:
            messagebox.showinfo("Mover página", "Selecciona exactamente una página para mover.")
            return

        destination = simpledialog.askinteger(
            "Mover página",
            f"Mover la página {index + 1} a la posición (1-{len(self.pages)})",
            minvalue=1,
            maxvalue=len(self.pages),
            parent=self,
        )
        if destination is None:
            return

        destination -= 1
        self.backend.move_to_position(index, destination)
        self.preview_index = destination
        self._refresh_grid()
        self.show_preview(destination)
        self._status(f"Página movida a la posición {destination + 1}")

    def rotate_right(self) -> None:
        self._rotate(90)

    def rotate_left(self) -> None:
        self._rotate(-90)

    def _rotate(self, degrees: int) -> None:
        if not self._require_pdf() or not self._require_selection():
            return

        count = self.backend.rotate_selected(degrees)
        self._refresh_grid()
        if self.preview_index in self.selected:
            self.show_preview(self.preview_index)
        self._status(f"Rotación {degrees:+} aplicada a {count} página(s)")

    def select_all(self) -> None:
        self.backend.select_all()
        self._refresh_grid()

    def deselect_all(self) -> None:
        self.backend.deselect_all()
        self._refresh_grid()

    def invert_selection(self) -> None:
        self.backend.invert_selection()
        self._refresh_grid()

    def insert_pdf(self) -> None:
        if not self._require_pdf():
            return

        path = filedialog.askopenfilename(
            title="Seleccionar PDF a insertar",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not path:
            return

        position = simpledialog.askinteger(
            "Insertar PDF",
            f"Insertar en la posición (1-{len(self.pages) + 1})",
            minvalue=1,
            maxvalue=len(self.pages) + 1,
            parent=self,
        )
        if position is None:
            return

        self._status("Cargando PDF a insertar...")
        threading.Thread(target=self._insert_worker, args=(path, position - 1), daemon=True).start()

    def _insert_worker(self, path: str, position: int) -> None:
        try:
            total = self.backend.insert_pdf(path, position)
            self.after(0, self._refresh_grid)
            self.after(0, lambda: self.show_preview(position))
            self.after(0, lambda: self._status(f"Insertadas {total} página(s) desde {Path(path).name}"))
        except Exception as ex:
            self.after(0, lambda: messagebox.showerror("Error al insertar", f"No se pudo insertar el PDF:\n{ex}"))

    def save_pdf(self) -> None:
        if not self._require_pdf():
            return
        if not self.pages:
            messagebox.showwarning("Vacío", "No hay páginas para guardar.")
            return

        path = filedialog.asksaveasfilename(
            title="Guardar PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"editado_{self.backend.get_filename()}",
        )
        if not path:
            return

        self._status("Guardando PDF...")
        threading.Thread(target=self._save_worker, args=(path,), daemon=True).start()

    def _save_worker(self, output_path: str) -> None:
        try:
            self.backend.save_pdf(output_path)
            self.after(0, lambda: self._status(f"Guardado {Path(output_path).name}"))
            self.after(0, lambda: messagebox.showinfo("Guardado", f"PDF guardado correctamente:\n{output_path}"))
        except Exception as ex:
            self.after(0, lambda: messagebox.showerror("Error al guardar", f"No se pudo guardar el PDF:\n{ex}"))


if __name__ == "__main__":
    app = PDFEditorBootstrapApp()
    app.mainloop()
