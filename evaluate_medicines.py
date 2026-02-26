import os
import csv
import argparse
from collections import Counter

import cv2
import numpy as np
from thefuzz import process, fuzz
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt

from detector import MedicineDetector
from ocr_engine import OCREngine
import database


IGNORED_WORDS = [
    'tablet', 'capsule', 'mg', 'ml', 'exp', 'mfg', 'batch', 'price', 'rs', 'usp', 'ip', 'bp',
    'pv', 'ltd', 'pharmaceuticals', 'india', 'store', 'cool', 'dry', 'place', 'dosage',
    'keep', 'reach', 'children', 'composition', 'marketed', 'manufactured', 'net', 'content',
    'transaction', 'expedience', 'offeric', 'warning', 'schedule', 'prescription',
    'incl', 'taxes', 'all', 'b.no', 'date', 'regd', 'trade', 'mark', 'limited', 'pvt',
    'medication', 'physician', 'directed', 'temperature', 'protect', 'light', 'moisture',
    'not', 'for', 'use', 'only', 'sale', 'retail', 'wholesale', 'distributor', 'logistics',
    'caution', 'practitioner', 'registered', 'medical', 'trihydrate', 'zyshield', 'zydus',
    'german', 'remedies', 'division', 'industrial', 'estate', 'ahmedabad', 'gujarat'
]


def normalize_text(s):
    s = (s or "").lower()
    for w in IGNORED_WORDS:
        s = s.replace(w, " ")
    s = "".join(ch for ch in s if ch.isalnum() or ch.isspace())
    return " ".join(s.split())


def load_labels(csv_path):
    labels = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fn = row.get("filename") or row.get("image") or row.get("file") or ""
            name = row.get("label") or row.get("medicine") or row.get("name") or ""
            if not fn or not name:
                continue
            labels[os.path.basename(fn)] = name.strip()
    return labels


def predict_for_image(detector, ocr_engine, img, med_names):
    annotated, detections = detector.detect(img)
    candidates = []
    for det in detections:
        crop = det["crop"]
        segs = ocr_engine.extract_segments_robust(crop)
        if not segs:
            segs = ocr_engine.extract_segments_fast(crop)
        for raw in segs:
            cleaned = normalize_text(raw)
            if len(cleaned) < 3 or len(cleaned.split()) > 8:
                continue
            best, score = process.extractOne(cleaned, med_names, scorer=fuzz.token_set_ratio)
            final = None
            if score >= 70:
                final = best
            else:
                words = cleaned.split()
                best_score = 0
                best_word = None
                for w in words:
                    if len(w) < 4:
                        continue
                    m, s = process.extractOne(w, med_names, scorer=fuzz.ratio)
                    if s > best_score:
                        best_score = s
                        best_word = m
                if best_score >= 85:
                    final = best_word
            if final:
                candidates.append(final)
    if not candidates:
        return "UNKNOWN"
    counts = Counter(candidates)
    return counts.most_common(1)[0][0]


def evaluate(images_dir, labels_csv, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    database.init_db()
    meds = database.get_all_medicines()
    med_names = [m[1] for m in meds]

    labels = load_labels(labels_csv)

    detector = MedicineDetector()
    ocr_engine = OCREngine()

    y_true = []
    y_pred = []

    for fn, true_name in labels.items():
        path = os.path.join(images_dir, fn)
        if not os.path.exists(path):
            continue
        img = cv2.imread(path)
        if img is None:
            continue
        pred = predict_for_image(detector, ocr_engine, img, med_names)
        y_true.append(true_name)
        y_pred.append(pred)

    if not y_true:
        print("No valid labeled samples found to evaluate.")
        return

    classes = sorted(set(y_true) | set(y_pred))

    report = classification_report(y_true, y_pred, labels=classes, zero_division=0)
    print(report)
    with open(os.path.join(output_dir, "classification_report.txt"), "w", encoding="utf-8") as f:
        f.write(report)

    cm = confusion_matrix(y_true, y_pred, labels=classes)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=classes)
    fig, ax = plt.subplots(figsize=(10, 8))
    disp.plot(ax=ax, cmap="Blues", xticks_rotation=90, colorbar=True)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "confusion_matrix.png"), dpi=150)
    plt.close(fig)

    print("Evaluation complete.")
    print("Report:", os.path.join(output_dir, "classification_report.txt"))
    print("Confusion matrix image:", os.path.join(output_dir, "confusion_matrix.png"))


def main():
    parser = argparse.ArgumentParser(description="Evaluate medicine recognition performance.")
    parser.add_argument("--images", required=True, help="Folder with test images.")
    parser.add_argument("--labels", required=True, help="CSV with ground truth labels.")
    parser.add_argument("--output", default="evaluation_output", help="Folder to store metrics and plots.")
    args = parser.parse_args()
    evaluate(args.images, args.labels, args.output)


if __name__ == "__main__":
    main()

