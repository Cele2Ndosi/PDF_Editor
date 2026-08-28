PYTHON  ?= python3
APP     := pdf_editor.py
IMAGE   := pdf-editor
DIST    := dist

.PHONY: help install run test build clean \
        docker-build docker-run docker-test \
        build-exe-docker

help:
	@echo "Targets:"
	@echo "  install          Install runtime dependencies"
	@echo "  run              Run the app locally"
	@echo "  test             Syntax check + import check"
	@echo "  build            Build a native binary with PyInstaller (exe on Windows)"
	@echo "  docker-build     Build the Linux dev/test container image"
	@echo "  docker-run       Run the app inside the container (via Xvfb)"
	@echo "  docker-test      Smoke-test deps inside the container"
	@echo "  build-exe-docker Experimental: cross-build a .exe from Linux via Wine"
	@echo "  clean            Remove build artifacts"

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) $(APP)

test:
	$(PYTHON) -c "import ast; ast.parse(open('$(APP)').read()); print('OK: syntax valid')"
	$(PYTHON) -c "import fitz, PIL; print('OK: fitz/PIL import cleanly')"

build:
	$(PYTHON) -m pip install --upgrade pyinstaller
	$(PYTHON) -m PyInstaller --clean --noconfirm pdf_editor.spec
	@echo "Output written to $(DIST)/"

docker-build:
	docker build -t $(IMAGE):latest .

docker-run: docker-build
	docker run --rm -it $(IMAGE):latest

docker-test: docker-build
	docker run --rm $(IMAGE):latest \
		python -c "import fitz, PIL; print('OK: deps import cleanly in container')"

# Experimental: builds a real .exe from a Linux host by running PyInstaller
# under Wine inside a container. Tkinter apps under Wine can be flaky
# (Tcl/Tk DLL bundling is the usual culprit) — the GitHub Actions workflow
# in .github/workflows/build.yml, which runs on a real windows-latest
# runner, is the reliable path and is what CI/CD uses. Use this target only
# for a quick local check when you don't have Windows handy.
build-exe-docker:
	docker run --rm -v "$(CURDIR):/src" mymi14s/ubuntu-wine:24.04-3.11 bash -c "\
		wine reg add 'HKCU\\Environment' /v PATH /t REG_EXPAND_SZ /d 'C:\\Python311;%PATH%' /f && \
		wineboot --update && \
		wine cmd /c 'python -m pip install --upgrade pip pyinstaller -r requirements.txt' && \
		wine cmd /c 'python -m PyInstaller --clean --noconfirm pdf_editor.spec' \
	"
	@echo "If it succeeded, look under dist/ for PDF_Editor.exe"

clean:
	rm -rf build dist __pycache__ *.spec.bak
