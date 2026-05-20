import tkinter as tk

from ui import styles

LOGO_TXT_SIZE = 16
DEFAULT_LABEL_TXT_SZ = 9 

TOPBAR_LOGO_TEXT = "📄 PDF Editor Local"
TOPBAR_LABEL_TEXT = "🔒 Sin conexión · 100% privado"

LOGO_STYLE = {
    "font": (styles.MAIN_FONT, LOGO_TXT_SIZE, "bold"),
    "bg":styles.BG_PANEL,
    "fg":styles.TEXT_WHITE
}

def render_topbar(app: tk.Tk):
    topbar = tk.Frame(app, height=56, bg=styles.BG_PANEL)
    topbar.pack(fill="x", side="top")
    topbar.pack_propagate(False)
    tk.Label(topbar,  
             text=TOPBAR_LOGO_TEXT,
             **LOGO_STYLE).pack(side="left", padx=18, pady=10)
    
    tk.Label(topbar, text=TOPBAR_LABEL_TEXT, **styles.DEFAULT_LABEL_STYLE).pack(side="left", padx=6)
    return topbar
