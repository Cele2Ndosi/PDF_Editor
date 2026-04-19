"""
=============================================================
  FULLY FUNCTIONAL PDF EDITOR
  Features:
    - Open / Save / Save As PDF
    - Multi-page scroll view
    - Add text anywhere (click to place)
    - Add highlight / rectangle / circle annotations
    - Add freehand drawing
    - Delete annotations
    - Undo / Redo
    - Zoom In / Out / Fit
    - Page navigation
    - Toolbar with mode buttons
    - Status bar
=============================================================
"""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, font as tkfont
import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw
import io
import copy


# ─────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────
MODES = ["select", "text", "highlight", "rect", "circle", "draw", "erase"]
MODE_CURSORS = {
    "select": "arrow",
    "text": "xterm",
    "highlight": "crosshair",
    "rect": "crosshair",
    "circle": "crosshair",
    "draw": "pencil",
    "erase": "X_cursor",
}
COLORS = ["#FFD700", "#FF4444", "#4488FF", "#44BB44", "#FF8800", "#AA44FF", "#000000", "#FFFFFF"]
ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]

# ─────────────────────────────────────────────────────────
#  ANNOTATION MODEL
# ─────────────────────────────────────────────────────────
class Annotation:
    """One annotation on one PDF page (document-space coords)."""
    def __init__(self, kind, page, **kw):
        self.kind = kind      # text | highlight | rect | circle | draw
        self.page = page
        self.data = kw        # kind-specific payload

    def copy(self):
        return Annotation(self.kind, self.page, **copy.deepcopy(self.data))


