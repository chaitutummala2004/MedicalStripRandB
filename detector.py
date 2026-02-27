from ultralytics import YOLO
import cv2

class MedicineDetector:
    def __init__(self, model_path='yolov8n.pt'):
        self.model_path = model_path
        self.model = None
        print("MedicineDetector initialized (model not loaded yet)")

    def get_model(self):
        if self.model is None:
            print("Loading YOLO model...")
            self.model = YOLO(self.model_path)
        return self.model

    def detect(self, frame):
        """
        Detects objects in the frame.
        Returns annotated frame and detection data.
        """
        model = self.get_model()
        results = model(frame)

        detections = []

        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                conf = float(box.conf[0])
                cls = int(box.cls[0])
                label = model.names[cls]

                crop = frame[y1:y2, x1:x2]

                detections.append({
                    'box': (x1, y1, x2, y2),
                    'label': label,
                    'confidence': conf,
                    'crop': crop
                })

        return results[0].plot(), detections
