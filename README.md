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

---

## Building & Deployment

This repo ships with a Makefile, a Dockerfile, and a GitHub Actions pipeline.
They cover two different jobs, and it's worth knowing which is which:

| Tool | Job |
|---|---|
| **Docker** (`Dockerfile`) | Consistent Linux environment for running the app and smoke-testing it (syntax + dependency imports) locally or in CI. |
| **GitHub Actions** (`.github/workflows/build.yml`) | Builds the real Windows `.exe` on an actual `windows-latest` runner, and publishes it to a GitHub Release when you push a version tag. |

A `.exe` is Windows machine code — PyInstaller has to run on Windows (or
under Wine) to produce one. Docker on Linux can't build a genuine `.exe` on
its own, which is why the CI/CD pipeline — not the Dockerfile — is the
source of truth for releases.

### Local development

```bash
make install    # pip install -r requirements.txt
make run        # launch the app
make test       # syntax + import sanity check
```

### Local Docker (dev/test container)

```bash
make docker-build   # build the image
make docker-run     # run the GUI in a container via Xvfb
make docker-test    # just check deps import cleanly
```

### Building the .exe

**Recommended — let CI build it:** push a tag and GitHub Actions builds and
releases the `.exe` for you:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Once the workflow finishes, the `.exe` is attached to a new GitHub Release
and also available as a build artifact on the Actions run itself.

**Locally on Windows:**

```bash
pip install -r requirements.txt pyinstaller
pyinstaller --clean --noconfirm pdf_editor.spec
# → dist/PDF_Editor.exe
```

**Locally on Linux/macOS (experimental):**

```bash
make build-exe-docker
```

This cross-builds via Wine in a container. It works for many pure-Python
apps, but Tkinter apps can occasionally hit Tcl/Tk DLL bundling issues under
Wine — if it gives you trouble, use the CI pipeline or a real Windows
machine instead.

---

## License

This project does not currently include a license file. All rights reserved by the author unless otherwise specified.
