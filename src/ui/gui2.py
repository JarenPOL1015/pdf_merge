from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import ttkbootstrap as ttk
from ttkbootstrap.constants import LIGHT

from core.pdf_backend import PDFEditorBackend, PageItem
from core.pdf_renderer import close_all_fitz_docs, render_page
from ui.components.gui2_grid import ThumbnailGrid
from ui.components.gui2_preview import PreviewPanel
from ui.components.gui2_sidebar import SidebarPanel
from ui.components.gui2_topbar import render_gui2_topbar
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class PDFEditorBootstrapApp(ttk.Window):
    def __init__(self) -> None:
        super().__init__(themename="litera")
        self.title("PDF Editor Local")
        self.geometry("1400x820")
        self.minsize(1100, 700)
        self.colors = self.style.colors

        self.backend = PDFEditorBackend()
        self.preview_index: int | None = None
        self.preview_cancel = threading.Event()
        ttk.Style("cyborg")
        self.iconbitmap(resource_path("img/logo.ico"))
        self.protocol("WM_DELETE_WINDOW", self._on_close)
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

        render_gui2_topbar(self, self.open_pdf, self.insert_pdf, self.save_pdf)

        body = ttk.Frame(self, padding=12)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=0)
        body.rowconfigure(0, weight=1)

        self.sidebar = SidebarPanel(
            body,
            {
                "delete_selected": self.delete_selected,
                "move_up": self.move_up,
                "move_down": self.move_down,
                "move_to_position": self.move_to_position,
                "rotate_right": self.rotate_right,
                "rotate_left": self.rotate_left,
                "select_all": self.select_all,
                "deselect_all": self.deselect_all,
                "invert_selection": self.invert_selection,
            },
        )
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

        self.grid_panel = ThumbnailGrid(body, self.colors, self._thumb_click, self.show_preview)
        self.grid_panel.grid(row=0, column=1, sticky="nsew")

        right = ttk.Frame(body, width=360)
        right.grid(row=0, column=2, sticky="nse", padx=(12, 0))
        right.grid_propagate(False)
        self.preview_panel = PreviewPanel(right, self.colors, self._preview_prev, self._preview_next, self._redraw_preview)

        self.status_var = tk.StringVar(value="Abre un PDF para comenzar")
        status = ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(12, 8), bootstyle=LIGHT)
        status.grid(row=2, column=0, sticky="ew")

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
        self.preview_index = None
        self.preview_cancel = threading.Event()

    def _show_progress(self, visible: bool) -> None:
        self.grid_panel.show_progress(visible)

    def _status(self, message: str) -> None:
        self.status_var.set(message)
        self.update_idletasks()

    def _update_document_labels(self) -> None:
        total = len(self.pages)
        selected_count = len(self.selected)
        self.sidebar.update_document_info(total, selected_count, self.backend.get_filename())

        if self.preview_index is None or self.preview_index >= total:
            self.preview_panel.lbl_nav.configure(text=f"0 / {total}")
        else:
            self.preview_panel.lbl_nav.configure(text=f"{self.preview_index + 1} / {total}")

    def _refresh_grid(self) -> None:
        self.grid_panel.render(self.pages, self.selected, self.preview_index)
        self._update_document_labels()

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
        self.preview_panel.clear(len(self.pages))

    def show_preview(self, idx: int) -> None:
        if not self.pages or idx < 0 or idx >= len(self.pages):
            return

        self.preview_index = idx
        page = self.pages[idx]

        self.preview_panel.set_page_info(idx, len(self.pages))
        self.preview_panel.set_status("Renderizando vista previa...")

        self.preview_cancel.set()
        cancel = threading.Event()
        self.preview_cancel = cancel

        if page.thumb:
            self.preview_panel.display_image(page.thumb, page.rotation, fast=True)

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
                self.after(0, lambda: self.preview_panel.set_status("Vista previa no disponible"))
                return

            self.after(0, lambda: self.preview_panel.display_image(image, rotation, fast=False))
        except Exception as ex:
            self.after(0, lambda: self.preview_panel.set_status(f"Error: {ex}"))

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
            total = self.backend.open_pdf(path, progress_callback=lambda pct: self.after(0, lambda p=pct: self.grid_panel.set_progress(p)))
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
