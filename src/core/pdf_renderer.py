from __future__ import annotations

from PIL import Image
import fitz


_fitz_cache: dict[str, fitz.Document] = {}


def get_fitz_doc(path: str) -> fitz.Document:
    if path not in _fitz_cache:
        _fitz_cache[path] = fitz.open(path)
    return _fitz_cache[path]


def render_page(pdf_path: str, page_index: int, dpi: int = 96) -> Image.Image | None:
    """Render a PDF page into a PIL image using PyMuPDF."""
    try:
        doc = get_fitz_doc(pdf_path)
        page = doc[page_index]
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    except Exception as ex:
        print(f"[render_page] Error on page {page_index}: {ex}")
        return None


def render_thumbnail(pdf_path: str, page_index: int) -> Image.Image | None:
    return render_page(pdf_path, page_index, dpi=36)


def close_fitz_doc(path: str) -> None:
    if path not in _fitz_cache:
        return

    try:
        _fitz_cache[path].close()
    except Exception:
        pass

    del _fitz_cache[path]


def close_all_fitz_docs() -> None:
    for path in list(_fitz_cache.keys()):
        close_fitz_doc(path)
