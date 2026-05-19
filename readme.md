PDF Editor

---

## 🚀 Cómo usarlo

**1. Instalar dependencias** (solo la primera vez):
```bash
pip install pypdf pillow pdf2image
```

> En Linux también necesitas poppler:
> ```bash
> sudo apt install poppler-utils   # Ubuntu/Debian
> brew install poppler             # macOS
> ```

**2. Ejecutar:**
```bash
python3 pdf_editor.py
```

---

## ✨ Funciones incluidas

| Función | Cómo |
|---|---|
| **Abrir PDF** | Botón "📂 Abrir PDF" o `Ctrl+O` |
| **Ver páginas** | Miniaturas con zoom ajustable |
| **Seleccionar páginas** | Clic simple / `Ctrl+clic` (múltiple) / `Shift+clic` (rango) |
| **Eliminar páginas** | Botón o tecla `Delete` |
| **Mover arriba/abajo** | Botones del panel izquierdo |
| **Mover a posición exacta** | "↕️ Mover a posición…" → escribe el número |
| **Rotar páginas** | 90° izquierda o derecha |
| **Insertar otro PDF** | "➕ Insertar PDF" → elige posición de inserción |
| **Vista previa** | Doble clic sobre una miniatura |
| **Guardar** | Botón "💾 Guardar" o `Ctrl+S` |

El archivo original **nunca se modifica** — siempre guardas una copia nueva.