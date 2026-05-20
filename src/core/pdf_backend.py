from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter

from core.pdf_renderer import close_fitz_doc, get_fitz_doc, render_thumbnail


@dataclass
class PageItem:
    original_index: int
    from_file: str
    rotation: int = 0
    thumb: Image.Image | None = None


class PDFEditorBackend:
    def __init__(self) -> None:
        self.pdf_path: str | None = None
        self.pages: list[PageItem] = []
        self.selected: set[int] = set()

    @property
    def has_document(self) -> bool:
        return bool(self.pages)

    @property
    def has_selection(self) -> bool:
        return bool(self.selected)

    def reset_document(self) -> None:
        if self.pdf_path:
            close_fitz_doc(self.pdf_path)
        self.pdf_path = None
        self.pages.clear()
        self.selected.clear()

    def open_pdf(self, path: str, progress_callback=None) -> int:
        if self.pdf_path and self.pdf_path != path:
            close_fitz_doc(self.pdf_path)

        self.pdf_path = path
        self.pages.clear()
        self.selected.clear()

        doc = get_fitz_doc(path)
        total = len(doc)

        for index in range(total):
            self.pages.append(
                PageItem(
                    original_index=index,
                    from_file=path,
                    rotation=0,
                    thumb=render_thumbnail(path, index),
                )
            )
            if progress_callback:
                progress_callback(int((index + 1) / total * 100))

        return total

    def insert_pdf(self, path: str, position: int) -> int:
        doc = get_fitz_doc(path)
        total = len(doc)
        new_pages: list[PageItem] = []

        for index in range(total):
            new_pages.append(
                PageItem(
                    original_index=index,
                    from_file=path,
                    rotation=0,
                    thumb=render_thumbnail(path, index),
                )
            )

        self.pages[position:position] = new_pages
        self.selected = set(range(position, position + total))
        return total

    def delete_selected(self) -> int:
        removed = len(self.selected)
        self.pages = [page for index, page in enumerate(self.pages) if index not in self.selected]
        self.selected.clear()
        return removed

    def move_up(self) -> bool:
        if not self.selected:
            return False

        selected = sorted(self.selected)
        if selected[0] == 0:
            return False

        for index in selected:
            self.pages[index - 1], self.pages[index] = self.pages[index], self.pages[index - 1]

        self.selected = {index - 1 for index in self.selected}
        return True

    def move_down(self) -> bool:
        if not self.selected:
            return False

        selected = sorted(self.selected, reverse=True)
        if selected[0] == len(self.pages) - 1:
            return False

        for index in selected:
            self.pages[index + 1], self.pages[index] = self.pages[index], self.pages[index + 1]

        self.selected = {index + 1 for index in self.selected}
        return True

    def move_to_position(self, source_index: int, destination_index: int) -> None:
        page = self.pages.pop(source_index)
        self.pages.insert(destination_index, page)
        self.selected = {destination_index}

    def rotate_selected(self, degrees: int) -> int:
        for index in self.selected:
            self.pages[index].rotation = (self.pages[index].rotation + degrees) % 360
        return len(self.selected)

    def select_all(self) -> None:
        self.selected = set(range(len(self.pages)))

    def deselect_all(self) -> None:
        self.selected.clear()

    def invert_selection(self) -> None:
        self.selected = set(range(len(self.pages))) - self.selected

    def set_single_selection(self, index: int) -> None:
        self.selected = {index}

    def toggle_selection(self, index: int) -> None:
        if index in self.selected:
            self.selected.discard(index)
        else:
            self.selected.add(index)

    def select_range_from_last(self, index: int) -> None:
        if not self.selected:
            self.selected = {index}
            return

        last = max(self.selected)
        for selected_index in range(min(last, index), max(last, index) + 1):
            self.selected.add(selected_index)

    def get_single_selected_index(self) -> int | None:
        if len(self.selected) != 1:
            return None
        return next(iter(self.selected))

    def save_pdf(self, output_path: str) -> None:
        readers: dict[str, PdfReader] = {}

        def get_reader(path: str) -> PdfReader:
            if path not in readers:
                readers[path] = PdfReader(path)
            return readers[path]

        writer = PdfWriter()
        for page_item in self.pages:
            page = get_reader(page_item.from_file).pages[page_item.original_index]
            if page_item.rotation:
                page.rotate(page_item.rotation)
            writer.add_page(page)

        with open(output_path, "wb") as file_handle:
            writer.write(file_handle)

    def get_filename(self) -> str:
        if not self.pdf_path:
            return ""
        return Path(self.pdf_path).name
