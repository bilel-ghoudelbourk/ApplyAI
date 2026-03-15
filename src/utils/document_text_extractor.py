from __future__ import annotations

import os
import re
import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET

import pdfplumber

from src.config import get_settings

try:
    import fitz
except ImportError:  # pragma: no cover - optional until dependencies are installed
    fitz = None

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:  # pragma: no cover - optional until dependencies are installed
    RapidOCR = None

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - optional until dependencies are installed
    Image = None
    ImageOps = None


CONTENT_TYPE_TO_EXTENSION = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}


def supported_document_extensions() -> list[str]:
    settings = get_settings().document_ingestion
    return [
        *settings.text_extensions,
        *settings.word_extensions,
        settings.pdf_extension,
        *settings.image_extensions,
    ]


def resolve_upload_filename(filename: str | None, content_type: str | None, *, default_stem: str) -> str:
    raw_name = (filename or "").strip()
    if raw_name:
        suffix = Path(raw_name).suffix.lower()
        if suffix:
            return Path(raw_name).name

    inferred_suffix = CONTENT_TYPE_TO_EXTENSION.get((content_type or "").lower(), ".txt")
    return f"{default_stem}{inferred_suffix}"


def is_supported_document_filename(filename: str) -> bool:
    return Path(filename).suffix.lower() in set(supported_document_extensions())


def describe_supported_document_formats() -> str:
    return ", ".join(supported_document_extensions())


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower() or ".txt"
    handle, temp_path = tempfile.mkstemp(suffix=suffix)
    try:
        os.close(handle)
        Path(temp_path).write_bytes(file_bytes)
        return extract_text_from_document(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def extract_text_from_document(document_path: str | Path) -> str:
    path = Path(document_path)
    if not path.exists():
        raise FileNotFoundError(f"Document file not found at {path}")

    suffix = path.suffix.lower()
    settings = get_settings().document_ingestion

    if suffix == settings.pdf_extension:
        return _extract_pdf_text(path)
    if suffix in settings.word_extensions:
        return _extract_docx_text(path)
    if suffix in settings.text_extensions:
        return _extract_plain_text(path)
    if suffix in settings.image_extensions:
        return _extract_image_text(path)

    raise ValueError(
        "Unsupported file format. Accepted formats: "
        f"{describe_supported_document_formats()}"
    )


def _normalize_extracted_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.splitlines()]
    compact_lines: list[str] = []
    previous_blank = False
    for line in lines:
        if not line:
            if previous_blank:
                continue
            compact_lines.append("")
            previous_blank = True
            continue
        compact_lines.append(line)
        previous_blank = False
    return "\n".join(compact_lines).strip()


def _extract_plain_text(path: Path) -> str:
    raw_bytes = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return _normalize_extracted_text(raw_bytes.decode(encoding))
        except UnicodeDecodeError:
            continue
    return _normalize_extracted_text(raw_bytes.decode("utf-8", errors="ignore"))


def _extract_docx_text(path: Path) -> str:
    xml_parts: list[str] = []
    namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        xml_files = [
            name
            for name in archive.namelist()
            if name == "word/document.xml" or name.startswith("word/header") or name.startswith("word/footer")
        ]
        for xml_name in xml_files:
            root = ET.fromstring(archive.read(xml_name))
            paragraphs: list[str] = []
            for paragraph in root.findall(".//w:p", namespaces):
                texts = [
                    node.text
                    for node in paragraph.findall(".//w:t", namespaces)
                    if node.text
                ]
                if texts:
                    paragraphs.append("".join(texts))
            if paragraphs:
                xml_parts.append("\n".join(paragraphs))

    extracted = _normalize_extracted_text("\n\n".join(xml_parts))
    if not extracted:
        raise ValueError("Aucun texte exploitable n'a ete extrait du fichier .docx.")
    return extracted


def _extract_pdf_text(path: Path) -> str:
    settings = get_settings().document_ingestion
    extracted_pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                extracted_pages.append(page_text)

    pdf_text = _normalize_extracted_text("\n\n".join(extracted_pages))
    if len(pdf_text) >= settings.pdf_text_min_chars_before_ocr or not settings.enable_ocr:
        if pdf_text:
            return pdf_text
        if not settings.enable_ocr:
            raise ValueError("Aucun texte exploitable n'a ete extrait du PDF.")

    ocr_text = _extract_pdf_text_with_ocr(path)
    combined = _normalize_extracted_text("\n\n".join(part for part in [pdf_text, ocr_text] if part))
    if not combined:
        raise ValueError("Aucun texte exploitable n'a ete extrait du PDF, meme avec OCR.")
    return combined


def _extract_pdf_text_with_ocr(path: Path) -> str:
    settings = get_settings().document_ingestion
    if fitz is None:
        raise RuntimeError("Le support OCR PDF requiert PyMuPDF. Reinstalle les dependances du projet.")

    ocr_pages: list[str] = []
    with fitz.open(path) as document:
        page_count = min(document.page_count, settings.pdf_ocr_max_pages)
        for index in range(page_count):
            page = document.load_page(index)
            matrix = fitz.Matrix(settings.pdf_ocr_zoom, settings.pdf_ocr_zoom)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
                temp_image_path = Path(handle.name)
            try:
                pixmap.save(temp_image_path)
                page_text = _extract_image_text(temp_image_path)
                if page_text:
                    ocr_pages.append(page_text)
            finally:
                temp_image_path.unlink(missing_ok=True)

    return _normalize_extracted_text("\n\n".join(ocr_pages))


def _extract_image_text(path: Path) -> str:
    settings = get_settings().document_ingestion
    if not settings.enable_ocr:
        raise ValueError("L'OCR est desactive pour les images.")
    processed_path = _prepare_image_for_ocr(path)
    try:
        result = _get_ocr_engine()(str(processed_path))
    finally:
        if processed_path != path:
            processed_path.unlink(missing_ok=True)

    ocr_lines: list[str] = []
    detections = result[0] if isinstance(result, tuple) else result
    for item in detections or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            text_value = item[1]
            if isinstance(text_value, str) and text_value.strip():
                ocr_lines.append(text_value)

    extracted = _normalize_extracted_text("\n".join(ocr_lines))
    if not extracted:
        raise ValueError("Aucun texte exploitable n'a ete detecte par OCR.")
    return extracted


def _prepare_image_for_ocr(path: Path) -> Path:
    settings = get_settings().document_ingestion
    if Image is None or ImageOps is None:
        return path

    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("L")
        max_side = max(image.size)
        if max_side > settings.ocr_max_image_side:
            ratio = settings.ocr_max_image_side / max_side
            resized_size = (
                max(1, int(image.width * ratio)),
                max(1, int(image.height * ratio)),
            )
            image = image.resize(resized_size)

        image = ImageOps.autocontrast(image)
        thresholded = image.point(lambda pixel: 255 if pixel > settings.ocr_binarize_threshold else 0)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
            temp_path = Path(handle.name)
        thresholded.save(temp_path)
        return temp_path


@lru_cache(maxsize=1)
def _get_ocr_engine():
    if RapidOCR is None:
        raise RuntimeError(
            "Le support OCR requiert rapidocr-onnxruntime. Reinstalle les dependances depuis requirements.txt."
        )
    return RapidOCR()
