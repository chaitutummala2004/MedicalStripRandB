from paddleocr import PaddleOCR
import numpy as np
import cv2
import logging
import easyocr

logging.getLogger("ppocr").setLevel(logging.ERROR)

class OCREngine:
    def __init__(self):
        self.ocr = None
        self.fast_reader = None
        print("OCREngine initialized (models not loaded yet)")

    # ---------------------------
    # Lazy loaders
    # ---------------------------

    def get_paddle(self):
        if self.ocr is None:
            print("Loading PaddleOCR model...")
            self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
        return self.ocr

    def get_easy(self):
        if self.fast_reader is None:
            print("Loading EasyOCR model...")
            self.fast_reader = easyocr.Reader(['en'], gpu=False)
        return self.fast_reader

    # ---------------------------
    # Image Preprocessing
    # ---------------------------

    def preprocess_image(self, image_array):
        if image_array is None:
            return None

        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_array

        h, w = gray.shape[:2]
        if h < 1000:
            gray = cv2.resize(gray, (w*2, h*2), interpolation=cv2.INTER_CUBIC)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        contrast = clahe.apply(gray)

        denoise = cv2.bilateralFilter(contrast, 9, 75, 75)
        return denoise

    # ---------------------------
    # OCR Methods
    # ---------------------------

    def extract_segments(self, image_array, conf_thresh=0.5):
        try:
            paddle = self.get_paddle()
            result = paddle.ocr(image_array)

            segments = []
            if result and result[0]:
                for line in result[0]:
                    text = line[1][0]
                    confidence = line[1][1]
                    if confidence >= conf_thresh:
                        segments.append(text)
            return segments
        except Exception as e:
            print(f"OCR Error: {e}")
            return []

    def extract_segments_fast(self, image_array, conf_thresh=0.5):
        try:
            easy = self.get_easy()
            results = easy.readtext(image_array, detail=1)

            texts = []
            for r in results:
                t = r[1]
                c = r[2]
                if c >= conf_thresh:
                    texts.append(t)
            return texts
        except Exception as e:
            print(f"OCR Error: {e}")
            return []

    def extract_text_robust(self, image_array):
        if image_array is None:
            return ""

        segments = self.extract_segments(image_array)
        if not segments:
            segments = self.extract_segments_fast(image_array)

        return " ".join(segments).strip()
