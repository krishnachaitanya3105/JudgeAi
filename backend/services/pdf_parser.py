"""
PDF Parser Service
──────────────────────────────────────────────────
Extracts text from PDF files using PyMuPDF as the
primary engine, with EasyOCR as a fallback for
scanned / image-heavy documents.
"""

import os
import tempfile
import fitz  # PyMuPDF
import requests
import easyocr

# ── Configuration ────────────────────────────────
TEXT_LENGTH_THRESHOLD = 100  # chars; below this → fallback to OCR
MAX_PARSE_PAGES = int(os.getenv("JUDGEAI_MAX_PARSE_PAGES", "24"))
OCR_DPI = int(os.getenv("JUDGEAI_OCR_DPI", "220"))
REQUEST_TIMEOUT_SEC = float(os.getenv("JUDGEAI_PDF_REQUEST_TIMEOUT_SEC", "30"))

# Lazy-loaded EasyOCR reader (heavy initialization)
_ocr_reader = None


def _get_ocr_reader():
    """Lazy-load the EasyOCR reader to avoid startup overhead."""
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(["en"], gpu=False)
    return _ocr_reader


def extract_text_pymupdf(pdf_path: str) -> str:
    """
    Extract text from a PDF using PyMuPDF (fitz).
    Iterates through every page and concatenates the text.
    """
    text_parts = []
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    end = min(page_count, MAX_PARSE_PAGES if MAX_PARSE_PAGES > 0 else page_count)
    for i in range(end):
        page = doc.load_page(i)
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts).strip()


def extract_text_easyocr(pdf_path: str) -> str:
    """
    Fallback: render each page as an image and run EasyOCR.
    Used when PyMuPDF returns insufficient text (scanned docs).
    """
    reader = _get_ocr_reader()
    text_parts = []
    doc = fitz.open(pdf_path)

    page_count = len(doc)
    end = min(page_count, MAX_PARSE_PAGES if MAX_PARSE_PAGES > 0 else page_count)
    for page_num in range(end):
        page = doc[page_num]
        # Render page to a high-res pixmap
        pix = page.get_pixmap(dpi=OCR_DPI)
        img_path = os.path.join(
            tempfile.gettempdir(), f"judgeai_ocr_page_{page_num}.png"
        )
        pix.save(img_path)

        # Run OCR on the rendered image
        results = reader.readtext(img_path, detail=0)
        text_parts.extend(results)

        # Clean up temp image
        os.remove(img_path)

    doc.close()
    return "\n".join(text_parts).strip()


def extract_text_from_path(pdf_path: str) -> str:
    """
    Main extraction function.
    1. Try PyMuPDF first
    2. If text is below threshold → fallback to EasyOCR
    3. Return clean extracted text
    """
    # Primary: PyMuPDF
    text = extract_text_pymupdf(pdf_path)

    # Fallback: EasyOCR for scanned documents
    if len(text) < TEXT_LENGTH_THRESHOLD:
        text = extract_text_easyocr(pdf_path)

    return text


def extract_structured_blocks(pdf_path: str) -> list:
    """
    Layout-aware text blocks with bounding boxes (PyMuPDF PDF user space).

    Each item: {"text", "page_number", "bbox": [x0,y0,x1,y1]}
    """
    blocks_out = []
    doc = fitz.open(pdf_path)
    try:
        page_count = len(doc)
        end = min(page_count, MAX_PARSE_PAGES if MAX_PARSE_PAGES > 0 else page_count)
        for page_ix in range(end):
            page = doc.load_page(page_ix)
            page_dict = page.get_text("dict")
            for blk in page_dict.get("blocks", []):
                if blk.get("type") != 0:
                    continue
                parts = []
                for line in blk.get("lines", []):
                    parts.append(
                        "".join(span.get("text", "") for span in line.get("spans", []))
                    )
                text = " ".join(s for s in parts if s).strip()
                if not text:
                    continue
                bb = blk.get("bbox")
                if not bb:
                    continue
                blocks_out.append(
                    {
                        "page_number": page_ix + 1,
                        "text": text,
                        "bbox": [float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])],
                    }
                )
    finally:
        doc.close()
    return blocks_out


def extract_pdf_bundle_from_url(pdf_url: str) -> tuple:
    """Download PDF once; return (full_text, layout_blocks)."""
    response = requests.get(pdf_url, timeout=REQUEST_TIMEOUT_SEC)
    response.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(response.content)
    tmp.close()
    path = tmp.name
    try:
        text = extract_text_from_path(path)
        blocks = extract_structured_blocks(path)
        return text, blocks
    finally:
        os.unlink(path)


def extract_text_from_url(pdf_url: str) -> str:
    """
    Download a PDF from a URL and extract text.
    Useful for extracting from Supabase Storage URLs.
    """
    response = requests.get(pdf_url, timeout=REQUEST_TIMEOUT_SEC)
    response.raise_for_status()

    # Write to a temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(response.content)
    tmp.close()

    try:
        text = extract_text_from_path(tmp.name)
    finally:
        os.unlink(tmp.name)

    return text
