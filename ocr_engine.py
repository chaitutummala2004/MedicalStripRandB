from paddleocr import PaddleOCR
import numpy as np
import cv2
import logging
import easyocr

# Suppress PaddleOCR logging
logging.getLogger("ppocr").setLevel(logging.ERROR)

class OCREngine:
    def __init__(self):
        print("Loading PaddleOCR Model... (this may take a while first time)")
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
        self.fast_reader = easyocr.Reader(['en'], gpu=False)
        print("PaddleOCR Model loaded")

    def preprocess_image(self, image_array):
        """
        Enhance image for better OCR results.
        """
        if image_array is None:
            return None
            
        # 1. Convert to Gray
        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_array
            
        # 2. Resize if too small (handwriting needs more pixels)
        h, w = gray.shape[:2]
        if h < 1000:
            scale = 2
            gray = cv2.resize(gray, (w*scale, h*scale), interpolation=cv2.INTER_CUBIC)
            
        # 3. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        contrast = clahe.apply(gray)
        
        # 4. Bilateral filter for noise reduction while keeping edges
        denoise = cv2.bilateralFilter(contrast, 9, 75, 75)
        
        return denoise

    def extract_text(self, image_array):
        """
        Extract text from a numpy image array (OpenCV format).
        """
        try:
            # PaddleOCR expects image path or numpy array
            # Result format: [ [ [ [x1,y1], [x2,y2], ... ], ("text", confidence) ], ... ]
            result = self.ocr.ocr(image_array)
            
            if not result or result[0] is None:
                return ""
            
            # Extract all text segments and join them
            detected_texts = []
            for line in result[0]:
                text = line[1][0]
                confidence = line[1][1]
                if confidence > 0.5: # Filter low confidence
                    detected_texts.append(text)
            
            full_text = " ".join(detected_texts)
            return full_text.strip()
            
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""

    def extract_segments(self, image_array, conf_thresh=0.5):
        try:
            result = self.ocr.ocr(image_array)
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

    def extract_segments_multiangle(self, image_array, conf_thresh=0.5):
        try:
            candidates = []
            angles = [0, 90, 180, 270]
            for a in angles:
                if a == 0:
                    img = image_array
                elif a == 90:
                    img = cv2.rotate(image_array, cv2.ROTATE_90_CLOCKWISE)
                elif a == 180:
                    img = cv2.rotate(image_array, cv2.ROTATE_180)
                else:
                    img = cv2.rotate(image_array, cv2.ROTATE_90_COUNTERCLOCKWISE)
                segs = self.extract_segments(img, conf_thresh=conf_thresh)
                if segs:
                    candidates.append(segs)
            if not candidates:
                return []
            best = max(candidates, key=lambda s: (len(s), sum(len(x) for x in s)))
            return best
        except Exception as e:
            print(f"OCR Error: {e}")
            return []

    def extract_segments_fast(self, image_array, conf_thresh=0.5):
        try:
            results = self.fast_reader.readtext(image_array, detail=1)
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

    def extract_segments_robust(self, image_array, conf_thresh=0.5):
        if image_array is None:
            return []
        base = image_array
        variants = []
        variants.append(base)
        pre = self.preprocess_image(base)
        variants.append(pre)
        if len(base.shape) == 3 and base.shape[2] == 3:
            gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
        else:
            gray = base
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(th)
        angles = [0, 90, 180, 270]
        out = []
        seen = set()
        for v in variants:
            for a in angles:
                if a == 0:
                    img = v
                elif a == 90:
                    img = cv2.rotate(v, cv2.ROTATE_90_CLOCKWISE)
                elif a == 180:
                    img = cv2.rotate(v, cv2.ROTATE_180)
                else:
                    img = cv2.rotate(v, cv2.ROTATE_90_COUNTERCLOCKWISE)
                segs1 = self.extract_segments(img, conf_thresh=conf_thresh)
                segs2 = self.extract_segments_fast(img, conf_thresh=conf_thresh)
                for t in segs1 + segs2:
                    key = t.strip().lower()
                    if key and key not in seen:
                        out.append(t)
                        seen.add(key)
        return out

    def extract_text_robust(self, image_array):
        segs = self.extract_segments_robust(image_array)
        if not segs:
            return ""
        return " ".join(segs).strip()