# ─────────────────────────────────────────────────────────
#  PDF ENGINE
# ─────────────────────────────────────────────────────────
class PDFEngine:
    def __init__(self):
        self.doc = None
        self.path = None
        self.annotations: list[Annotation] = []   # all user annotations
        self._undo_stack: list = []
        self._redo_stack: list = []

    # ── file ──────────────────────────────────────────────
    def load(self, path):
        self.doc = fitz.open(path)
        self.path = path
        self.annotations.clear()
        self._undo_stack.clear()
        self._redo_stack.clear()

    def page_count(self):
        return len(self.doc) if self.doc else 0

    def page_size(self, page_num):
        p = self.doc[page_num]
        return p.rect.width, p.rect.height

    # ── rendering ─────────────────────────────────────────
    def render_page(self, page_num, zoom):
        """Render PDF page + all annotations → PIL Image."""
        page = self.doc[page_num]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Draw annotations on the PIL image
        draw = ImageDraw.Draw(img, "RGBA")
        for ann in self.annotations:
            if ann.page != page_num:
                continue
            self._draw_annotation(draw, ann, zoom)

        return img

    def _draw_annotation(self, draw, ann, zoom):
        z = zoom
        d = ann.data
        if ann.kind == "highlight":
            x0, y0, x1, y1 = d["x0"]*z, d["y0"]*z, d["x1"]*z, d["y1"]*z
            draw.rectangle([x0, y0, x1, y1], fill=(*self._hex_to_rgb(d["color"]), 100))
        elif ann.kind == "rect":
            x0, y0, x1, y1 = d["x0"]*z, d["y0"]*z, d["x1"]*z, d["y1"]*z
            draw.rectangle([x0, y0, x1, y1], outline=d["color"], width=int(d.get("width", 2)))
        elif ann.kind == "circle":
            x0, y0, x1, y1 = d["x0"]*z, d["y0"]*z, d["x1"]*z, d["y1"]*z
            draw.ellipse([x0, y0, x1, y1], outline=d["color"], width=int(d.get("width", 2)))
        elif ann.kind == "draw":
            pts = [(p[0]*z, p[1]*z) for p in d["points"]]
            if len(pts) >= 2:
                draw.line(pts, fill=d["color"], width=int(d.get("width", 2)))
        elif ann.kind == "text":
            draw.text((d["x"]*z, d["y"]*z), d["text"],
                      fill=d.get("color", "#000000"))

    def _hex_to_rgb(self, h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    # ── annotation management ──────────────────────────────
    def add_annotation(self, ann: Annotation):
        self._undo_stack.append(("add", ann))
        self._redo_stack.clear()
        self.annotations.append(ann)

    def delete_annotation(self, ann: Annotation):
        if ann in self.annotations:
            self._undo_stack.append(("del", ann))
            self._redo_stack.clear()
            self.annotations.remove(ann)

    def undo(self):
        if not self._undo_stack:
            return False
        entry = self._undo_stack.pop()
        action = entry[0]
        if action == "add":
            ann = entry[1]
            self.annotations.remove(ann)
            self._redo_stack.append(("add", ann))
        elif action == "del":
            ann = entry[1]
            self.annotations.append(ann)
            self._redo_stack.append(("del", ann))
        elif action == "move":
            _, ann, old_data, new_data = entry
            ann.data = copy.deepcopy(old_data)
            self._redo_stack.append(("move", ann, old_data, new_data))
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        entry = self._redo_stack.pop()
        action = entry[0]
        if action == "add":
            ann = entry[1]
            self.annotations.append(ann)
            self._undo_stack.append(("add", ann))
        elif action == "del":
            ann = entry[1]
            self.annotations.remove(ann)
            self._undo_stack.append(("del", ann))
        elif action == "move":
            _, ann, old_data, new_data = entry
            ann.data = copy.deepcopy(new_data)
            self._undo_stack.append(("move", ann, old_data, new_data))
        return True

    def hit_test(self, page_num, doc_x, doc_y, radius=10):
        """Return annotation under (doc_x, doc_y) or None."""
        for ann in reversed(self.annotations):
            if ann.page != page_num:
                continue
            d = ann.data
            if ann.kind in ("highlight", "rect", "circle"):
                if d["x0"]-radius <= doc_x <= d["x1"]+radius and \
                   d["y0"]-radius <= doc_y <= d["y1"]+radius:
                    return ann
            elif ann.kind == "text":
                if abs(doc_x - d["x"]) < 80 and abs(doc_y - d["y"]) < 20:
                    return ann
            elif ann.kind == "draw":
                for p in d["points"]:
                    if abs(p[0]-doc_x) < radius and abs(p[1]-doc_y) < radius:
                        return ann
        return None

    # ── export ─────────────────────────────────────────────
    def export(self, path):
        new_doc = fitz.open()
        for i in range(len(self.doc)):
            page = self.doc[i]
            rect = page.rect
            new_page = new_doc.new_page(width=rect.width, height=rect.height)
            new_page.show_pdf_page(rect, self.doc, i)
            # Apply annotations as native PDF annotations
            for ann in self.annotations:
                if ann.page != i:
                    continue
                d = ann.data
                if ann.kind == "highlight":
                    quad = fitz.Quad(fitz.Rect(d["x0"], d["y0"], d["x1"], d["y1"]))
                    a = new_page.add_highlight_annot(quad)
                    a.update()
                elif ann.kind == "rect":
                    a = new_page.add_rect_annot(fitz.Rect(d["x0"], d["y0"], d["x1"], d["y1"]))
                    r, g, b = self._hex_to_rgb(d["color"])
                    a.set_colors(stroke=(r/255, g/255, b/255))
                    a.update()
                elif ann.kind == "circle":
                    a = new_page.add_circle_annot(fitz.Rect(d["x0"], d["y0"], d["x1"], d["y1"]))
                    r, g, b = self._hex_to_rgb(d["color"])
                    a.set_colors(stroke=(r/255, g/255, b/255))
                    a.update()
                elif ann.kind == "text":
                    new_page.insert_text(
                        (d["x"], d["y"]), d["text"],
                        fontsize=d.get("size", 12), color=(0, 0, 0))
                elif ann.kind == "draw":
                    pts = [fitz.Point(p[0], p[1]) for p in d["points"]]
                    if len(pts) >= 2:
                        r, g, b = self._hex_to_rgb(d["color"])
                        new_page.draw_polyline(pts, color=(r/255, g/255, b/255),
                                               width=d.get("width", 2))
        new_doc.save(path)
        new_doc.close()


# ─────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────
class PDFEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Editor")
        self.root.geometry("1200x820")
        self.root.configure(bg="#2b2b2b")

        self.engine = PDFEngine()
        self.zoom_idx = 2          # default 1.0
        self.zoom = ZOOM_LEVELS[self.zoom_idx]
        self.mode = "select"
        self.color = "#FFD700"
        self.pen_width = 2
        self.font_size = 12

        # drawing state
        self._drag_start = None
        self._draw_points = []
        self._preview_id = None
        self._draw_line_id = None
        self._selected_ann = None
        self._drag_ann_origin = None

        # page layout cache: list of (page_num, canvas_y_top, canvas_y_bottom)
        self._page_layout = []
        self._tk_images = []       # keep references alive

        self._build_ui()
        self._bind_events()
        self._status("Ready — Open a PDF to start editing.")

    # ═══════════════════════════════════════════════════════
    #  UI CONSTRUCTION
    # ═══════════════════════════════════════════════════════
    def _build_ui(self):
        # ── Menu bar ──────────────────────────────────────
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        fm = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=fm)
        fm.add_command(label="Open PDF…      Ctrl+O", command=self.open_pdf)
        fm.add_command(label="Save              Ctrl+S", command=self.save_pdf)
        fm.add_command(label="Save As…         Ctrl+Shift+S", command=self.save_as_pdf)
        fm.add_separator()
        fm.add_command(label="Quit", command=self.root.quit)

        em = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=em)
        em.add_command(label="Undo    Ctrl+Z", command=self.undo)
        em.add_command(label="Redo    Ctrl+Y", command=self.redo)

        vm = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=vm)
        vm.add_command(label="Zoom In   Ctrl++", command=self.zoom_in)
        vm.add_command(label="Zoom Out  Ctrl+-", command=self.zoom_out)
        vm.add_command(label="Fit Page   Ctrl+0", command=self.zoom_fit)

        # ── Top toolbar ───────────────────────────────────
        self.toolbar = tk.Frame(self.root, bg="#3c3c3c", height=48)
        self.toolbar.pack(fill="x", side="top")

        # File buttons
        self._tb_btn("📂 Open", self.open_pdf)
        self._tb_btn("💾 Save", self.save_pdf)
        self._tb_sep()

        # Zoom
        self._tb_btn("🔍−", self.zoom_out)
        self.zoom_label = tk.Label(self.toolbar, text="100%", bg="#3c3c3c",
                                   fg="white", width=5, font=("Arial", 10))
        self.zoom_label.pack(side="left", padx=2)
        self._tb_btn("🔍+", self.zoom_in)
        self._tb_sep()

        # Mode buttons (radio-style)
        self._mode_buttons = {}
        mode_specs = [
            ("select", "⭢ Select"),
            ("text",   "T Text"),
            ("highlight","🖊 Highlight"),
            ("rect",   "☐ Rect"),
            ("circle", "○ Circle"),
            ("draw",   "✏ Draw"),
            ("erase",  "✖ Erase"),
        ]
        for m, label in mode_specs:
            btn = tk.Button(self.toolbar, text=label, bg="#555555", fg="white",
                            relief="flat", padx=8, pady=4,
                            font=("Arial", 9, "bold"),
                            command=lambda mm=m: self.set_mode(mm))
            btn.pack(side="left", padx=2, pady=4)
            self._mode_buttons[m] = btn
        self._tb_sep()

        # Color swatches
        tk.Label(self.toolbar, text="Color:", bg="#3c3c3c", fg="white",
                 font=("Arial", 9)).pack(side="left", padx=(4, 2))
        self._color_btns = []
        for c in COLORS:
            b = tk.Button(self.toolbar, bg=c, width=2, height=1,
                          relief="solid", bd=1,
                          command=lambda cc=c: self.set_color(cc))
            b.pack(side="left", padx=1, pady=6)
            self._color_btns.append(b)
        self._tb_sep()

        # Pen width
        tk.Label(self.toolbar, text="Width:", bg="#3c3c3c", fg="white",
                 font=("Arial", 9)).pack(side="left", padx=(4, 2))
        self._width_var = tk.IntVar(value=2)
        tk.Spinbox(self.toolbar, from_=1, to=20, width=3,
                   textvariable=self._width_var,
                   command=self._update_width,
                   bg="#555555", fg="white",
                   buttonbackground="#555555").pack(side="left", pady=8)
        self._tb_sep()

        # Undo / Redo
        self._tb_btn("↩ Undo", self.undo)
        self._tb_btn("↪ Redo", self.redo)

        # ── Main area: sidebar + canvas ───────────────────
        self.main_frame = tk.Frame(self.root, bg="#2b2b2b")
        self.main_frame.pack(fill="both", expand=True)

        # Thumbnail sidebar
        self.sidebar = tk.Frame(self.main_frame, bg="#252525", width=130)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="Pages", bg="#252525", fg="#aaaaaa",
                 font=("Arial", 9, "bold")).pack(pady=(8, 4))

        self.thumb_canvas = tk.Canvas(self.sidebar, bg="#252525",
                                      highlightthickness=0)
        thumb_scroll = tk.Scrollbar(self.sidebar, orient="vertical",
                                    command=self.thumb_canvas.yview)
        self.thumb_canvas.configure(yscrollcommand=thumb_scroll.set)
        thumb_scroll.pack(side="right", fill="y")
        self.thumb_canvas.pack(fill="both", expand=True)
        self._thumb_images = []

        # Main canvas + scrollbars
        canvas_frame = tk.Frame(self.main_frame, bg="#2b2b2b")
        canvas_frame.pack(side="left", fill="both", expand=True)

        self.h_scroll = tk.Scrollbar(canvas_frame, orient="horizontal")
        self.h_scroll.pack(side="bottom", fill="x")
        self.v_scroll = tk.Scrollbar(canvas_frame, orient="vertical")
        self.v_scroll.pack(side="right", fill="y")

        self.canvas = tk.Canvas(canvas_frame, bg="#555555",
                                xscrollcommand=self.h_scroll.set,
                                yscrollcommand=self.v_scroll.set,
                                cursor="arrow", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        # ── Status bar ────────────────────────────────────
        self.status_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.status_var,
                 bg="#1e1e1e", fg="#aaaaaa", anchor="w",
                 font=("Arial", 9), padx=8).pack(fill="x", side="bottom")

        # Refresh mode highlight
        self.set_mode("select")

    def _tb_btn(self, label, cmd):
        tk.Button(self.toolbar, text=label, command=cmd,
                  bg="#555555", fg="white", relief="flat",
                  padx=8, pady=4, font=("Arial", 9, "bold"),
                  activebackground="#777777",
                  activeforeground="white").pack(side="left", padx=2, pady=4)

    def _tb_sep(self):
        tk.Frame(self.toolbar, bg="#666666", width=1).pack(
            side="left", fill="y", padx=4, pady=6)

    # ═══════════════════════════════════════════════════════
    #  EVENT BINDING
    # ═══════════════════════════════════════════════════════
    def _bind_events(self):
        self.root.bind("<Control-o>", lambda e: self.open_pdf())
        self.root.bind("<Control-s>", lambda e: self.save_pdf())
        self.root.bind("<Control-S>", lambda e: self.save_as_pdf())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-equal>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.zoom_fit())

        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<MouseWheel>",      self._on_mousewheel)
        self.canvas.bind("<Button-4>",        self._on_mousewheel)
        self.canvas.bind("<Button-5>",        self._on_mousewheel)

    # ═══════════════════════════════════════════════════════
    #  MOUSE EVENTS
    # ═══════════════════════════════════════════════════════
    def _canvas_to_doc(self, cx, cy):
        """Convert canvas (scrolled) coords → document-space coords."""
        rx = self.canvas.canvasx(cx) / self.zoom
        ry = self.canvas.canvasy(cy)
        for pg, ytop, ybot in self._page_layout:
            if ytop <= ry <= ybot:
                return pg, rx, (ry - ytop) / self.zoom
        return None, rx, ry

    def _on_press(self, event):
        page, dx, dy = self._canvas_to_doc(event.x, event.y)
        self._drag_start = (event.x, event.y, page, dx, dy)
        self._draw_points = [(dx, dy)]
        self._selected_ann = None
        self._drag_ann_origin = None

        if self.mode == "select" and page is not None:
            hit = self.engine.hit_test(page, dx, dy)
            if hit:
                self._selected_ann = hit
                self._drag_ann_origin = copy.deepcopy(hit.data)
                self.canvas.config(cursor="fleur")
            else:
                self.canvas.config(cursor="arrow")

        elif self.mode == "text" and page is not None:
            text = simpledialog.askstring("Add Text", "Enter text:",
                                          parent=self.root)
            if text:
                ann = Annotation("text", page,
                                  x=dx, y=dy, text=text,
                                  color=self.color, size=self.font_size)
                self.engine.add_annotation(ann)
                self._render_all()

        elif self.mode == "erase" and page is not None:
            hit = self.engine.hit_test(page, dx, dy)
            if hit:
                self.engine.delete_annotation(hit)
                self._render_all()

    def _on_drag(self, event):
        if self._drag_start is None:
            return
        sx, sy, page, sdx, sdy = self._drag_start

        # ── SELECT: drag annotation to move it ──────────────
        if self.mode == "select" and self._selected_ann is not None:
            pg, dx, dy = self._canvas_to_doc(event.x, event.y)
            delta_x = dx - sdx
            delta_y = dy - sdy
            ann = self._selected_ann
            d = ann.data
            orig = self._drag_ann_origin

            # Move annotation in document space
            if ann.kind == "text":
                d["x"] = orig["x"] + delta_x
                d["y"] = orig["y"] + delta_y
            elif ann.kind in ("highlight", "rect", "circle"):
                w = orig["x1"] - orig["x0"]
                h = orig["y1"] - orig["y0"]
                d["x0"] = orig["x0"] + delta_x
                d["y0"] = orig["y0"] + delta_y
                d["x1"] = orig["x0"] + delta_x + w
                d["y1"] = orig["y0"] + delta_y + h
            elif ann.kind == "draw":
                d["points"] = [
                    (p[0] + delta_x, p[1] + delta_y)
                    for p in orig["points"]
                ]

            # Draw snap/alignment guides
            self._draw_snap_guides(ann, page)
            # Live re-render
            self._render_all(skip_guides=True)
            self._draw_snap_guides(ann, page)
            return

        # ── DRAW freehand ───────────────────────────────────
        if self.mode == "draw":
            pg, dx, dy = self._canvas_to_doc(event.x, event.y)
            self._draw_points.append((dx, dy))
            if self._draw_line_id:
                self.canvas.delete(self._draw_line_id)
            pts_flat = []
            for p in self._draw_points:
                pts_flat += [p[0]*self.zoom,
                              (self._page_top(page) + p[1]*self.zoom)]
            if len(pts_flat) >= 4:
                self._draw_line_id = self.canvas.create_line(
                    pts_flat, fill=self.color,
                    width=self.pen_width, smooth=True)
            return

        # ── Shape previews ──────────────────────────────────
        if self.mode in ("highlight", "rect", "circle"):
            if self._preview_id:
                self.canvas.delete(self._preview_id)
            x0, y0 = sx, sy
            x1, y1 = event.x, event.y
            color = self.color
            if self.mode == "highlight":
                self._preview_id = self.canvas.create_rectangle(
                    x0, y0, x1, y1, fill=color, stipple="gray50",
                    outline=color, width=1)
            elif self.mode == "rect":
                self._preview_id = self.canvas.create_rectangle(
                    x0, y0, x1, y1, outline=color,
                    width=self.pen_width, dash=(4, 4))
            elif self.mode == "circle":
                self._preview_id = self.canvas.create_oval(
                    x0, y0, x1, y1, outline=color,
                    width=self.pen_width, dash=(4, 4))

    def _on_release(self, event):
        if self._drag_start is None:
            return
        sx, sy, page, sdx, sdy = self._drag_start

        # ── SELECT: finish move, register undo ──────────────
        if self.mode == "select":
            self.canvas.config(cursor="arrow")
            self._clear_snap_guides()
            if self._selected_ann is not None and self._drag_ann_origin is not None:
                orig = self._drag_ann_origin
                curr = self._selected_ann.data
                # Only register undo if it actually moved
                moved = (orig != curr)
                if moved:
                    ann = self._selected_ann
                    # Push a "move" undo entry: (move, ann, old_data, new_data)
                    self.engine._undo_stack.append(("move", ann, orig, copy.deepcopy(curr)))
                    self.engine._redo_stack.clear()
                self._render_all()
            self._selected_ann = None
            self._drag_ann_origin = None
            self._drag_start = None
            self._draw_points = []
            return

        if page is None:
            self._drag_start = None
            return

        pg_r, edx, edy = self._canvas_to_doc(event.x, event.y)

        if self.mode in ("highlight", "rect", "circle"):
            if self._preview_id:
                self.canvas.delete(self._preview_id)
                self._preview_id = None
            x0, y0 = min(sdx, edx), min(sdy, edy)
            x1, y1 = max(sdx, edx), max(sdy, edy)
            if abs(x1-x0) > 3 and abs(y1-y0) > 3:
                ann = Annotation(self.mode, page,
                                  x0=x0, y0=y0, x1=x1, y1=y1,
                                  color=self.color, width=self.pen_width)
                self.engine.add_annotation(ann)
                self._render_all()

        elif self.mode == "draw":
            if self._draw_line_id:
                self.canvas.delete(self._draw_line_id)
                self._draw_line_id = None
            if len(self._draw_points) >= 2:
                ann = Annotation("draw", page,
                                  points=list(self._draw_points),
                                  color=self.color, width=self.pen_width)
                self.engine.add_annotation(ann)
                self._render_all()

        self._drag_start = None
        self._draw_points = []

    def _on_mousewheel(self, event):
        if event.num == 4:
            delta = 120
        elif event.num == 5:
            delta = -120
        else:
            delta = event.delta
        self.canvas.yview_scroll(int(-1 * (delta / 120)), "units")

    # ═══════════════════════════════════════════════════════
    #  SNAP / ALIGNMENT GUIDES
    # ═══════════════════════════════════════════════════════
    _SNAP_IDS = []   # canvas item ids for guide lines
    _SNAP_THRESHOLD = 8  # doc-space pixels to snap

    def _ann_edges(self, ann):
        """Return (left, top, right, bottom, cx, cy) in doc space."""
        d = ann.data
        if ann.kind == "text":
            return d["x"], d["y"]-12, d["x"]+80, d["y"], d["x"]+40, d["y"]-6
        elif ann.kind in ("highlight", "rect", "circle"):
            cx = (d["x0"]+d["x1"])/2
            cy = (d["y0"]+d["y1"])/2
            return d["x0"], d["y0"], d["x1"], d["y1"], cx, cy
        elif ann.kind == "draw":
            xs = [p[0] for p in d["points"]]
            ys = [p[1] for p in d["points"]]
            return min(xs), min(ys), max(xs), max(ys), \
                   (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
        return 0, 0, 0, 0, 0, 0

    def _draw_snap_guides(self, moving_ann, page):
        """Draw cyan guide lines when edges align with other annotations."""
        self._clear_snap_guides()
        ml, mt, mr, mb, mcx, mcy = self._ann_edges(moving_ann)
        ytop = self._page_top(page)
        z = self.zoom
        thr = self._SNAP_THRESHOLD

        for ann in self.engine.annotations:
            if ann is moving_ann or ann.page != page:
                continue
            l, t, r, b, cx, cy = self._ann_edges(ann)

            def hline(doc_y):
                cy_ = ytop + doc_y * z
                iid = self.canvas.create_line(
                    0, cy_, 9999, cy_,
                    fill="#00CFFF", dash=(4, 3), width=1)
                self._SNAP_IDS.append(iid)

            def vline(doc_x):
                cx_ = doc_x * z
                iid = self.canvas.create_line(
                    cx_, 0, cx_, 9999,
                    fill="#00CFFF", dash=(4, 3), width=1)
                self._SNAP_IDS.append(iid)

            # Horizontal alignments
            for my, oy in [(mt, t), (mt, b), (mb, t), (mb, b),
                           (mcy, cy), (mcy, t), (mcy, b)]:
                if abs(my - oy) < thr:
                    hline(oy)
            # Vertical alignments
            for mx, ox in [(ml, l), (ml, r), (mr, l), (mr, r),
                           (mcx, cx), (mcx, l), (mcx, r)]:
                if abs(mx - ox) < thr:
                    vline(ox)

    def _clear_snap_guides(self):
        for iid in self._SNAP_IDS:
            self.canvas.delete(iid)
        self._SNAP_IDS.clear()

    def _page_top(self, page_num):
        """Canvas-space Y coordinate of the top of a page."""
        for pg, ytop, _ in self._page_layout:
            if pg == page_num:
                return ytop
        return 0

    # ═══════════════════════════════════════════════════════
    #  RENDERING
    # ═══════════════════════════════════════════════════════
    def _render_all(self, skip_guides=False):
        if not self.engine.doc:
            return
        self.canvas.delete("all")
        self._tk_images.clear()
        self._page_layout.clear()
        self._thumb_images.clear()
        self.thumb_canvas.delete("all")

        GAP = 20
        PADDING = 40  # horizontal centering padding
        y = GAP
        max_w = 0

        for i in range(self.engine.page_count()):
            img = self.engine.render_page(i, self.zoom)
            tk_img = ImageTk.PhotoImage(img)
            self._tk_images.append(tk_img)

            cx = PADDING
            self.canvas.create_image(cx, y, anchor="nw", image=tk_img)
            # page shadow
            self.canvas.create_rectangle(
                cx+3, y+3, cx+img.width+3, y+img.height+3,
                fill="#111111", outline="")
            self.canvas.create_image(cx, y, anchor="nw", image=tk_img)

            self._page_layout.append((i, y, y + img.height))
            y += img.height + GAP
            max_w = max(max_w, img.width)

            # Thumbnail
            thumb = img.copy()
            thumb.thumbnail((100, 140))
            tk_thumb = ImageTk.PhotoImage(thumb)
            self._thumb_images.append(tk_thumb)
            ty = i * 160 + 10
            self.thumb_canvas.create_rectangle(
                10, ty, 120, ty + 150, fill="#333333", outline="#555555")
            self.thumb_canvas.create_image(65, ty + 70, image=tk_thumb)
            self.thumb_canvas.create_text(65, ty + 145,
                text=f"Page {i+1}", fill="#aaaaaa",
                font=("Arial", 8))

        total_h = y
        total_w = max_w + PADDING * 2
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))
        self.thumb_canvas.config(
            scrollregion=(0, 0, 130, self.engine.page_count() * 160 + 20))
        self.zoom_label.config(text=f"{int(self.zoom*100)}%")

    # ═══════════════════════════════════════════════════════
    #  FILE OPERATIONS
    # ═══════════════════════════════════════════════════════
    def open_pdf(self):
        import os
        initial_dir = os.path.expanduser("~/Downloads") if os.path.isdir(
            os.path.expanduser("~/Downloads")) else os.path.expanduser("~")
        path = filedialog.askopenfilename(
            title="Open PDF",
            initialdir=initial_dir,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.engine.load(path)
            self._render_all()
            self.root.title(f"PDF Editor — {path.split('/')[-1]}")
            self._status(f"Opened: {path}  ({self.engine.page_count()} pages)")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open PDF:\n{e}")

    def save_pdf(self):
        if not self.engine.path:
            self.save_as_pdf()
            return
        # Can't overwrite the file that's currently open in PyMuPDF,
        # so save to a temp file then atomically replace the original.
        self._do_save(self.engine.path, overwrite_original=True)

    def save_as_pdf(self):
        import os
        initial_dir = os.path.expanduser("~/Downloads") if os.path.isdir(
            os.path.expanduser("~/Downloads")) else os.path.expanduser("~")
        # Suggest a sensible default filename
        orig_name = os.path.basename(self.engine.path or "document.pdf")
        stem, _ = os.path.splitext(orig_name)
        default_name = f"{stem}_edited.pdf"
        path = filedialog.asksaveasfilename(
            title="Save PDF As",
            initialdir=initial_dir,
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")])
        if path:
            self._do_save(path, overwrite_original=False)

    def _do_save(self, path, overwrite_original=False):
        import os, shutil, tempfile
        try:
            if overwrite_original:
                # Write to a temp file next to the original, then swap
                dir_ = os.path.dirname(os.path.abspath(path))
                # Fall back to user home if original dir isn't writable
                if not os.access(dir_, os.W_OK):
                    dir_ = os.path.expanduser("~")
                    path = os.path.join(dir_, os.path.basename(path))
                fd, tmp_path = tempfile.mkstemp(suffix=".pdf", dir=dir_)
                os.close(fd)
                try:
                    self.engine.export(tmp_path)
                    # Close the original doc so we can replace it
                    self.engine.doc.close()
                    shutil.move(tmp_path, path)
                    # Re-open so the editor stays live
                    self.engine.doc = fitz.open(path)
                    self.engine.path = path
                except Exception:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    raise
            else:
                self.engine.export(path)
                self.engine.path = path

            self._status(f"Saved: {path}")
            messagebox.showinfo("Saved", f"PDF saved successfully!\n\n{path}")
        except PermissionError as e:
            # Guide the user to pick a writable location
            messagebox.showerror(
                "Permission Denied",
                f"Cannot write to:\n{path}\n\n"
                f"Try saving to your Desktop or Downloads folder instead.\n\n"
                f"Details: {e}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save PDF:\n{e}")

    # ═══════════════════════════════════════════════════════
    #  EDIT OPERATIONS
    # ═══════════════════════════════════════════════════════
    def undo(self):
        if self.engine.undo():
            self._render_all()
            self._status("Undo.")
        else:
            self._status("Nothing to undo.")

    def redo(self):
        if self.engine.redo():
            self._render_all()
            self._status("Redo.")
        else:
            self._status("Nothing to redo.")

    # ═══════════════════════════════════════════════════════
    #  ZOOM
    # ═══════════════════════════════════════════════════════
    def zoom_in(self):
        if self.zoom_idx < len(ZOOM_LEVELS) - 1:
            self.zoom_idx += 1
            self.zoom = ZOOM_LEVELS[self.zoom_idx]
            self._render_all()

    def zoom_out(self):
        if self.zoom_idx > 0:
            self.zoom_idx -= 1
            self.zoom = ZOOM_LEVELS[self.zoom_idx]
            self._render_all()

    def zoom_fit(self):
        if not self.engine.doc:
            return
        w, _ = self.engine.page_size(0)
        canvas_w = self.canvas.winfo_width() - 80
        fit_zoom = canvas_w / w
        # snap to nearest
        closest = min(ZOOM_LEVELS, key=lambda z: abs(z - fit_zoom))
        self.zoom_idx = ZOOM_LEVELS.index(closest)
        self.zoom = closest
        self._render_all()

    # ═══════════════════════════════════════════════════════
    #  MODE & COLOR
    # ═══════════════════════════════════════════════════════
    def set_mode(self, mode):
        self.mode = mode
        self.canvas.config(cursor=MODE_CURSORS.get(mode, "arrow"))
        for m, btn in self._mode_buttons.items():
            if m == mode:
                btn.config(bg="#0078d4", fg="white")
            else:
                btn.config(bg="#555555", fg="white")
        self._status(f"Mode: {mode.upper()}")

    def set_color(self, color):
        self.color = color
        for b in self._color_btns:
            b.config(relief="solid", bd=1)
        # highlight selected
        idx = COLORS.index(color)
        self._color_btns[idx].config(relief="sunken", bd=2)

    def _update_width(self):
        self.pen_width = self._width_var.get()

    # ═══════════════════════════════════════════════════════
    #  STATUS
    # ═══════════════════════════════════════════════════════
    def _status(self, msg):
        self.status_var.set(f"  {msg}")


# ─────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.minsize(900, 600)
    app = PDFEditorApp(root)
    root.mainloop()