# Linux dev/test image for PDF Editor.
#
# This image is for running the app and smoke-testing it in a consistent
# environment (locally or in CI) — it does NOT produce a Windows .exe.
# See .github/workflows/build.yml for the real .exe build, which runs
# PyInstaller on an actual Windows runner.

FROM python:3.11-slim

# Tkinter + a virtual display (Xvfb) so the GUI can actually initialize
# in a headless container, plus the shared libs PyMuPDF/Pillow need.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        xvfb \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pdf_editor.py .

# Runs the GUI against a virtual framebuffer so `docker run` works
# on a headless CI machine or a server with no display attached.
CMD ["xvfb-run", "-a", "python", "pdf_editor.py"]
