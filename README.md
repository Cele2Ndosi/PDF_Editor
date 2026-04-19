# PDF Editor

A fully functional desktop PDF editor built with Python and Tkinter. Open, annotate, draw on, and save PDF files — all from a clean, dark-themed GUI.

---

## Features

- **Open & Save PDFs** — Open any PDF file and save in-place or export as a new file
- **Multi-page scroll view** — View all pages in a continuous scrollable canvas with a thumbnail sidebar
- **Text annotations** — Click anywhere on a page to place a text label
- **Shape annotations** — Draw highlights, rectangles, and circles with a preview while dragging
- **Freehand drawing** — Sketch directly on any page with a configurable pen
- **Erase annotations** — Click to remove any annotation
- **Move annotations** — Drag existing annotations to reposition them, with snap/alignment guides
- **Undo / Redo** — Full undo/redo stack for all annotation actions
- **Zoom** — Zoom in, zoom out, or fit the page to the window (50% – 300%)
- **Color picker** — Choose from 8 preset colors for any annotation type
- **Pen width control** — Adjustable stroke width for shapes and freehand drawing
- **Native PDF export** — Annotations are embedded as native PDF objects (highlights, shapes, text, polylines)

---

## Requirements

- Python 3.10+
- [PyMuPDF](https://pymupdf.readthedocs.io/) (`fitz`)
- [Pillow](https://python-pillow.org/)
- `tkinter` (included with most standard Python distributions)

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Cele2Ndosi/PDF_Editor.git
   cd PDF_Editor
   ```

2. **Install dependencies:**
   ```bash
   pip install pymupdf Pillow
   ```

3. **Run the application:**
   ```bash
   python pdf_editor.py
   ```

---

## Usage

### Opening a file
Go to **File → Open PDF** or press `Ctrl+O` to open a PDF. The file will be rendered across all pages in the main canvas.

### Annotation modes

Select a mode from the toolbar:

| Mode | Description |
|---|---|
| ⭢ Select | Click and drag annotations to move them |
| T Text | Click on the page to place a text label |
| 🖊 Highlight | Drag to draw a semi-transparent highlight box |
| ☐ Rect | Drag to draw a rectangle outline |
| ○ Circle | Drag to draw an ellipse outline |
| ✏ Draw | Freehand brush strokes |
| ✖ Erase | Click an annotation to delete it |

### Saving
- **Save** (`Ctrl+S`) — Overwrites the original file with annotations embedded
- **Save As** (`Ctrl+Shift+S`) — Saves a new copy (defaults to `<original>_edited.pdf`)

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open PDF |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl++` | Zoom In |
| `Ctrl+-` | Zoom Out |
| `Ctrl+0` | Fit page to window |

---

## Project Structure

```
PDF_Editor/
└── pdf_editor.py   # Single-file application (918 lines)
```

The app is organized into three main classes:

- **`Annotation`** — Data model for a single annotation (type, page, coordinates, color, etc.)
- **`PDFEngine`** — Handles PDF loading, rendering via PyMuPDF, annotation management, undo/redo stack, and native PDF export
- **`PDFEditorApp`** — Tkinter UI layer: toolbar, canvas, sidebar, event handling, zoom, and mode switching

---

## License

This project does not currently include a license file. All rights reserved by the author unless otherwise specified.
