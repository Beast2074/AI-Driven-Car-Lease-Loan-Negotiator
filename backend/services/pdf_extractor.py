import os
import io
import platform
import logging
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)

# Configure Tesseract path for Windows if installed
if platform.system() == "Windows":
    tesseract_candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe")
    ]
    for cand in tesseract_candidates:
        if os.path.exists(cand):
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = cand
                break
            except Exception:
                pass


class PDFExtractor:
    @staticmethod
    def extract_text(file_content: bytes) -> Optional[str]:
        """
        Extract text from PDF bytes using PyMuPDF (fitz), with Tesseract OCR fallback for scanned pages.
        """
        if not file_content:
            return ""

        extracted_pages = []

        # 1. Primary: PyMuPDF (pymupdf / fitz)
        try:
            try:
                import pymupdf as fitz  # Modern import name (pymupdf >= 1.24)
            except ImportError:
                import fitz  # Legacy fallback for older pymupdf installs
            doc = fitz.open(stream=file_content, filetype="pdf")
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text().strip()

                # If page has sufficient digital text, use it
                if len(page_text) >= 40:
                    extracted_pages.append(page_text)
                else:
                    # Page is an image or scanned document: run OCR
                    try:
                        import pytesseract
                        pix = page.get_pixmap(dpi=150)
                        img = Image.open(io.BytesIO(pix.tobytes("png")))
                        ocr_text = pytesseract.image_to_string(img).strip()
                        if ocr_text:
                            extracted_pages.append(ocr_text)
                        elif page_text:
                            extracted_pages.append(page_text)
                    except Exception as ocr_err:
                        logger.warning(f"OCR failed for page {page_num}: {ocr_err}")
                        if page_text:
                            extracted_pages.append(page_text)

            full_text = "\n\n".join(extracted_pages).strip()
            if full_text:
                return full_text
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")

        # 2. Secondary: pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page in pdf.pages:
                    txt = page.extract_text()
                    if txt:
                        extracted_pages.append(txt)
            full_text = "\n\n".join(extracted_pages).strip()
            if full_text:
                return full_text
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")

        # 3. Tertiary: PyPDF2 fallback
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            for page in pdf_reader.pages:
                txt = page.extract_text()
                if txt:
                    extracted_pages.append(txt)
            full_text = "\n\n".join(extracted_pages).strip()
            if full_text:
                return full_text
        except Exception as e:
            logger.error(f"PyPDF2 extraction error: {e}")

        return "\n\n".join(extracted_pages).strip()

    @staticmethod
    def extract_text_from_path(file_path: str) -> Optional[str]:
        """Extract text from a file path"""
        try:
            with open(file_path, "rb") as f:
                return PDFExtractor.extract_text(f.read())
        except Exception as e:
            logger.error(f"Failed to read file from path {file_path}: {e}")
            return ""


pdf_extractor = PDFExtractor()
