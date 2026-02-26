from ultralytics import YOLO
import cv2

class MedicineDetector:
    def __init__(self, model_path='yolov8n.pt'):
        # Load a pretrained YOLOv8 model
        # For specific medicine detection, you would train a custom model
        # and pass the path to best.pt here.
        self.model = YOLO(model_path)
    
    def detect(self, frame):
        """
        Detects objects in the frame.
        Returns the frame with bounding boxes and a list of cropped images.
        """
        results = self.model(frame)
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Get coordinates
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Confidence
                conf = float(box.conf[0])
                
                # Class Name
                cls = int(box.cls[0])
                label = self.model.names[cls]
                
                # Filter logic: In a real scenario, you'd filter for 'medicine' class
                # For this demo with generic YOLO, we'll accept 'bottle', 'cup', 'cell phone' (proxy for packet)
                # or just return everything for now to demonstrate the pipeline.
                
                # Crop the detected object
                crop = frame[y1:y2, x1:x2]
                
                detections.append({
                    'box': (x1, y1, x2, y2),
                    'label': label,
                    'confidence': conf,
                    'crop': crop
                })
                
        return results[0].plot(), detections # Returns annotated frame and detection data
