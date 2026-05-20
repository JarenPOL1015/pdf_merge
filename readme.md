# PDF Editor - By: Jaren Pazmino

Un editor de PDF rápido, moderno y diseñado con un enfoque absoluto en la **privacidad y seguridad de tus datos**. Ideal para manipular documentos sensibles (como pasaportes, contratos o identificaciones) de forma 100% offline.

## 🔒 Privacidad Garantizada
A diferencia de las herramientas web online, esta aplicación procesa todo de forma **100% local en tu memoria RAM**. Tus archivos nunca tocan internet, eliminando cualquier riesgo de filtración.



## 🚀 Cómo usarlo

**1. Clonar el repositorio e instalar dependencias** (solo la primera vez):
```bash
pip install -r requirements.txt
```

**2. Ejecutar:**
```bash
python pdf_editor.py
```

## 📦 Cómo compilar tu propio ejecutable (.exe)

Si quieres generar el archivo independiente para Windows 11 (el que no abre la consola negra y empaqueta todo en un solo archivo), ejecuta este comando en tu terminal:

```bash
pyinstaller --clean --onefile --windowed --name "PDF Editor Local" --collect-all pymupdf --hidden-import=fitz --hidden-import=PIL --hidden-import=pypdf pdf_editor.py
```

El ejecutable final aparecerá en la carpeta **dist/.**


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

## 🛠️ Tecnologías utilizadas

* **Tkinter:** Para la interfaz gráfica de usuario (GUI).
* **PyMuPDF (fitz):** Para el renderizado de alta velocidad y visualización de páginas sin dependencias externas pesadas.
* **pypdf:** Para la manipulación binaria, reordenamiento y guardado de los documentos.
* **Pillow:** Para el procesamiento eficiente de imágenes y miniaturas.

## Authors 👥

- Jaren Pazmiño

Miembro del Club de Inteligencia Artificial Politécnico CIAP
<img alt="Logo_CIAP" src="img/ciap.png" />
