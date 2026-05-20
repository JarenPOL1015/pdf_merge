from __future__ import annotations

import ttkbootstrap as ttk
from ttkbootstrap.constants import INFO, LEFT, PRIMARY, SUCCESS


def render_gui2_topbar(parent, open_command, insert_command, save_command) -> None:
    bar = ttk.Frame(parent, padding=(12, 12, 12, 8))
    bar.grid(row=0, column=0, sticky="ew")
    bar.columnconfigure(0, weight=1)

    title_box = ttk.Frame(bar)
    title_box.grid(row=0, column=0, sticky="w")

    ttk.Label(title_box, text="PDF Editor Local", font=("Segoe UI", 16, "bold")).pack(anchor="w")
    ttk.Label(
        title_box,
        text="Abrir, reordenar, rotar, insertar y guardar páginas PDF",
    ).pack(anchor="w", pady=(2, 0))

    actions = ttk.Frame(bar)
    actions.grid(row=0, column=1, sticky="e")

    ttk.Button(actions, text="Abrir PDF", command=open_command, bootstyle=PRIMARY).pack(side=LEFT, padx=4)
    ttk.Button(actions, text="Insertar PDF", command=insert_command, bootstyle=INFO).pack(side=LEFT, padx=4)
    ttk.Button(actions, text="Guardar", command=save_command, bootstyle=SUCCESS).pack(side=LEFT, padx=4)
