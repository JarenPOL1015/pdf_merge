
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
from pathlib import Path
from ui import styles
from pypdf import PdfReader, PdfWriter
from PIL import Image, ImageTk
import fitz
import tkinter as _tk, tkinter.messagebox as _mb

from ui.components.topbar import render_topbar

_fitz_cache: dict[str, fitz.Document] = {}

def _get_fitz_doc(path: str) -> fitz.Document:
    if path not in _fitz_cache:
        _fitz_cache[path] = fitz.open(path)
    return _fitz_cache[path]

def render_page(pdf_path: str, page_index: int, dpi: int = 96) -> Image.Image | None:
    """Renderiza una página como imagen PIL usando PyMuPDF. Sin poppler."""
    try:
        doc = _get_fitz_doc(pdf_path)
        page = doc[page_index]
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img
    except Exception as ex:
        print(f"[render_page] Error en pág {page_index}: {ex}")
        return None

def render_thumbnail(pdf_path: str, page_index: int) -> Image.Image | None:
    """Miniatura de baja resolución para el grid."""
    return render_page(pdf_path, page_index, dpi=36)

def close_fitz_doc(path: str):
    """Libera el documento de la caché."""
    if path in _fitz_cache:
        try:
            _fitz_cache[path].close()
        except Exception:
            pass
        del _fitz_cache[path]




class PDFEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(styles.APP_TITLE)
        self.geometry(styles.DEFAULT_GEOMETRY)
        self.minsize(1000, 640)
        self.configure(bg=styles.BG_DARK)
        
        #TODO: adapt to other OS
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # State
        self.pdf_path: str | None = None
        self.pages: list[dict] = []
        self.selected: set[int] = set()
        self.thumb_cache: dict[int, ImageTk.PhotoImage] = {}

        # Preview
        self._preview_idx: int | None = None
        self._preview_tk: ImageTk.PhotoImage | None = None
        self._preview_cancel = threading.Event()

        self._build_ui()
        self._bind_keys()

    def _on_close(self):
        self._preview_cancel.set()
        for path in list(_fitz_cache.keys()):
            close_fitz_doc(path)
        self.destroy()

    # ──────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────

    def _build_ui(self):
        
        topbar = render_topbar(self)
        btn_f = tk.Frame(topbar, bg=styles.BG_PANEL)
        btn_f.pack(side="right", padx=12)
        self._topbtn(btn_f, "📂 Abrir PDF",    self.open_pdf,   styles.ACCENT)
        self._topbtn(btn_f, "➕ Insertar PDF",  self.insert_pdf, "#2b6cb0")
        self._topbtn(btn_f, "💾 Guardar",        self.save_pdf,   styles.GREEN)

        # Main
        main = tk.Frame(self, bg=styles.BG_DARK)
        main.pack(fill="both", expand=True)

        # Izquierda
        left = tk.Frame(main, bg=styles.BG_CARD, width=215)
        left.pack(side="left", fill="y", padx=(10,0), pady=10)
        left.pack_propagate(False)
        self._build_left(left)

        # Derecha — preview
        right = tk.Frame(main, bg=styles.PREVIEW_BG, width=350)
        right.pack(side="right", fill="y", padx=(0,10), pady=10)
        right.pack_propagate(False)
        self._build_preview(right)

        # Centro — grid
        center = tk.Frame(main, bg=styles.BG_DARK)
        center.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self._build_center(center)

        # Statusbar
        self.statusbar = tk.Label(self, text="Abre un PDF para comenzar",
                                  font=("Segoe UI", 9), bg=styles.BG_PANEL,
                                  fg=styles.TEXT_GRAY, anchor="w", padx=12)
        self.statusbar.pack(fill="x", side="bottom")

    def _topbtn(self, parent, text, cmd, color):
        b = tk.Button(parent, text=text, command=cmd, bg=color, fg="white",
                      relief="flat", font=("Segoe UI", 9, "bold"),
                      cursor="hand2", padx=12, pady=6, bd=0)
        b.pack(side="left", padx=4, pady=8)
        b.bind("<Enter>", lambda e: b.config(bg=self._darken(color)))
        b.bind("<Leave>", lambda e: b.config(bg=color))

    def _darken(self, c):
        r,g,b = int(c[1:3],16), int(c[3:5],16), int(c[5:7],16)
        return f"#{max(0,r-30):02x}{max(0,g-30):02x}{max(0,b-30):02x}"

    # ── Panel izquierdo ──────────────────────
    def _build_left(self, p):
        def section(title):
            tk.Label(p, text=title, font=("Segoe UI", 8, "bold"),
                     bg=styles.BG_CARD, fg=styles.TEXT_GRAY).pack(anchor="w", padx=14, pady=(14,4))

        section("OPERACIONES")
        for lbl, cmd, color in [
            ("🗑️  Eliminar selección",  self.delete_selected,  styles.ACCENT),
            ("⬆️  Mover arriba",         self.move_up,          styles.BG_PANEL),
            ("⬇️  Mover abajo",          self.move_down,        styles.BG_PANEL),
            ("↕️  Mover a posición…",    self.move_to_position, styles.BG_PANEL),
            ("🔄  Rotar 90° →",          self.rotate_right,     styles.BG_PANEL),
            ("🔄  Rotar 90° ←",          self.rotate_left,      styles.BG_PANEL),
        ]:
            tk.Button(p, text=lbl, command=cmd, bg=color, fg=styles.TEXT_WHITE,
                      relief="flat", font=("Segoe UI", 9), cursor="hand2",
                      anchor="w", padx=10, pady=7, bd=0).pack(fill="x", padx=10, pady=2)

        ttk.Separator(p, orient="horizontal").pack(fill="x", padx=10, pady=10)
        section("SELECCIÓN")
        for lbl, cmd in [
            ("✅  Seleccionar todo",   self.select_all),
            ("⬜  Deseleccionar todo", self.deselect_all),
            ("🔁  Invertir selección", self.invert_selection),
        ]:
            tk.Button(p, text=lbl, command=cmd, bg=styles.BG_CARD, fg=styles.TEXT_WHITE,
                      relief="flat", font=("Segoe UI", 9), cursor="hand2",
                      anchor="w", padx=10, pady=6, bd=0).pack(fill="x", padx=10, pady=1)

        ttk.Separator(p, orient="horizontal").pack(fill="x", padx=10, pady=10)
        section("DOCUMENTO")
        self.lbl_pages = tk.Label(p, text="—", font=("Segoe UI", 20, "bold"),
                                  bg=styles.BG_CARD, fg=styles.ACCENT)
        self.lbl_pages.pack(pady=(2,0))
        tk.Label(p, text="páginas totales", font=("Segoe UI", 8),
                 bg=styles.BG_CARD, fg=styles.TEXT_GRAY).pack()
        self.lbl_sel = tk.Label(p, text="0 seleccionadas",
                                font=("Segoe UI", 9), bg=styles.BG_CARD, fg=styles.YELLOW)
        self.lbl_sel.pack(pady=(6,0))
        self.lbl_fname = tk.Label(p, text="", font=("Segoe UI", 8),
                                  bg=styles.BG_CARD, fg=styles.TEXT_GRAY, wraplength=190)
        self.lbl_fname.pack(pady=(4,0), padx=10)

    # ── Panel de vista previa ────────────────
    def _build_preview(self, p):
        hdr = tk.Frame(p, bg=styles.BG_PANEL, height=36)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="👁  Vista Previa", font=("Segoe UI", 9, "bold"),
                 bg=styles.BG_PANEL, fg=styles.TEXT_WHITE).pack(side="left", padx=10, pady=8)

        self.lbl_pv_info = tk.Label(p, text="← Haz clic en una página",
                                    font=("Segoe UI", 8), bg=styles.PREVIEW_BG,
                                    fg=styles.TEXT_GRAY, wraplength=330)
        self.lbl_pv_info.pack(pady=(8,2), padx=8)

        # Canvas de preview con scroll vertical
        cf = tk.Frame(p, bg=styles.PREVIEW_BG)
        cf.pack(fill="both", expand=True, padx=4, pady=4)
        self.pv_canvas = tk.Canvas(cf, bg=styles.PREVIEW_BG, highlightthickness=0)
        sb = tk.Scrollbar(cf, orient="vertical", command=self.pv_canvas.yview)
        self.pv_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.pv_canvas.pack(fill="both", expand=True)
        self.pv_canvas.bind("<MouseWheel>", self._pv_scroll)
        self.pv_canvas.bind("<Button-4>",   self._pv_scroll)
        self.pv_canvas.bind("<Button-5>",   self._pv_scroll)
        self.pv_canvas.bind("<Configure>",  lambda e: self._redraw_preview())

        self._pv_placeholder = self.pv_canvas.create_text(
            170, 200,
            text="Haz clic en\nuna miniatura\npara previsualizar",
            font=("Segoe UI", 11), fill=styles.TEXT_GRAY, justify="center"
        )
        self._pv_img_item = None

        # Spinner
        self.lbl_spinner = tk.Label(p, text="", font=("Segoe UI", 8),
                                    bg=styles.PREVIEW_BG, fg=styles.YELLOW)
        self.lbl_spinner.pack(pady=2)

        # Navegación
        nav = tk.Frame(p, bg=styles.BG_CARD, height=40)
        nav.pack(fill="x", side="bottom")
        nav.pack_propagate(False)
        tk.Button(nav, text="◀", command=self._pv_prev, bg=styles.BG_PANEL, fg=styles.TEXT_WHITE,
                  relief="flat", font=("Segoe UI", 10), cursor="hand2",
                  padx=12, pady=4, bd=0).pack(side="left", padx=6, pady=5)
        self.lbl_nav = tk.Label(nav, text="—", font=("Segoe UI", 8, "bold"),
                                bg=styles.BG_CARD, fg=styles.TEXT_GRAY)
        self.lbl_nav.pack(side="left", expand=True)
        tk.Button(nav, text="▶", command=self._pv_next, bg=styles.BG_PANEL, fg=styles.TEXT_WHITE,
                  relief="flat", font=("Segoe UI", 10), cursor="hand2",
                  padx=12, pady=4, bd=0).pack(side="right", padx=6, pady=5)

    # ── Grid central ─────────────────────────
    def _build_center(self, p):
        tb = tk.Frame(p, bg=styles.BG_CARD, height=36)
        tb.pack(fill="x")
        tb.pack_propagate(False)
        tk.Label(tb, text="Clic: seleccionar y previsualizar  ·  Ctrl+clic: multiselección  ·  Doble clic: previsualizar",
                 font=("Segoe UI", 8), bg=styles.BG_CARD, fg=styles.TEXT_GRAY).pack(side="left", padx=12, pady=8)
        tk.Label(tb, text="Zoom:", font=("Segoe UI", 8),
                 bg=styles.BG_CARD, fg=styles.TEXT_GRAY).pack(side="right", padx=(0,4))
        self.zoom_var = tk.IntVar(value=130)
        tk.Scale(tb, from_=60, to=220, variable=self.zoom_var, orient="horizontal",
                  length=100, command=lambda _: self._refresh_grid()).pack(side="right", padx=(0,12))

        cf = tk.Frame(p, bg=styles.BG_DARK)
        cf.pack(fill="both", expand=True, pady=(6,0))
        self.canvas = tk.Canvas(cf, bg=styles.BG_DARK, highlightthickness=0)
        sy = tk.Scrollbar(cf, orient="vertical",   command=self.canvas.yview)
        sx = tk.Scrollbar(cf, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=styles.BG_DARK)
        self._cwin = self.canvas.create_window((0,0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(
            self._cwin, width=e.width))
        self.canvas.bind("<MouseWheel>", self._grid_scroll)
        self.canvas.bind("<Button-4>",   self._grid_scroll)
        self.canvas.bind("<Button-5>",   self._grid_scroll)

        # Progress bar
        self.prog_frame = tk.Frame(p, bg=styles.BG_DARK)
        self.prog_var   = tk.DoubleVar()
        self.prog_bar   = ttk.Progressbar(self.prog_frame, variable=self.prog_var,
                                           maximum=100, length=400)
        self.prog_lbl   = tk.Label(self.prog_frame, text="Generando miniaturas…",
                                   font=("Segoe UI", 9), bg=styles.BG_DARK, fg=styles.TEXT_GRAY)

    # ──────────────────────────────────────────
    #  EVENTOS TECLADO / SCROLL
    # ──────────────────────────────────────────
    def _bind_keys(self):
        self.bind("<Delete>",    lambda e: self.delete_selected())
        self.bind("<Control-a>", lambda e: self.select_all())
        self.bind("<Control-s>", lambda e: self.save_pdf())
        self.bind("<Control-o>", lambda e: self.open_pdf())
        self.bind("<Left>",      lambda e: self._pv_prev())
        self.bind("<Right>",     lambda e: self._pv_next())

    def _grid_scroll(self, e):
        if e.num == 4:   self.canvas.yview_scroll(-1, "units")
        elif e.num == 5: self.canvas.yview_scroll(1,  "units")
        else: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units")

    def _pv_scroll(self, e):
        if e.num == 4:   self.pv_canvas.yview_scroll(-1, "units")
        elif e.num == 5: self.pv_canvas.yview_scroll(1,  "units")
        else: self.pv_canvas.yview_scroll(int(-1*(e.delta/120)), "units")

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
        # Liberar PDF anterior
        if self.pdf_path:
            close_fitz_doc(self.pdf_path)
        self.pdf_path = path
        self.pages.clear()
        self.selected.clear()
        self.thumb_cache.clear()
        self._preview_idx = None
        self._preview_cancel.set()
        self._preview_cancel = threading.Event()
        self._load_async(path)

    def _load_async(self, path):
        self._show_prog(True)
        self.status(f"Cargando {Path(path).name}…")
        threading.Thread(target=self._load_worker, args=(path,), daemon=True).start()

    def _load_worker(self, path):
        try:
            doc = _get_fitz_doc(path)
            n = len(doc)
            self.pages = []
            thumbs = []

            for i in range(n):
                thumb = render_thumbnail(path, i)   # 36 dpi — rápido
                self.pages.append({
                    "original_index": i,
                    "rotation": 0,
                    "thumb": thumb,    # PIL Image baja res
                    "from_file": path,
                })
                pct = int((i+1)/n*100)
                self.after(0, lambda p=pct: self.prog_var.set(p))

            self.after(0, self._load_done)
        except Exception as ex:
            self.after(0, lambda: messagebox.showerror("Error", f"No se pudo abrir:\n{ex}"))
            self.after(0, lambda: self._show_prog(False))

    def _load_done(self):
        self._show_prog(False)
        self._refresh_grid()
        name = Path(self.pdf_path).name
        self.lbl_fname.config(text=name)
        self.lbl_pages.config(text=str(len(self.pages)))
        self.status(f"✅ {name} — {len(self.pages)} páginas  (PyMuPDF)")
        if self.pages:
            self.show_preview(0)

    # ──────────────────────────────────────────
    #  PROGRESS
    # ──────────────────────────────────────────
    def _show_prog(self, show):
        if show:
            self.prog_frame.pack(fill="x", pady=4)
            self.prog_lbl.pack()
            self.prog_bar.pack(pady=2)
        else:
            self.prog_bar.pack_forget()
            self.prog_lbl.pack_forget()
            self.prog_frame.pack_forget()

    # ──────────────────────────────────────────
    #  GRID DE MINIATURAS
    # ──────────────────────────────────────────
    def _refresh_grid(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.thumb_cache.clear()

        if not self.pages:
            tk.Label(self.inner, text="📂\n\nAbre un PDF para ver sus páginas",
                     font=("Segoe UI", 14), bg=styles.BG_DARK, fg=styles.TEXT_GRAY,
                     justify="center").pack(expand=True, pady=120)
            return

        tw = self.zoom_var.get()
        th = int(tw * 1.414)
        cols = max(1, (self.canvas.winfo_width() or 700) // (tw + 24))

        for idx, page in enumerate(self.pages):
            self._make_thumb(idx, page, idx//cols, idx%cols, tw, th)

        self.lbl_pages.config(text=str(len(self.pages)))
        n = len(self.selected)
        self.lbl_sel.config(text=f"{n} seleccionada{'s' if n!=1 else ''}")

    def _make_thumb(self, idx, page, row, col, tw, th):
        sel  = idx in self.selected
        prev = idx == self._preview_idx
        bc   = "#f6c90e" if prev else (styles.THUMB_SEL if sel else styles.BORDER)
        bw   = 3 if prev else (2 if sel else 1)

        frame = tk.Frame(self.inner, bg=styles.THUMB_SEL if sel else styles.THUMB_BG,
                         highlightbackground=bc, highlightthickness=bw, bd=0)
        frame.grid(row=row, column=col, padx=8, pady=8, sticky="n")

        img = page.get("thumb")
        if img:
            rot = page.get("rotation", 0)
            tmp = img.rotate(-rot, expand=True) if rot else img.copy()
            tmp.thumbnail((tw, th), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(tmp)
            self.thumb_cache[idx] = tk_img
            lbl_img = tk.Label(frame, image=tk_img, bg=styles.THUMB_BG, cursor="hand2")
        else:
            lbl_img = tk.Label(frame, text="📄", font=("Segoe UI", 26),
                               bg=styles.THUMB_BG, width=tw//10, height=th//20, cursor="hand2")
        lbl_img.pack(padx=4, pady=(4,2))

        lbl_n = tk.Label(frame, text=f"Pág. {idx+1}", font=("Segoe UI", 8, "bold"),
                         bg=styles.THUMB_SEL if sel else styles.THUMB_BG,
                         fg=styles.TEXT_WHITE if sel else styles.TEXT_GRAY)
        lbl_n.pack(pady=(0,4))
        if prev:
            tk.Label(frame, text="👁", font=("Segoe UI", 7),
                     bg=styles.THUMB_BG, fg="#f6c90e").pack(pady=(0,2))

        for w in (frame, lbl_img, lbl_n):
            w.bind("<Button-1>",        lambda e, i=idx: self._thumb_click(e, i))
            w.bind("<Double-Button-1>", lambda e, i=idx: self.show_preview(i))

    def _thumb_click(self, event, idx):
        ctrl  = (event.state & 0x4) != 0
        shift = (event.state & 0x1) != 0
        if ctrl:
            if idx in self.selected: self.selected.discard(idx)
            else: self.selected.add(idx)
        elif shift and self.selected:
            last = max(self.selected)
            for i in range(min(last,idx), max(last,idx)+1):
                self.selected.add(i)
        else:
            self.selected = {idx}
            self.show_preview(idx)
        self._refresh_grid()

    # ──────────────────────────────────────────
    #  VISTA PREVIA
    # ──────────────────────────────────────────
    def show_preview(self, idx: int):
        if not self.pages or idx < 0 or idx >= len(self.pages):
            return
        self._preview_idx = idx
        page = self.pages[idx]
        self.lbl_pv_info.config(text=f"Página {idx+1} de {len(self.pages)}")
        self.lbl_nav.config(text=f"{idx+1} / {len(self.pages)}")
        self.lbl_spinner.config(text="⏳ Renderizando…")

        # Cancelar renderizado previo
        self._preview_cancel.set()
        cancel = threading.Event()
        self._preview_cancel = cancel

        src   = page.get("from_file", self.pdf_path)
        orig  = page["original_index"]
        rot   = page.get("rotation", 0)

        # Mostrar miniatura mientras carga la HQ
        if page.get("thumb"):
            self._display_preview_img(page["thumb"], rot, fast=True)

        threading.Thread(
            target=self._pv_worker,
            args=(src, orig, rot, cancel),
            daemon=True
        ).start()

    def _pv_worker(self, pdf_path, page_index, rotation, cancel):
        """Renderiza a alta resolución en hilo secundario."""
        try:
            img = render_page(pdf_path, page_index, dpi=130)
            if cancel.is_set():
                return
            if img:
                self.after(0, lambda: self._display_preview_img(img, rotation, fast=False))
            else:
                self.after(0, lambda: self.lbl_spinner.config(text="⚠️ Sin imagen"))
        except Exception as ex:
            self.after(0, lambda: self.lbl_spinner.config(text=f"Error: {ex}"))

    def _display_preview_img(self, img: Image.Image, rotation: int, fast: bool):
        """Dibuja la imagen en el canvas de preview."""
        if rotation:
            img = img.rotate(-rotation, expand=True)

        pw = self.pv_canvas.winfo_width() or 330
        pw = max(180, pw - 10)
        ratio = pw / img.width
        nh = int(img.height * ratio)
        img = img.resize((pw, nh), Image.LANCZOS)

        tk_img = ImageTk.PhotoImage(img)
        self._preview_tk = tk_img   # evitar GC

        self.pv_canvas.delete("all")
        self.pv_canvas.create_image(0, 0, anchor="nw", image=tk_img)
        self.pv_canvas.configure(scrollregion=(0, 0, pw, nh))
        self.pv_canvas.yview_moveto(0)

        if not fast:
            self.lbl_spinner.config(text="✅ Vista previa lista")
            self.after(2500, lambda: self.lbl_spinner.config(text=""))

    def _redraw_preview(self):
        """Redibuja al cambiar tamaño del panel."""
        if self._preview_idx is not None:
            self.show_preview(self._preview_idx)

    def _pv_prev(self):
        if self._preview_idx is not None and self._preview_idx > 0:
            self.show_preview(self._preview_idx - 1)

    def _pv_next(self):
        if self._preview_idx is not None and self._preview_idx < len(self.pages)-1:
            self.show_preview(self._preview_idx + 1)

    # ──────────────────────────────────────────
    #  OPERACIONES
    # ──────────────────────────────────────────
    def _req_pdf(self):
        if not self.pages:
            messagebox.showwarning("Sin PDF", "Primero abre un PDF.")
            return False
        return True

    def _req_sel(self):
        if not self.selected:
            messagebox.showwarning("Sin selección",
                "Selecciona al menos una página.\nClic = seleccionar · Ctrl+clic = múltiple")
            return False
        return True

    def delete_selected(self):
        if not self._req_pdf() or not self._req_sel():
            return
        n = len(self.selected)
        if not messagebox.askyesno("Confirmar", f"¿Eliminar {n} página(s)?"):
            return
        self.pages = [p for i, p in enumerate(self.pages) if i not in self.selected]
        self.selected.clear()
        self._preview_idx = min(self._preview_idx or 0, max(0, len(self.pages)-1)) if self.pages else None
        self._refresh_grid()
        if self._preview_idx is not None and self.pages:
            self.show_preview(self._preview_idx)
        self.status(f"✅ {n} página(s) eliminada(s)")

    def move_up(self):
        if not self._req_pdf() or not self._req_sel(): return
        sel = sorted(self.selected)
        if sel[0] == 0: return
        for i in sel:
            self.pages[i-1], self.pages[i] = self.pages[i], self.pages[i-1]
        self.selected = {i-1 for i in self.selected}
        if self._preview_idx is not None:
            self._preview_idx = max(0, self._preview_idx - 1)
        self._refresh_grid()

    def move_down(self):
        if not self._req_pdf() or not self._req_sel(): return
        sel = sorted(self.selected, reverse=True)
        if sel[0] == len(self.pages)-1: return
        for i in sel:
            self.pages[i+1], self.pages[i] = self.pages[i], self.pages[i+1]
        self.selected = {i+1 for i in self.selected}
        if self._preview_idx is not None:
            self._preview_idx = min(len(self.pages)-1, self._preview_idx + 1)
        self._refresh_grid()

    def move_to_position(self):
        if not self._req_pdf() or not self._req_sel(): return
        if len(self.selected) > 1:
            messagebox.showinfo("Aviso", "Selecciona una sola página para mover a posición.")
            return
        idx = next(iter(self.selected))
        dest = simpledialog.askinteger(
            "Mover página",
            f"Página {idx+1} → ¿A qué posición? (1–{len(self.pages)})",
            minvalue=1, maxvalue=len(self.pages), parent=self
        )
        if dest is None: return
        dest -= 1
        page = self.pages.pop(idx)
        self.pages.insert(dest, page)
        self.selected = {dest}
        self._preview_idx = dest
        self._refresh_grid()
        self.show_preview(dest)
        self.status(f"✅ Página movida a posición {dest+1}")

    def rotate_right(self): self._rotate(90)
    def rotate_left(self):  self._rotate(-90)

    def _rotate(self, deg):
        if not self._req_pdf() or not self._req_sel(): return
        for i in self.selected:
            self.pages[i]["rotation"] = (self.pages[i].get("rotation", 0) + deg) % 360
        self._refresh_grid()
        if self._preview_idx in self.selected:
            self.show_preview(self._preview_idx)
        self.status(f"✅ Rotación {deg:+}° aplicada a {len(self.selected)} página(s)")

    def select_all(self):
        self.selected = set(range(len(self.pages)))
        self._refresh_grid()

    def deselect_all(self):
        self.selected.clear()
        self._refresh_grid()

    def invert_selection(self):
        self.selected = set(range(len(self.pages))) - self.selected
        self._refresh_grid()

    # ──────────────────────────────────────────
    #  INSERTAR PDF
    # ──────────────────────────────────────────
    def insert_pdf(self):
        if not self._req_pdf(): return
        path = filedialog.askopenfilename(title="Seleccionar PDF a insertar",
                                          filetypes=[("PDF files", "*.pdf")])
        if not path: return
        pos = simpledialog.askinteger(
            "Insertar PDF",
            f"¿En qué posición? (1–{len(self.pages)+1})\n"
            f"[1 = inicio · {len(self.pages)+1} = final]",
            minvalue=1, maxvalue=len(self.pages)+1, parent=self
        )
        if pos is None: return
        pos -= 1
        self.status("Cargando PDF a insertar…")
        threading.Thread(target=self._insert_worker, args=(path, pos), daemon=True).start()

    def _insert_worker(self, path, pos):
        try:
            doc = _get_fitz_doc(path)
            n = len(doc)
            new_pages = []
            for i in range(n):
                thumb = render_thumbnail(path, i)
                new_pages.append({
                    "original_index": i,
                    "rotation": 0,
                    "thumb": thumb,
                    "from_file": path,
                })
            self.pages[pos:pos] = new_pages
            self.selected = set(range(pos, pos+n))
            self.after(0, self._refresh_grid)
            self.after(0, lambda: self.show_preview(pos))
            self.after(0, lambda: self.status(
                f"✅ {n} pág. de «{Path(path).name}» insertadas en pos. {pos+1}"))
        except Exception as ex:
            self.after(0, lambda: messagebox.showerror("Error", f"{ex}"))

    # ──────────────────────────────────────────
    #  GUARDAR PDF
    # ──────────────────────────────────────────
    def save_pdf(self):
        if not self._req_pdf(): return
        if not self.pages:
            messagebox.showwarning("Vacío", "No hay páginas."); return
        path = filedialog.asksaveasfilename(
            title="Guardar PDF", defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"editado_{Path(self.pdf_path).name}"
        )
        if not path: return
        self.status("Guardando…")
        threading.Thread(target=self._save_worker, args=(path,), daemon=True).start()

    def _save_worker(self, out):
        try:
            readers: dict[str, PdfReader] = {}
            def get_r(p):
                if p not in readers: readers[p] = PdfReader(p)
                return readers[p]
            writer = PdfWriter()
            for pi in self.pages:
                src  = pi.get("from_file", self.pdf_path)
                page = get_r(src).pages[pi["original_index"]]
                if pi.get("rotation"): page.rotate(pi["rotation"])
                writer.add_page(page)
            with open(out, "wb") as f:
                writer.write(f)
            self.after(0, lambda: self.status(f"✅ Guardado: {Path(out).name}"))
            self.after(0, lambda: messagebox.showinfo("Guardado",
                f"PDF guardado exitosamente:\n{out}"))
        except Exception as ex:
            self.after(0, lambda: messagebox.showerror("Error al guardar", f"{ex}"))

    # ──────────────────────────────────────────
    def status(self, msg):
        self.statusbar.config(text=msg)
        self.update_idletasks()
