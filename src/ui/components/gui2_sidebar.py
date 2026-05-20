from __future__ import annotations

import ttkbootstrap as ttk
from ttkbootstrap.constants import DANGER, OUTLINE, PRIMARY, SECONDARY, WARNING, X


class SidebarPanel(ttk.Frame):
    def __init__(self, parent, commands: dict[str, object]) -> None:
        super().__init__(parent, width=240)
        self.grid_propagate(False)

        ops = ttk.Labelframe(self, text="Operaciones", padding=10)
        ops.pack(fill=X)

        ttk.Button(ops, text="Eliminar selección", command=commands["delete_selected"], bootstyle=DANGER).pack(fill=X, pady=3)
        ttk.Button(ops, text="Mover arriba", command=commands["move_up"], bootstyle=SECONDARY).pack(fill=X, pady=3)
        ttk.Button(ops, text="Mover abajo", command=commands["move_down"], bootstyle=SECONDARY).pack(fill=X, pady=3)
        ttk.Button(ops, text="Mover a posición", command=commands["move_to_position"], bootstyle=SECONDARY).pack(fill=X, pady=3)
        ttk.Button(ops, text="Rotar a la derecha", command=commands["rotate_right"], bootstyle=SECONDARY).pack(fill=X, pady=3)
        ttk.Button(ops, text="Rotar a la izquierda", command=commands["rotate_left"], bootstyle=SECONDARY).pack(fill=X, pady=3)

        sel = ttk.Labelframe(self, text="Selección", padding=10)
        sel.pack(fill=X, pady=(12, 0))

        ttk.Button(sel, text="Seleccionar todo", command=commands["select_all"], bootstyle=SECONDARY).pack(fill=X, pady=3)
        ttk.Button(sel, text="Deseleccionar todo", command=commands["deselect_all"], bootstyle=SECONDARY).pack(fill=X, pady=3)
        ttk.Button(sel, text="Invertir selección", command=commands["invert_selection"], bootstyle=SECONDARY).pack(fill=X, pady=3)

        doc = ttk.Labelframe(self, text="Documento", padding=10)
        doc.pack(fill=X, pady=(12, 0))

        self.lbl_pages = ttk.Label(doc, text="0", font=("Segoe UI", 24, "bold"), bootstyle=PRIMARY)
        self.lbl_pages.pack(anchor="center")
        ttk.Label(doc, text="páginas totales").pack(anchor="center")

        self.lbl_sel = ttk.Label(doc, text="0 seleccionadas", bootstyle=WARNING)
        self.lbl_sel.pack(anchor="center", pady=(8, 0))

        self.lbl_fname = ttk.Label(doc, text="", wraplength=200, justify="left")
        self.lbl_fname.pack(anchor="w", pady=(10, 0))

    def update_document_info(self, total: int, selected_count: int, filename: str) -> None:
        suffix = "seleccionada" if selected_count == 1 else "seleccionadas"
        self.lbl_pages.configure(text=str(total))
        self.lbl_sel.configure(text=f"{selected_count} {suffix}")
        self.lbl_fname.configure(text=filename)
