"""
PDF Parser Service
──────────────────────────────────────────────────
Extracts text from PDF files using PyMuPDF as the
primary engine, with EasyOCR as a fallback for
scanned / image-heavy documents.

Memory optimizations (Render 512 MB free plan):
 - PDF is streamed from URL; never fully loaded into RAM as bytes.
 - OCR is capped at MAX_OCR_PAGES (independent of MAX_PARSE_PAGES).
 - Per-page gc.collect() + pixmap delete prevents accumulation.
 - Structured log lines include RSS memory at each stage.
"""

from __future__ import annotations

import gc
import logging
import os
import tempfile
import time
from typing import Tuple

import fitz  # PyMuPDF
import numpy as np
import requests

logger = logging.getLogger("judgeai.pdf_parser")

# ── Configuration ─────────────────────────────────────────────
TEXT_LENGTH_THRESHOLD = 100  # chars; below this → fallback to OCR
MAX_PARSE_PAGES = int(os.getenv("JUDGEAI_MAX_PARSE_PAGES", "12"))
MAX_OCR_PAGES = int(os.getenv("JUDGEAI_MAX_OCR_PAGES", "6"))   # hard cap for OCR path
OCR_DPI = int(os.getenv("JUDGEAI_OCR_DPI", "72"))              # 72 DPI is enough for text OCR
REQUEST_TIMEOUT_SEC = float(os.getenv("JUDGEAI_PDF_REQUEST_TIMEOUT_SEC", "45"))
STREAM_CHUNK_BYTES = 65_536  # 64 KB chunks when downloading


def _rss_mb() -> float:
    """Return current process RSS in MB (best-effort; 0.0 if psutil unavailable)."""
    try:
        import psutil, os as _os
        return psutil.Process(_os.getpid()).memory_info().rss / 1_048_576
    except Exception:
        return 0.0


# ── Lazy-loaded EasyOCR reader (heavy initialisation ~250 MB) ─
_ocr_reader = None


def _get_ocr_reader():
    """Lazy-load the EasyOCR reader to avoid startup overhead."""
    global _ocr_reader
    if _ocr_reader is None:
        logger.info("[pdf_parser] Initialising EasyOCR reader (rss=%.1f MB)", _rss_mb())
        t0 = time.monotonic()
        import easyocr
        _ocr_reader = easyocr.Reader(["en"], gpu=False)
        logger.info(
            "[pdf_parser] EasyOCR ready in %.2fs (rss=%.1f MB)",
            time.monotonic() - t0, _rss_mb(),
        )
    return _ocr_reader


# ── Internal helpers ───────────────────────────────────────────

def _stream_pdf_to_tempfile(pdf_url: str) -> str:
    """
    Stream-download a PDF URL into a named temp file.
    Returns the temp file path. Caller must os.unlink() it.

    Streaming avoids loading the full PDF binary into RAM
    (critical for Render's 512 MB limit).
    """
    logger.info(
        "[pdf_parser] Streaming PDF from %s… (rss=%.1f MB)", pdf_url[:80], _rss_mb()
    )
    t0 = time.monotonic()
    response = requests.get(pdf_url, timeout=REQUEST_TIMEOUT_SEC, stream=True)
    response.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    total_bytes = 0
    try:
        for chunk in response.iter_content(chunk_size=STREAM_CHUNK_BYTES):
            if chunk:
                tmp.write(chunk)
                total_bytes += len(chunk)
        tmp.flush()
    finally:
        tmp.close()
        response.close()

    logger.info(
        "[pdf_parser] Downloaded %.1f KB in %.2fs (rss=%.1f MB)",
        total_bytes / 1024, time.monotonic() - t0, _rss_mb(),
    )
    return tmp.name


def _extract_pymupdf_text_and_blocks(pdf_path: str) -> Tuple[str, list]:
    """
    Single-pass PyMuPDF extraction: returns (full_text, layout_blocks).
    Opens the document exactly once.
    """
    text_parts: list[str] = []
    blocks_out: list[dict] = []

    doc = fitz.open(pdf_path)
    try:
        page_count = len(doc)
        end = min(page_count, MAX_PARSE_PAGES if MAX_PARSE_PAGES > 0 else page_count)
        logger.info(
            "[pdf_parser] PyMuPDF: %d total pages, processing %d (rss=%.1f MB)",
            page_count, end, _rss_mb(),
        )

        for page_ix in range(end):
            page = doc.load_page(page_ix)

            # Plain text
            t = page.get_text()
            if t:
                text_parts.append(t)

            # Layout blocks (dict mode)
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

    return "\n".join(text_parts).strip(), blocks_out


