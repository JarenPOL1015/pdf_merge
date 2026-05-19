#!/usr/bin/env python3
"""
PDF Editor Local - Herramienta privada para gestionar páginas de PDFs
Funciones: cargar PDF, visualizar páginas, mover/eliminar páginas, insertar otro PDF
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import os
import tempfile
import shutil
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
    from PIL import Image, ImageTk
    from pdf2image import convert_from_path
except ImportError as e:
    print(f"Dependencia faltante: {e}")
    print("Instala con: pip install pypdf pillow pdf2image")
    exit(1)


# ─────────────────────────────────────────────
#  COLORES Y ESTILOS
# ─────────────────────────────────────────────
BG_DARK      = "#1a1a2e"
BG_CARD      = "#16213e"
BG_PANEL     = "#0f3460"
ACCENT       = "#e94560"
ACCENT_HOVER = "#c73652"
TEXT_WHITE   = "#eaeaea"
TEXT_GRAY    = "#a0aec0"
GREEN        = "#48bb78"
YELLOW       = "#ecc94b"
THUMB_BG     = "#1e2a45"
THUMB_SEL    = "#e94560"
BORDER       = "#2d3748"


class PDFEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Editor Local  🔒  100% Privado")
        self.geometry("1200x780")
        self.minsize(900, 600)
        self.configure(bg=BG_DARK)

        # Estado
        self.pdf_path: str | None = None
        self.pages: list[dict] = []        # [{index, thumb, selected}, ...]
        self.selected: set[int] = set()    # índices seleccionados
        self.thumb_cache: dict[int, ImageTk.PhotoImage] = {}
        self.loading = False
        self._drag_start: int | None = None

        self._build_ui()
        self._bind_keys()

    # ──────────────────────────────────────────
    #  CONSTRUCCIÓN DE UI
    # ──────────────────────────────────────────
    def _build_ui(self):
        # Barra superior
        topbar = tk.Frame(self, bg=BG_PANEL, height=56)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="📄 PDF Editor Local", font=("Segoe UI", 16, "bold"),
                 bg=BG_PANEL, fg=TEXT_WHITE).pack(side="left", padx=18, pady=10)

        tk.Label(topbar, text="🔒 Sin conexión · 100% privado",
                 font=("Segoe UI", 9), bg=BG_PANEL, fg=GREEN).pack(side="left", padx=6)

        # Botones barra superior
        btn_frame = tk.Frame(topbar, bg=BG_PANEL)
        btn_frame.pack(side="right", padx=12)

        self._topbtn(btn_frame, "📂 Abrir PDF",   self.open_pdf,   ACCENT)
        self._topbtn(btn_frame, "➕ Insertar PDF", self.insert_pdf, "#2b6cb0")
        self._topbtn(btn_frame, "💾 Guardar",       self.save_pdf,   GREEN)

        # Contenedor principal
        main = tk.Frame(self, bg=BG_DARK)
        main.pack(fill="both", expand=True)

        # ── Panel izquierdo: controles ──
        left = tk.Frame(main, bg=BG_CARD, width=220)
        left.pack(side="left", fill="y", padx=(10, 0), pady=10)
        left.pack_propagate(False)
        self._build_left_panel(left)

        # ── Panel central: páginas ──
        center = tk.Frame(main, bg=BG_DARK)
        center.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self._build_center(center)

        # Barra de estado
        self.statusbar = tk.Label(self, text="Abre un PDF para comenzar",
                                  font=("Segoe UI", 9), bg=BG_PANEL,
                                  fg=TEXT_GRAY, anchor="w", padx=12)
        self.statusbar.pack(fill="x", side="bottom")

    def _topbtn(self, parent, text, cmd, color):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=color, fg="white", relief="flat",
                      font=("Segoe UI", 9, "bold"), cursor="hand2",
                      padx=12, pady=6, bd=0)
        b.pack(side="left", padx=4, pady=8)
        b.bind("<Enter>", lambda e: b.config(bg=self._darken(color)))
        b.bind("<Leave>", lambda e: b.config(bg=color))
        return b

    def _darken(self, hex_color):
        r, g, b = int(hex_color[1:3],16), int(hex_color[3:5],16), int(hex_color[5:7],16)
        r, g, b = max(0,r-30), max(0,g-30), max(0,b-30)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _build_left_panel(self, parent):
        tk.Label(parent, text="OPERACIONES", font=("Segoe UI", 8, "bold"),
                 bg=BG_CARD, fg=TEXT_GRAY).pack(anchor="w", padx=14, pady=(16,4))

        ops = [
            ("🗑️  Eliminar selección",   self.delete_selected,  ACCENT),
            ("⬆️  Mover arriba",          self.move_up,          BG_PANEL),
            ("⬇️  Mover abajo",           self.move_down,        BG_PANEL),
            ("↕️  Mover a posición…",     self.move_to_position, BG_PANEL),
            ("🔄  Rotar 90° →",           self.rotate_right,     BG_PANEL),
            ("🔄  Rotar 90° ←",           self.rotate_left,      BG_PANEL),
        ]
        for label, cmd, color in ops:
            b = tk.Button(parent, text=label, command=cmd,
                          bg=color, fg=TEXT_WHITE, relief="flat",
                          font=("Segoe UI", 9), cursor="hand2",
                          anchor="w", padx=10, pady=7, bd=0)
            b.pack(fill="x", padx=10, pady=2)

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=10, pady=12)

        tk.Label(parent, text="SELECCIÓN", font=("Segoe UI", 8, "bold"),
                 bg=BG_CARD, fg=TEXT_GRAY).pack(anchor="w", padx=14, pady=(0,4))

        sel_ops = [
            ("✅  Seleccionar todo",    self.select_all),
            ("⬜  Deseleccionar todo",  self.deselect_all),
            ("🔁  Invertir selección",  self.invert_selection),
        ]
        for label, cmd in sel_ops:
            b = tk.Button(parent, text=label, command=cmd,
                          bg=BG_CARD, fg=TEXT_WHITE, relief="flat",
                          font=("Segoe UI", 9), cursor="hand2",
                          anchor="w", padx=10, pady=6, bd=0)
            b.pack(fill="x", padx=10, pady=1)

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=10, pady=12)

        # Info del documento
        tk.Label(parent, text="DOCUMENTO", font=("Segoe UI", 8, "bold"),
                 bg=BG_CARD, fg=TEXT_GRAY).pack(anchor="w", padx=14, pady=(0,4))

        self.lbl_pages = tk.Label(parent, text="—", font=("Segoe UI", 20, "bold"),
                                  bg=BG_CARD, fg=ACCENT)
        self.lbl_pages.pack(pady=(4,0))
        tk.Label(parent, text="páginas totales", font=("Segoe UI", 8),
                 bg=BG_CARD, fg=TEXT_GRAY).pack()

        self.lbl_sel_count = tk.Label(parent, text="0 seleccionadas",
                                      font=("Segoe UI", 9), bg=BG_CARD, fg=YELLOW)
        self.lbl_sel_count.pack(pady=(6,0))

        self.lbl_filename = tk.Label(parent, text="", font=("Segoe UI", 8),
                                     bg=BG_CARD, fg=TEXT_GRAY, wraplength=190)
        self.lbl_filename.pack(pady=(4,0), padx=10)

    def _build_center(self, parent):
        # Barra de herramientas de la vista
        toolbar = tk.Frame(parent, bg=BG_CARD, height=36)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="Vista de páginas — Ctrl+clic para multiselección",
                 font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_GRAY).pack(side="left", padx=12, pady=8)

        # Zoom
        tk.Label(toolbar, text="Zoom:", font=("Segoe UI", 8),
                 bg=BG_CARD, fg=TEXT_GRAY).pack(side="right", padx=(0,4), pady=8)
        self.zoom_var = tk.IntVar(value=130)
        zoom_scale = ttk.Scale(toolbar, from_=60, to=220, variable=self.zoom_var,
                               orient="horizontal", length=100,
                               command=lambda _: self._refresh_grid())
        zoom_scale.pack(side="right", padx=(0,12), pady=6)

        # Canvas con scroll
        canvas_frame = tk.Frame(parent, bg=BG_DARK)
        canvas_frame.pack(fill="both", expand=True, pady=(6,0))

        self.canvas = tk.Canvas(canvas_frame, bg=BG_DARK, highlightthickness=0)
        scrollbar_y = ttk.Scrollbar(canvas_frame, orient="vertical",
                                    command=self.canvas.yview)
        scrollbar_x = ttk.Scrollbar(canvas_frame, orient="horizontal",
                                    command=self.canvas.xview)

        self.canvas.configure(yscrollcommand=scrollbar_y.set,
                              xscrollcommand=scrollbar_x.set)

        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)

        # Frame interior del canvas
        self.inner = tk.Frame(self.canvas, bg=BG_DARK)
        self.canvas_window = self.canvas.create_window((0,0), window=self.inner,
                                                        anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<MouseWheel>",   self._on_mousewheel)
        self.canvas.bind("<Button-4>",     self._on_mousewheel)
        self.canvas.bind("<Button-5>",     self._on_mousewheel)

        # Placeholder
        self.placeholder = tk.Label(self.inner,
                                    text="📂\n\nAbre un PDF para ver sus páginas",
                                    font=("Segoe UI", 14), bg=BG_DARK,
                                    fg=TEXT_GRAY, justify="center")
        self.placeholder.pack(expand=True, pady=120)

        # Progress bar (oculta por defecto)
        self.progress_frame = tk.Frame(parent, bg=BG_DARK)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var,
                                             maximum=100, length=400)
        self.progress_label = tk.Label(self.progress_frame, text="Cargando páginas…",
                                       font=("Segoe UI", 9), bg=BG_DARK, fg=TEXT_GRAY)

    # ──────────────────────────────────────────
    #  EVENTOS
    # ──────────────────────────────────────────
    def _bind_keys(self):
        self.bind("<Delete>",       lambda e: self.delete_selected())
        self.bind("<Control-a>",    lambda e: self.select_all())
        self.bind("<Control-s>",    lambda e: self.save_pdf())
        self.bind("<Control-o>",    lambda e: self.open_pdf())

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    # ──────────────────────────────────────────
    #  ABRIR PDF
    # ──────────────────────────────────────────
    def open_pdf(self):
        path = filedialog.askopenfilename(
            title="Seleccionar PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not path:
            return
        self.pdf_path = path
        self.pages.clear()
        self.selected.clear()
        self.thumb_cache.clear()
        self._load_pdf_async(path)

    def _load_pdf_async(self, path):
        self.loading = True
        self._show_progress(True)
        self.status(f"Cargando {Path(path).name}…")
        thread = threading.Thread(target=self._load_pdf_worker, args=(path,), daemon=True)
        thread.start()

    def _load_pdf_worker(self, path):
        try:
            reader = PdfReader(path)
            n = len(reader.pages)
            # Genera miniaturas
            dpi = 72
            try:
                images = convert_from_path(path, dpi=dpi, fmt="jpeg",
                                           thread_count=2)
            except Exception:
                images = [None] * n

            self.pages = []
            for i in range(n):
                img = images[i] if i < len(images) else None
                self.pages.append({
                    "original_index": i,
                    "rotation": 0,
                    "image": img,
                })
                pct = int((i+1)/n*100)
                self.after(0, lambda p=pct: self.progress_var.set(p))

            self.after(0, self._on_load_complete)
        except Exception as ex:
            self.after(0, lambda: messagebox.showerror("Error", f"No se pudo abrir el PDF:\n{ex}"))
            self.after(0, lambda: self._show_progress(False))
            self.loading = False

    def _on_load_complete(self):
        self.loading = False
        self._show_progress(False)
        self._refresh_grid()
        name = Path(self.pdf_path).name
        self.lbl_filename.config(text=name)
        self.lbl_pages.config(text=str(len(self.pages)))
        self.status(f"✅ {name} — {len(self.pages)} páginas cargadas")

    # ──────────────────────────────────────────
    #  PROGRESO
    # ──────────────────────────────────────────
    def _show_progress(self, show: bool):
        if show:
            self.progress_frame.pack(fill="x", pady=4)
            self.progress_label.pack()
            self.progress_bar.pack(pady=2)
        else:
            self.progress_bar.pack_forget()
            self.progress_label.pack_forget()
            self.progress_frame.pack_forget()

    # ──────────────────────────────────────────
    #  GRID DE MINIATURAS
    # ──────────────────────────────────────────
    def _refresh_grid(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.thumb_cache.clear()

        if not self.pages:
            self.placeholder = tk.Label(self.inner,
                                        text="📂\n\nAbre un PDF para ver sus páginas",
                                        font=("Segoe UI", 14), bg=BG_DARK,
                                        fg=TEXT_GRAY, justify="center")
            self.placeholder.pack(expand=True, pady=120)
            return

        thumb_w = self.zoom_var.get()
        thumb_h = int(thumb_w * 1.414)   # proporción A4
        cols = max(1, (self.canvas.winfo_width() or 800) // (thumb_w + 24))

        for idx, page in enumerate(self.pages):
            col = idx % cols
            row = idx // cols
            self._create_thumb(idx, page, row, col, thumb_w, thumb_h)

        self.lbl_pages.config(text=str(len(self.pages)))
        self._update_selection_label()

    def _create_thumb(self, idx, page, row, col, thumb_w, thumb_h):
        selected = idx in self.selected
        frame = tk.Frame(self.inner,
                         bg=THUMB_SEL if selected else THUMB_BG,
                         bd=0, relief="flat",
                         highlightbackground=THUMB_SEL if selected else BORDER,
                         highlightthickness=2 if selected else 1)
        frame.grid(row=row, column=col, padx=8, pady=8, sticky="n")

        # Miniatura
        img = page.get("image")
        tk_img = None
        if img:
            rot = page.get("rotation", 0)
            if rot:
                img = img.rotate(-rot, expand=True)
            img_resized = img.copy()
            img_resized.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(img_resized)
            self.thumb_cache[idx] = tk_img
            lbl_img = tk.Label(frame, image=tk_img, bg=THUMB_BG, cursor="hand2")
            lbl_img.pack(padx=4, pady=(4,2))
        else:
            placeholder = tk.Label(frame, text="📄",
                                   font=("Segoe UI", 28), bg=THUMB_BG,
                                   width=thumb_w//10, height=thumb_h//20,
                                   cursor="hand2")
            placeholder.pack(padx=4, pady=(4,2))
            lbl_img = placeholder

        # Número de página
        lbl_num = tk.Label(frame, text=f"Pág. {idx+1}",
                           font=("Segoe UI", 8, "bold"),
                           bg=THUMB_SEL if selected else THUMB_BG,
                           fg=TEXT_WHITE if selected else TEXT_GRAY)
        lbl_num.pack(pady=(0,4))

        # Eventos de clic
        for widget in (frame, lbl_img, lbl_num):
            widget.bind("<Button-1>", lambda e, i=idx: self._on_thumb_click(e, i))
            widget.bind("<Double-Button-1>", lambda e, i=idx: self._preview_page(i))

    def _on_thumb_click(self, event, idx):
        ctrl = (event.state & 0x4) != 0
        shift = (event.state & 0x1) != 0

        if ctrl:
            if idx in self.selected:
                self.selected.discard(idx)
            else:
                self.selected.add(idx)
        elif shift and self.selected:
            last = max(self.selected)
            start, end = min(last, idx), max(last, idx)
            for i in range(start, end+1):
                self.selected.add(i)
        else:
            if self.selected == {idx}:
                self.selected.clear()
            else:
                self.selected = {idx}

        self._refresh_grid()

    # ──────────────────────────────────────────
    #  PREVIEW DE PÁGINA
    # ──────────────────────────────────────────
    def _preview_page(self, idx):
        page = self.pages[idx]
        img = page.get("image")
        if not img:
            messagebox.showinfo("Vista previa", "No hay vista previa disponible para esta página.")
            return

        win = tk.Toplevel(self)
        win.title(f"Vista previa — Página {idx+1}")
        win.configure(bg=BG_DARK)
        win.geometry("700x900")

        rot = page.get("rotation", 0)
        if rot:
            img = img.rotate(-rot, expand=True)

        img_copy = img.copy()
        img_copy.thumbnail((660, 860), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img_copy)

        lbl = tk.Label(win, image=tk_img, bg=BG_DARK)
        lbl.image = tk_img
        lbl.pack(expand=True, pady=10)

        tk.Button(win, text="Cerrar", command=win.destroy,
                  bg=ACCENT, fg="white", relief="flat",
                  font=("Segoe UI", 10), padx=16, pady=6).pack(pady=6)

    # ──────────────────────────────────────────
    #  OPERACIONES DE PÁGINA
    # ──────────────────────────────────────────
    def _require_pdf(self):
        if not self.pages:
            messagebox.showwarning("Sin PDF", "Primero abre un archivo PDF.")
            return False
        return True

    def _require_selection(self):
        if not self.selected:
            messagebox.showwarning("Sin selección",
                                   "Selecciona al menos una página primero.\n"
                                   "Clic = seleccionar · Ctrl+clic = múltiple")
            return False
        return True

    def delete_selected(self):
        if not self._require_pdf() or not self._require_selection():
            return
        n = len(self.selected)
        if not messagebox.askyesno("Confirmar",
                                   f"¿Eliminar {n} página(s) seleccionada(s)?"):
            return
        self.pages = [p for i, p in enumerate(self.pages) if i not in self.selected]
        self.selected.clear()
        self._refresh_grid()
        self.status(f"✅ {n} página(s) eliminada(s)")

    def move_up(self):
        if not self._require_pdf() or not self._require_selection():
            return
        sorted_sel = sorted(self.selected)
        if sorted_sel[0] == 0:
            return
        for i in sorted_sel:
            self.pages[i-1], self.pages[i] = self.pages[i], self.pages[i-1]
        self.selected = {i-1 for i in self.selected}
        self._refresh_grid()

    def move_down(self):
        if not self._require_pdf() or not self._require_selection():
            return
        sorted_sel = sorted(self.selected, reverse=True)
        if sorted_sel[0] == len(self.pages)-1:
            return
        for i in sorted_sel:
            self.pages[i+1], self.pages[i] = self.pages[i], self.pages[i+1]
        self.selected = {i+1 for i in self.selected}
        self._refresh_grid()

    def move_to_position(self):
        if not self._require_pdf() or not self._require_selection():
            return
        if len(self.selected) > 1:
            messagebox.showinfo("Aviso",
                "Para mover a posición específica, selecciona una sola página.")
            return
        idx = next(iter(self.selected))
        dest = simpledialog.askinteger(
            "Mover página",
            f"Página {idx+1} → ¿Mover a qué posición? (1–{len(self.pages)})",
            minvalue=1, maxvalue=len(self.pages), parent=self
        )
        if dest is None:
            return
        dest -= 1  # 0-based
        page = self.pages.pop(idx)
        self.pages.insert(dest, page)
        self.selected = {dest}
        self._refresh_grid()
        self.status(f"✅ Página movida a posición {dest+1}")

    def rotate_right(self):
        self._rotate(90)

    def rotate_left(self):
        self._rotate(-90)

    def _rotate(self, degrees):
        if not self._require_pdf() or not self._require_selection():
            return
        for i in self.selected:
            self.pages[i]["rotation"] = (self.pages[i].get("rotation", 0) + degrees) % 360
        self._refresh_grid()
        self.status(f"✅ Rotación aplicada a {len(self.selected)} página(s)")

    def select_all(self):
        self.selected = set(range(len(self.pages)))
        self._refresh_grid()

    def deselect_all(self):
        self.selected.clear()
        self._refresh_grid()

    def invert_selection(self):
        all_idx = set(range(len(self.pages)))
        self.selected = all_idx - self.selected
        self._refresh_grid()

    def _update_selection_label(self):
        n = len(self.selected)
        self.lbl_sel_count.config(text=f"{n} seleccionada{'s' if n!=1 else ''}")

    # ──────────────────────────────────────────
    #  INSERTAR PDF
    # ──────────────────────────────────────────
    def insert_pdf(self):
        if not self._require_pdf():
            return

        path = filedialog.askopenfilename(
            title="Seleccionar PDF a insertar",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return

        # Preguntar posición
        pos = simpledialog.askinteger(
            "Insertar PDF",
            f"¿Insertar el nuevo PDF en qué posición? (1–{len(self.pages)+1})\n"
            f"[1 = al inicio, {len(self.pages)+1} = al final]",
            minvalue=1, maxvalue=len(self.pages)+1, parent=self
        )
        if pos is None:
            return
        pos -= 1  # 0-based

        self.status(f"Cargando PDF a insertar…")
        thread = threading.Thread(
            target=self._insert_pdf_worker,
            args=(path, pos), daemon=True
        )
        thread.start()

    def _insert_pdf_worker(self, path, pos):
        try:
            reader = PdfReader(path)
            n = len(reader.pages)
            try:
                images = convert_from_path(path, dpi=72, fmt="jpeg", thread_count=2)
            except Exception:
                images = [None] * n

            new_pages = []
            for i in range(n):
                img = images[i] if i < len(images) else None
                new_pages.append({
                    "original_index": i,
                    "rotation": 0,
                    "image": img,
                    "from_file": path,
                })

            self.pages[pos:pos] = new_pages
            self.selected = set(range(pos, pos + n))
            self.after(0, self._refresh_grid)
            self.after(0, lambda: self.status(
                f"✅ {n} páginas de «{Path(path).name}» insertadas en posición {pos+1}"))
        except Exception as ex:
            self.after(0, lambda: messagebox.showerror(
                "Error", f"No se pudo insertar el PDF:\n{ex}"))

    # ──────────────────────────────────────────
    #  GUARDAR PDF
    # ──────────────────────────────────────────
    def save_pdf(self):
        if not self._require_pdf():
            return
        if not self.pages:
            messagebox.showwarning("Vacío", "No hay páginas para guardar.")
            return

        path = filedialog.asksaveasfilename(
            title="Guardar PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"editado_{Path(self.pdf_path).name}"
        )
        if not path:
            return

        self.status("Guardando PDF…")
        thread = threading.Thread(target=self._save_worker, args=(path,), daemon=True)
        thread.start()

    def _save_worker(self, output_path):
        try:
            # Agrupar páginas por archivo fuente
            # Necesitamos readers para cada PDF fuente
            readers: dict[str, PdfReader] = {}

            def get_reader(fpath):
                if fpath not in readers:
                    readers[fpath] = PdfReader(fpath)
                return readers[fpath]

            main_reader = get_reader(self.pdf_path)
            writer = PdfWriter()

            for page_info in self.pages:
                src = page_info.get("from_file", self.pdf_path)
                reader = get_reader(src)
                orig_idx = page_info["original_index"]
                page = reader.pages[orig_idx]

                rot = page_info.get("rotation", 0)
                if rot:
                    page.rotate(rot)

                writer.add_page(page)

            with open(output_path, "wb") as f:
                writer.write(f)

            self.after(0, lambda: self.status(
                f"✅ Guardado en: {Path(output_path).name}"))
            self.after(0, lambda: messagebox.showinfo(
                "Guardado", f"PDF guardado exitosamente:\n{output_path}"))
        except Exception as ex:
            self.after(0, lambda: messagebox.showerror(
                "Error al guardar", f"{ex}"))
            self.after(0, lambda: self.status("❌ Error al guardar"))

    # ──────────────────────────────────────────
    #  UTILIDADES
    # ──────────────────────────────────────────
    def status(self, msg: str):
        self.statusbar.config(text=msg)
        self.update_idletasks()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = PDFEditorApp()
    app.mainloop()
