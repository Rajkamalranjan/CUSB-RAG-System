"""OCR engine selector.

PaddleOCR is preferred when installed with GPU support; Tesseract remains the
CPU fallback for development machines.
"""

from __future__ import annotations


class OCREngine:
    def __init__(self, prefer_gpu: bool = True):
        self.engine = None
        self.name = "none"
        if prefer_gpu:
            try:
                from paddleocr import PaddleOCR

                self.engine = PaddleOCR(use_doc_orientation_classify=True, use_doc_unwarping=True, use_textline_orientation=True)
                self.name = "paddleocr"
            except Exception:
                self.engine = None
        if self.engine is None:
            import pytesseract

            self.engine = pytesseract
            self.name = "tesseract"

    def image_to_text(self, image) -> str:
        if self.name == "paddleocr":
            result = self.engine.predict(image)
            texts = []
            for item in result:
                for text in item.get("rec_texts", []):
                    texts.append(text)
            return "\n".join(texts)
        return self.engine.image_to_string(image, lang="eng")