def _extract_ocr_text(pdf_path: str) -> str:
    """
    EasyOCR fallback: render pages as images and OCR them.
    Capped at MAX_OCR_PAGES and cleans up pixmap memory per page.
    """
    reader = _get_ocr_reader()
    doc = fitz.open(pdf_path)
    ocr_parts: list[str] = []

    try:
        page_count = len(doc)
        end = min(page_count, MAX_OCR_PAGES if MAX_OCR_PAGES > 0 else page_count)
        logger.info(
            "[pdf_parser] EasyOCR fallback: %d total pages, OCR-ing %d at %d DPI (rss=%.1f MB)",
            page_count, end, OCR_DPI, _rss_mb(),
        )

        for page_num in range(end):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=OCR_DPI, colorspace=fitz.csGRAY)  # grayscale → half RAM vs RGB
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)

            results = reader.readtext(img, detail=0)
            if results:
                ocr_parts.extend(results)

            # Aggressive per-page cleanup
            del img
            del pix
            del page
            gc.collect()

            logger.debug(
                "[pdf_parser] OCR page %d/%d done (rss=%.1f MB)", page_num + 1, end, _rss_mb()
            )
    finally:
        doc.close()
        gc.collect()

    return "\n".join(ocr_parts).strip()


# ── Public API ─────────────────────────────────────────────────

def extract_pdf_bundle_from_url(pdf_url: str) -> Tuple[str, list]:
    """
    Download PDF (streamed) → (full_text, layout_blocks).

    Pipeline:
      1. Stream-download to temp file.
      2. Single-pass PyMuPDF text + block extraction.
      3. If text < threshold, EasyOCR fallback.
      4. Temp file deleted in finally block.
    """
    path = _stream_pdf_to_tempfile(pdf_url)
    try:
        t0 = time.monotonic()
        text, blocks = _extract_pymupdf_text_and_blocks(path)
        logger.info(
            "[pdf_parser] PyMuPDF extracted %d chars, %d blocks in %.2fs (rss=%.1f MB)",
            len(text), len(blocks), time.monotonic() - t0, _rss_mb(),
        )

        if len(text) < TEXT_LENGTH_THRESHOLD:
            logger.info(
                "[pdf_parser] Text below threshold (%d < %d), trying OCR…",
                len(text), TEXT_LENGTH_THRESHOLD,
            )
            t1 = time.monotonic()
            text = _extract_ocr_text(path)
            logger.info(
                "[pdf_parser] OCR extracted %d chars in %.2fs (rss=%.1f MB)",
                len(text), time.monotonic() - t1, _rss_mb(),
            )

        return text, blocks
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
        gc.collect()


# ── Legacy helpers (kept for compat, delegate to bundle) ───────

def extract_text_from_url(pdf_url: str) -> str:
    """Compatibility shim: download + extract text only."""
    text, _ = extract_pdf_bundle_from_url(pdf_url)
    return text


def extract_pdf_bundle_from_path(pdf_path: str) -> Tuple[str, list]:
    """Extract bundle from an already-local file path."""
    t0 = time.monotonic()
    text, blocks = _extract_pymupdf_text_and_blocks(pdf_path)
    if len(text) < TEXT_LENGTH_THRESHOLD:
        text = _extract_ocr_text(pdf_path)
    logger.info(
        "[pdf_parser] extract_pdf_bundle_from_path: %d chars in %.2fs",
        len(text), time.monotonic() - t0,
    )
    return text, blocks


def extract_text_from_path(pdf_path: str) -> str:
    """Extract text only from a local file."""
    text, _ = extract_pdf_bundle_from_path(pdf_path)
    return text


def extract_structured_blocks(pdf_path: str) -> list:
    """Extract layout blocks only (compat shim)."""
    _, blocks = _extract_pymupdf_text_and_blocks(pdf_path)
    return blocks
