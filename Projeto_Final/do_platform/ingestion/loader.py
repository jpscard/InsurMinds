"""Recebimento e extração de conteúdo bruto (texto) de PDFs e imagens.

Estratégia híbrida, página a página:
  1. PDF com camada de texto  -> pdfplumber (rápido, fiel ao layout).
  2. Página sem texto útil    -> renderiza com pypdfium2 e aplica OCR (Tesseract).
  3. Imagem (PNG/JPG/TIFF)    -> pré-processamento leve + OCR.

Assim um PDF "misto" (parte digital, parte digitalizada) é tratado corretamente.
"""
from __future__ import annotations

import hashlib
import io
import math
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps

from ..config import ROOT_DIR, Settings, get_settings

log = logging.getLogger(__name__)

PDF_EXT = {".pdf"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
SUPPORTED_EXT = PDF_EXT | IMG_EXT
MAX_OCR_PIXELS = 30_000_000  # ~ uma página A3 a 300 dpi


class IngestionError(RuntimeError):
    pass


@dataclass
class PageText:
    number: int
    text: str
    method: str  # "texto" | "ocr"


@dataclass
class DocumentText:
    filename: str
    sha256: str
    pages: list[PageText] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(f"[Página {p.number}]\n{p.text}" for p in self.pages)

    @property
    def ocr_pages(self) -> int:
        return sum(p.method == "ocr" for p in self.pages)

    @property
    def char_count(self) -> int:
        return sum(len(p.text) for p in self.pages)


def _default_tesseract() -> str | None:
    """No Windows o instalador não põe o Tesseract no PATH; tenta os locais padrão."""
    if shutil.which("tesseract"):
        return None
    candidates = [Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR",
                  Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR"]
    for d in candidates:
        if (d / "tesseract.exe").exists():
            return str(d / "tesseract.exe")
    return None


def _ocr_image(img: Image.Image, s: Settings) -> str:
    try:
        import pytesseract
    except ImportError as exc:
        raise IngestionError("pytesseract não instalado (pip install pytesseract)") from exc
    cmd = s.tesseract_cmd or _default_tesseract()
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    config = f"--psm {s.ocr_psm}"
    tessdata = s.tessdata_dir or (ROOT_DIR / "data" / "tessdata")
    if tessdata.is_dir() and any(tessdata.glob("*.traineddata")):
        # Variável de ambiente em vez de --tessdata-dir: no Windows o pytesseract não trata
        # aspas no config, o que quebra caminhos com espaço.
        os.environ["TESSDATA_PREFIX"] = str(tessdata)
    gray = ImageOps.autocontrast(ImageOps.grayscale(img))
    try:
        return pytesseract.image_to_string(gray, lang=s.ocr_lang, config=config)
    except pytesseract.TesseractNotFoundError as exc:
        raise IngestionError(
            "Tesseract OCR não encontrado. Instale-o e/ou defina TESSERACT_CMD no .env"
        ) from exc
    except pytesseract.TesseractError:
        # Pacote de idioma 'por' ausente: tenta só inglês em vez de falhar.
        log.warning("Idioma OCR '%s' indisponível; usando 'eng'", s.ocr_lang)
        return pytesseract.image_to_string(gray, lang="eng", config=f"--psm {s.ocr_psm}")


def _load_pdf(data: bytes, s: Settings) -> list[PageText]:
    import pdfplumber
    import pypdfium2 as pdfium

    pages: list[PageText] = []
    try:
        pdf_plumb = pdfplumber.open(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise IngestionError(f"PDF inválido ou protegido: {exc}") from exc

    pdf_render = None
    with pdf_plumb:
        if len(pdf_plumb.pages) > s.max_pages:
            raise IngestionError(f"O documento tem {len(pdf_plumb.pages)} páginas; o limite é {s.max_pages}.")
        for i, page in enumerate(pdf_plumb.pages, start=1):
            text = (page.extract_text() or "").strip()
            if len(text) >= s.min_chars_per_page:
                pages.append(PageText(i, text, "texto"))
                continue
            # Página digitalizada: OCR sobre a renderização
            if pdf_render is None:
                pdf_render = pdfium.PdfDocument(data)
            w, h = pdf_render[i - 1].get_size()  # em pontos (1/72")
            # Limita o tamanho da imagem: uma página gigante a 300 dpi esgotaria a memória.
            scale = min(s.ocr_dpi / 72, math.sqrt(MAX_OCR_PIXELS / max(w * h, 1)))
            img = pdf_render[i - 1].render(scale=scale).to_pil()
            ocr_text = _ocr_image(img, s).strip()
            pages.append(PageText(i, ocr_text or text, "ocr"))
    if pdf_render is not None:
        pdf_render.close()
    return pages


def load_document(filename: str, data: bytes, settings: Settings | None = None) -> DocumentText:
    """Converte um arquivo (bytes) em texto por página."""
    s = settings or get_settings()
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXT:
        raise IngestionError(f"Formato não suportado: {ext}. Use PDF ou imagem ({', '.join(sorted(IMG_EXT))}).")
    if not data:
        raise IngestionError("Arquivo vazio")

    doc = DocumentText(filename=filename, sha256=hashlib.sha256(data).hexdigest())
    if ext in PDF_EXT:
        doc.pages = _load_pdf(data, s)
    else:
        try:
            img = Image.open(io.BytesIO(data))
        except Exception as exc:  # noqa: BLE001
            raise IngestionError(f"Imagem inválida: {exc}") from exc
        doc.pages = [PageText(1, _ocr_image(img, s).strip(), "ocr")]

    if doc.char_count < 50:
        raise IngestionError("Não foi possível extrair texto legível do documento")
    log.info("%s: %d páginas, %d via OCR, %d caracteres",
             filename, len(doc.pages), doc.ocr_pages, doc.char_count)
    return doc


def load_path(path: str | Path, settings: Settings | None = None) -> DocumentText:
    p = Path(path)
    return load_document(p.name, p.read_bytes(), settings)
