from flask import Flask, render_template, Response, jsonify, request
import io
import cv2
import time
import threading
import numpy as np
from detector import MedicineDetector
from ocr_engine import OCREngine
import database
from thefuzz import process, fuzz
import json
import urllib.request
import re

app = Flask(__name__)
database.init_db()

# Initialize Models
detector = MedicineDetector()
ocr_engine = OCREngine()

camera = None
current_frame = None
lock = threading.Lock()
poll_thread = None
poll_stop = None
using_poll = False
poll_url = None
ANNOTATE_STREAM = False
CURRENT_RECEIPT_ID = None
CURRENT_PRESCRIPTION = {}
COMPANY_INFO = {
    'company_name': 'Smart Pharmacy',
    'address': '123 Main Street',
    'city': 'City',
    'postal_code': '000000',
    'state': 'State',
    'pan': 'XXXXXXXXXX',
    'gst': '22AAAAA0000A1Z6',
    'mobile': '8888888888',
    'email': 'pharmacy@example.com',
    'bank_name': 'ABC Bank',
    'holder_name': 'Smart Pharmacy',
    'account_number': '121212121212',
    'ifsc': 'ABC123456',
    'upi_id': 'smartpharmacy@upi'
}

def ensure_current_receipt():
    global CURRENT_RECEIPT_ID
    if CURRENT_RECEIPT_ID is None:
        CURRENT_RECEIPT_ID = database.create_receipt()
    return CURRENT_RECEIPT_ID

def _normalize_text(s):
    # Allow more characters that might appear in medicine names but remove noise
    s = (s or '').lower()
    s = re.sub(r'[^a-z0-9\s\-]', ' ', s)
    return " ".join(s.split())

def parse_prescription_text(text):
    lines = [l.strip() for l in re.split(r'[\r\n]+', text or '') if l.strip()]
    all_meds = database.get_all_medicines()
    med_names = [m[1] for m in all_meds]
    out = []
    for i, line in enumerate(lines):
        cleaned = _normalize_text(line)
        if len(cleaned) < 3:
            continue
        best = process.extractOne(cleaned, med_names, scorer=fuzz.token_set_ratio)
        matched_name = None
        if best and best[1] >= 70:
            matched_name = best[0]
        else:
            parts = cleaned.split()
            best_score = 0
            best_word = None
            for w in parts:
                if len(w) < 4:
                    continue
                res = process.extractOne(w, med_names, scorer=fuzz.ratio)
                if res and res[1] > best_score:
                    best_score = res[1]
                    best_word = res[0]
            if best_score >= 85:
                matched_name = best_word
        if not matched_name:
            continue
        out.append({'name': matched_name})
    return out

def start_polling(url):
    global poll_thread, poll_stop, using_poll, poll_url
    stop_polling()
    poll_url = url
    poll_stop = threading.Event()
    using_poll = True
    def run():
        global current_frame
        while not poll_stop.is_set():
            try:
                base = poll_url
                ts = str(int(time.time() * 1000))
                u = base + ('&' if '?' in base else '?') + 't=' + ts
                req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'})
                with urllib.request.urlopen(req, timeout=2) as resp:
                    data = resp.read()
                arr = np.frombuffer(data, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None:
                    with lock:
                        current_frame = img.copy()
            except Exception:
                time.sleep(0.2)
                continue
            time.sleep(0.05)
    poll_thread = threading.Thread(target=run, daemon=True)
    poll_thread.start()

def stop_polling():
    global poll_thread, poll_stop, using_poll
    if poll_stop is not None:
        try:
            poll_stop.set()
        except Exception:
            pass
    poll_stop = None
    poll_thread = None
    using_poll = False

def set_camera_source(source):
    global camera
    if camera is not None:
        try:
            camera.release()
        except Exception:
            pass
    if not source or (isinstance(source, str) and source.startswith('local')):
        stop_polling()
        def open_local_camera():
            prefs = [
                cv2.CAP_DSHOW,
                cv2.CAP_MSMF,
                cv2.CAP_VFW,
            ]
            idxs = [0, 1, 2]
            for api in prefs:
                for i in idxs:
                    cap = cv2.VideoCapture(i, api)
                    if cap is not None and cap.isOpened():
                        ok, frm = cap.read()
                        if ok and frm is not None:
                            try:
                                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            except Exception:
                                pass
                            return cap
                        try:
                            cap.release()
                        except Exception:
                            pass
            return None
        # Support explicit index selection via 'local:N'
        if isinstance(source, str) and source.startswith('local:'):
            try:
                idx = int(source.split(':', 1)[1])
            except Exception:
                idx = 0
            opened = None
            for api in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_VFW]:
                cap = cv2.VideoCapture(idx, api)
                if cap is not None and cap.isOpened():
                    ok, frm = cap.read()
                    if ok and frm is not None:
                        opened = cap
                        break
                    try:
                        cap.release()
                    except Exception:
                        pass
            camera = opened if opened is not None else open_local_camera()
        else:
            camera = open_local_camera()
        if camera is None:
            camera = cv2.VideoCapture(0)
            try:
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            except Exception:
                pass
    else:
        stop_polling()
        def try_open(u):
            cap = cv2.VideoCapture(u)
            if cap is not None and cap.isOpened():
                ok, frm = cap.read()
                if ok and frm is not None:
                    return cap
                try:
                    cap.release()
                except Exception:
                    pass
            cap2 = cv2.VideoCapture(u, cv2.CAP_FFMPEG)
            if cap2 is not None and cap2.isOpened():
                ok2, frm2 = cap2.read()
                if ok2 and frm2 is not None:
                    return cap2
                try:
                    cap2.release()
                except Exception:
                    pass
            return None
        # 'usb' alias: try non-default webcam indices
        if source == 'usb':
            for api in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_VFW]:
                for i in [1, 2, 3, 4]:
                    cap = cv2.VideoCapture(i, api)
                    if cap is not None and cap.isOpened():
                        ok, frm = cap.read()
                        if ok and frm is not None:
                            camera = cap
                            try:
                                camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            except Exception:
                                pass
                            return True
                        try:
                            cap.release()
                        except Exception:
                            pass
        candidates = [source]
        if source.startswith('http'):
            base = source.rstrip('/')
            candidates += [
                base + '/video',
                base + '/videofeed',
                base + '/stream/video.mjpeg',
                base + '/mjpeg',
                base + '/cam.mjpeg',
                base + '/video.mjpg',
                base + '/action/stream',
                base + '/stream',
            ]
        opened = None
        for u in candidates:
            cap = try_open(u)
            if cap:
                opened = cap
                break
        if opened:
            camera = opened
            return True
        if source.startswith('http'):
            base = source.rstrip('/')
            shot_candidates = [
                base,
                base + '/shot.jpg',
                base + '/photo.jpg',
                base + '/image',
                base + '/jpg',
                base + '/snapshot',
                base + '/capture',
                base + '/cam-lo.jpg'
            ]
            for u in shot_candidates:
                try:
                    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'})
                    with urllib.request.urlopen(req, timeout=3) as resp:
                        data = resp.read()
                    arr = np.frombuffer(data, dtype=np.uint8)
                    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if img is None:
                        continue
                    start_polling(u)
                    camera = None
                    return True
                except Exception:
                    continue
        camera = cv2.VideoCapture(source)
    return camera is not None and camera.isOpened() or using_poll

set_camera_source('local')

def gen_frames():
    global current_frame
    while True:
        if using_poll:
            frame = None
            with lock:
                if current_frame is not None:
                    frame = current_frame.copy()
            if frame is None:
                time.sleep(0.05)
                continue
        else:
            success, frame = (camera.read() if camera is not None else (False, None))
            if not success:
                time.sleep(0.2)
                continue
        annotated_frame = frame
        if ANNOTATE_STREAM:
            annotated_frame, _ = detector.detect(frame)

        with lock:
            current_frame = frame.copy()
            
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/debug_cameras')
def debug_cameras():
    out = []
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_VFW, cv2.CAP_ANY]
    for idx in range(0, 6):
        for api in backends:
            ok = False
            cap = None
            try:
                cap = cv2.VideoCapture(idx, api)
                if cap is not None and cap.isOpened():
                    s, frm = cap.read()
                    if s and frm is not None:
                        ok = True
            except Exception:
                pass
            try:
                if cap is not None:
                    cap.release()
            except Exception:
                pass
            out.append({'index': idx, 'backend': int(api), 'ok': ok})
    return jsonify(out)

@app.route('/set_camera', methods=['POST'])
def set_camera():
    src = request.form.get('url') or (request.get_json(silent=True) or {}).get('url')
    if not src:
        src = 'local'
    ok = set_camera_source(src)
    if ok:
        return jsonify({'status': 'success', 'source': src})
    return jsonify({'status': 'error', 'message': 'Failed to open camera source'}), 400

@app.route('/auto_local', methods=['POST'])
def auto_local():
    global camera
    stop_polling()
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_VFW]
    found_idx = None
    cap = None
    for idx in range(0, 6):
        for api in backends:
            try:
                c = cv2.VideoCapture(idx, api)
                if c is not None and c.isOpened():
                    ok, frm = c.read()
                    if ok and frm is not None:
                        cap = c
                        found_idx = idx
                        break
            except Exception:
                pass
            try:
                if c is not None:
                    c.release()
            except Exception:
                pass
        if cap is not None:
            break
    if cap is None:
        cap = cv2.VideoCapture(0)
        if cap is not None and cap.isOpened():
            ok, frm = cap.read()
            if ok and frm is not None:
                found_idx = 0
            else:
                try:
                    cap.release()
                except Exception:
                    pass
                cap = None
    if cap is None:
        return jsonify({'status': 'error', 'message': 'No local camera found'}), 400
    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    except Exception:
        pass
    camera = cap
    return jsonify({'status': 'success', 'index': found_idx})

@app.route('/test_camera', methods=['POST'])
def test_camera():
    src = request.form.get('url') or (request.get_json(silent=True) or {}).get('url')
    if not src:
        return jsonify({'status': 'error', 'message': 'No URL provided'}), 400
    out = {'url': src, 'stream': [], 'snapshot': []}
    def check_stream(u):
        ok = False
        cap = cv2.VideoCapture(u)
        if cap is not None and cap.isOpened():
            s, frm = cap.read()
            ok = bool(s and frm is not None)
        try:
            if cap is not None:
                cap.release()
        except Exception:
            pass
        return ok
    def check_snapshot(u):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = resp.read()
            arr = np.frombuffer(data, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return img is not None
        except Exception:
            return False
    if src.startswith('http'):
        base = src.rstrip('/')
        streams = [
            base,
            base + '/video',
            base + '/videofeed',
            base + '/stream/video.mjpeg',
            base + '/mjpeg',
            base + '/cam.mjpeg',
            base + '/video.mjpg',
            base + '/action/stream',
            base + '/stream'
        ]
        shots = [
            base,
            base + '/shot.jpg',
            base + '/photo.jpg',
            base + '/image',
            base + '/jpg',
            base + '/snapshot',
            base + '/capture',
            base + '/cam-lo.jpg'
        ]
        for u in streams:
            out['stream'].append({'url': u, 'ok': check_stream(u)})
        for u in shots:
            out['snapshot'].append({'url': u, 'ok': check_snapshot(u)})
        success = any(x['ok'] for x in out['stream']) or any(x['ok'] for x in out['snapshot'])
        return jsonify({'status': 'success' if success else 'error', 'diagnostics': out})
    else:
        ok = check_stream(src)
        return jsonify({'status': 'success' if ok else 'error', 'diagnostics': {'url': src, 'stream_ok': ok}})

@app.route('/scan', methods=['POST'])
def scan_and_bill():
    global current_frame
    if current_frame is None:
        if using_poll and poll_url:
            try:
                base = poll_url
                ts = str(int(time.time() * 1000))
                u = base + ('&' if '?' in base else '?') + 't=' + ts
                req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'})
                with urllib.request.urlopen(req, timeout=2) as resp:
                    data = resp.read()
                arr = np.frombuffer(data, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None:
                    with lock:
                        current_frame = img.copy()
            except Exception:
                pass
        else:
            try:
                if camera is not None:
                    ok, frm = camera.read()
                    if ok and frm is not None:
                        with lock:
                            current_frame = frm.copy()
            except Exception:
                pass
        if current_frame is None:
            return jsonify({'status': 'error', 'message': 'No frame captured'})
    
    with lock:
        frame_to_process = current_frame.copy()
        
    mode = request.form.get('mode') or request.args.get('mode') or 'accurate'
    preview_flag = request.form.get('preview') or request.args.get('preview')
    preview = False
    if preview_flag:
        val = str(preview_flag).lower()
        preview = val in ['1', 'true', 'yes']
    if mode == 'fast':
        results = []
        segments = ocr_engine.extract_segments_fast(frame_to_process)
        matched_med = None
        all_meds = database.get_all_medicines()
        med_names = [med[1] for med in all_meds]
        aggregated = {}
        ignored_words = [
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
        for detected_text in segments:
            cleaned_text = detected_text.lower()
            for word in ignored_words:
                cleaned_text = cleaned_text.replace(word, ' ')
            cleaned_text = ''.join(e for e in cleaned_text if e.isalnum() or e.isspace())
            cleaned_text = " ".join(cleaned_text.split())
            if len(cleaned_text) < 3:
                continue
            best_match, score = process.extractOne(cleaned_text, med_names, scorer=fuzz.token_set_ratio)
            final_match = None
            if score >= 70:
                final_match = best_match
            if final_match:
                for med in all_meds:
                    if med[1] == final_match:
                        matched_med = med
                        break
            if not matched_med:
                created = database.ensure_medicine(cleaned_text.title())
                if created:
                    matched_med = created
            if matched_med:
                med_id = matched_med[0]
                name = matched_med[1]
                price = matched_med[4]
                stock = matched_med[5]
                if stock > 0:
                    entry = aggregated.get(name)
                    if not entry:
                        aggregated[name] = {'id': med_id, 'price': price, 'count': 1, 'stock': stock}
                    else:
                        entry['count'] += 1
                else:
                    results.append({'status': 'error','medicine': name,'message': 'Out of stock','debug_text': detected_text})
        if not aggregated and not results:
            return jsonify({'status': 'warning', 'message': 'No text detected'})
        if preview:
            preview_items = []
            for name, entry in aggregated.items():
                preview_items.append({'id': entry['id'], 'medicine': name, 'price': entry['price'], 'available': entry['stock'], 'suggested_qty': entry['count']})
            return jsonify({'preview': True, 'matches': preview_items})
        for name, entry in aggregated.items():
            qty = entry['count']
            unit_price = entry['price']
            med_row = database.get_medicine_by_id(entry['id'])
            discount = float(med_row[6] if med_row and len(med_row) > 6 else 0.0)
            allocations = database.reduce_stock_fefo(entry['id'], qty)
            total = 0.0
            for a in allocations:
                part_total = unit_price * a['qty'] * (1 - discount/100.0)
                total += part_total
                database.record_sale_extended(entry['id'], name, a['qty'], part_total, discount, a['mfg_date'], a['exp_date'], a.get('batch_id'))
            results.append({'status': 'success','medicine': name,'qty': qty,'price': unit_price,'total': total,'message': 'Added to bill'})
        return jsonify({'results': results})
    
    _, detections = detector.detect(frame_to_process)
    
    results = []
    aggregated = {}
    
    if not detections:
        pass

    found_any_match = False

    for det in detections:
        crop = det['crop']
        matched_med = None
        all_meds = database.get_all_medicines()
        med_names = [med[1] for med in all_meds]
        ignored_words = [
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

        segments = ocr_engine.extract_segments_fast(crop)
        if not segments:
            segments = ocr_engine.extract_segments_multiangle(crop)
        for detected_text in segments:
            cleaned_text = detected_text.lower()
            for word in ignored_words:
                cleaned_text = cleaned_text.replace(word, ' ')
            cleaned_text = ''.join(e for e in cleaned_text if e.isalnum() or e.isspace())
            cleaned_text = " ".join(cleaned_text.split())
            if len(cleaned_text) < 3:
                continue
            if len(cleaned_text.split()) > 8:
                continue
            best_match, score = process.extractOne(cleaned_text, med_names, scorer=fuzz.token_set_ratio)
            final_match = None
            if score >= 70:
                final_match = best_match
            else:
                words = cleaned_text.split()
                best_word_score = 0
                best_word_match = None
                for word in words:
                    if len(word) < 4:
                        continue
                    match, s = process.extractOne(word, med_names, scorer=fuzz.ratio)
                    if s > best_word_score:
                        best_word_score = s
                        best_word_match = match
                if best_word_score >= 85:
                    final_match = best_word_match
            if final_match:
                for med in all_meds:
                    if med[1] == final_match:
                        matched_med = med
                        break
            if not matched_med:
                created = database.ensure_medicine(cleaned_text.title())
                if created:
                    matched_med = created
            if matched_med:
                found_any_match = True
                med_id = matched_med[0]
                name = matched_med[1]
                price = matched_med[4]
                stock = matched_med[5]
                if stock > 0:
                    entry = aggregated.get(name)
                    if not entry:
                        aggregated[name] = {'id': med_id, 'price': price, 'count': 1, 'stock': stock}
                    else:
                        entry['count'] += 1
                else:
                    results.append({'status': 'error','medicine': name,'message': 'Out of stock','debug_text': detected_text})

    if not aggregated and not results:
        segments = ocr_engine.extract_segments_fast(frame_to_process)
        if not segments:
            segments = ocr_engine.extract_segments_multiangle(frame_to_process)
        if not segments or len(segments) == 0:
            full_text = ocr_engine.extract_text(frame_to_process)
            if full_text and len(full_text.strip()) > 0:
                segments = [full_text]
            else:
                return jsonify({'status': 'warning', 'message': 'No text detected'})
        matched_med = None
        all_meds = database.get_all_medicines()
        med_names = [med[1] for med in all_meds]
        ignored_words = [
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
        for detected_text in segments:
            cleaned_text = detected_text.lower()
            for word in ignored_words:
                cleaned_text = cleaned_text.replace(word, ' ')
            cleaned_text = ''.join(e for e in cleaned_text if e.isalnum() or e.isspace())
            cleaned_text = " ".join(cleaned_text.split())
            if len(cleaned_text) < 3:
                continue
            if len(cleaned_text.split()) > 12:
                continue
            best_match, score = process.extractOne(cleaned_text, med_names, scorer=fuzz.token_set_ratio)
            final_match = None
            if score >= 70:
                final_match = best_match
            else:
                words = cleaned_text.split()
                best_word_score = 0
                best_word_match = None
                for word in words:
                    if len(word) < 4:
                        continue
                    match, s = process.extractOne(word, med_names, scorer=fuzz.ratio)
                    if s > best_word_score:
                        best_word_score = s
                        best_word_match = match
                if best_word_score >= 85:
                    final_match = best_word_match
            if final_match:
                for med in all_meds:
                    if med[1] == final_match:
                        matched_med = med
                        break
            if not matched_med:
                created = database.ensure_medicine(cleaned_text.title())
                if created:
                    matched_med = created
            if matched_med:
                med_id = matched_med[0]
                name = matched_med[1]
                price = matched_med[4]
                stock = matched_med[5]
                if stock > 0:
                    entry = aggregated.get(name)
                    if not entry:
                        aggregated[name] = {'id': med_id, 'price': price, 'count': 1, 'stock': stock}
                    else:
                        entry['count'] += 1
                else:
                    results.append({'status': 'error','medicine': name,'message': 'Out of stock','debug_text': detected_text})
        if not aggregated and not results:
            return jsonify({'status': 'warning', 'message': 'Medicine name not recognized from text.'})
    if preview:
        preview_items = []
        for name, entry in aggregated.items():
            preview_items.append({'id': entry['id'], 'medicine': name, 'price': entry['price'], 'available': entry['stock'], 'suggested_qty': entry['count']})
        return jsonify({'preview': True, 'matches': preview_items})
    for name, entry in aggregated.items():
        qty = entry['count']
        unit_price = entry['price']
        med_row = database.get_medicine_by_id(entry['id'])
        discount = float(med_row[6] if med_row and len(med_row) > 6 else 0.0)
        allocations = database.reduce_stock_fefo(entry['id'], qty)
        total = 0.0
        for a in allocations:
            part_total = unit_price * a['qty'] * (1 - discount/100.0)
            total += part_total
            database.record_sale_extended(entry['id'], name, a['qty'], part_total, discount, a['mfg_date'], a['exp_date'], a.get('batch_id'))
        results.append({'status': 'success','medicine': name,'qty': qty,'price': unit_price,'total': total,'message': 'Added to bill'})
    
    return jsonify({'results': results})

@app.route('/sales_data')
def sales_data():
    sales = database.get_recent_sales()
    data = []
    for s in sales:
        data.append({
            'id': s[0],
            'medicine': s[1],
            'quantity': s[2],
            'total': s[3],
            'time': s[4]
        })
    return jsonify(data)

@app.route('/bill', methods=['POST'])
def bill_items():
    try:
        rid = ensure_current_receipt()
        payload = request.get_json(force=True, silent=False)
        items = payload.get('items', []) if payload else []
        results = []
        if not items:
            return jsonify({'status': 'error', 'message': 'No items provided'})
        for it in items:
            med_id = it.get('id')
            raw_qty = it.get('qty', 1)
            try:
                qty = int(raw_qty)
            except Exception:
                qty = 1
            if qty <= 0:
                qty = 1
            med = None
            if med_id:
                rows = database.get_all_medicines()
                for r in rows:
                    if r[0] == med_id:
                        med = r
                        break
            if not med:
                name = it.get('name')
                if not name:
                    results.append({'status': 'error', 'message': 'Missing name and id'})
                    continue
                med = database.get_medicine_by_name(name)
            if not med:
                created = database.ensure_medicine(it.get('name', 'Unknown'))
                med = created
            med_id = med[0]
            name = med[1]
            price = med[4]
            stock = med[5]
            med_row = database.get_medicine_by_id(med_id)
            discount = float(med_row[6] if med_row and len(med_row) > 6 else 0.0)
            database.add_receipt_item(rid, med_id, name, qty, price, discount)
            line_total = price * qty * (1 - discount/100.0)
            results.append({'status': 'success', 'medicine': name, 'qty': qty, 'price': price, 'total': line_total})
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Billing failed: {str(e)}'})

@app.route('/report')
def report():
    rows = database.get_inventory_report()
    out = []
    for r in rows:
        out.append({'medicine': r[0], 'stock': r[1], 'sold': r[2]})
    batches = database.get_batches_report()
    b = []
    for row in batches:
        b.append({'medicine': row[0], 'batch_stock': row[1], 'mfg_date': row[2], 'exp_date': row[3], 'discount': row[4], 'batch_id': row[5]})
    current = []
    try:
        if CURRENT_RECEIPT_ID is not None:
            items = database.get_receipt_items(CURRENT_RECEIPT_ID)
            for it in items:
                _, mid, name, qty, unit_price, discount = it
                total = unit_price * qty * (1 - (discount or 0.0)/100.0)
                current.append({'medicine': name, 'qty': qty, 'unit_price': unit_price, 'discount': discount or 0.0, 'total': total})
    except Exception:
        pass
    hist_rows = database.list_receipts(limit=20)
    history = []
    for r in hist_rows:
        history.append({'id': r[0], 'number': r[1], 'customer': r[2], 'payment': r[4], 'total': r[5], 'printed': bool(r[6]), 'time': r[7]})
    return jsonify({'summary': out, 'batches': b, 'current_receipt': current, 'history': history})

@app.route('/import_dataset', methods=['POST'])
def import_dataset():
    f = request.files.get('file')
    if not f:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400
    try:
        content = f.read().decode('utf-8')
        database.import_csv_text(content)
        return jsonify({'status': 'success', 'message': 'Dataset imported'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/print_receipt', methods=['POST'])
def print_receipt():
    try:
        payload = request.get_json(silent=True) or {}
        name = payload.get('customer_name') or ''
        phone = payload.get('customer_phone') or ''
        payment = payload.get('payment_mode') or ''
        number = payload.get('number') or None
        c_addr = payload.get('customer_address') or ''
        c_city = payload.get('customer_city') or ''
        c_postal = payload.get('customer_postal') or ''
        c_state = payload.get('customer_state') or ''
        c_email = payload.get('customer_email') or ''
        c_gst = payload.get('customer_gst') or ''
        c_pan = payload.get('customer_pan') or ''
        rid = ensure_current_receipt()
        database.update_receipt_meta(rid, number=number, customer_name=name, customer_phone=phone, payment_mode=payment)
        total, detailed = database.finalize_receipt_and_reduce_stock(rid)
        subtotal = sum(it['unit_price'] * it['qty'] for it in detailed)
        discount_total = sum((it['unit_price'] * it['qty']) * ((it['discount'] or 0.0)/100.0) for it in detailed)
        cgst = 0.0
        sgst = 0.0
        igst = 0.0
        vat = 0.0
        others = 0.0
        extra_fees = 0.0
        grand_total = total + cgst + sgst + igst + vat + others + extra_fees
        invoice_no = number or f"INV-{rid}"
        today_str = time.strftime('%d/%m/%Y')
        due_str = today_str
        ci = COMPANY_INFO
        rows_html = ''.join([
            f"<tr><td>{i+1}</td><td>{it['medicine']}</td><td></td><td>{it['unit_price']:.2f}</td><td>{it['qty']}</td><td>{it['amount']:.2f}</td></tr>"
            for i, it in enumerate(detailed)
        ])
        totals_html = f"""
        <table style="width:100%; border-collapse:collapse; margin-top:8px;">
          <tr><td style="width:70%;"></td><td style="width:30%;">
            <table style="width:100%;">
              <tr><td style="padding:4px;">Sub Total</td><td style="text-align:right; padding:4px;">₹ {subtotal:.2f}</td></tr>
              <tr><td style="padding:4px;">CGST @ 0%</td><td style="text-align:right; padding:4px;">₹ {cgst:.2f}</td></tr>
              <tr><td style="padding:4px;">SGST @ 0%</td><td style="text-align:right; padding:4px;">₹ {sgst:.2f}</td></tr>
              <tr><td style="padding:4px;">IGST @ 0%</td><td style="text-align:right; padding:4px;">₹ {igst:.2f}</td></tr>
              <tr><td style="padding:4px;">VAT @ 0%</td><td style="text-align:right; padding:4px;">₹ {vat:.2f}</td></tr>
              <tr><td style="padding:4px;">OTHERS @ 0%</td><td style="text-align:right; padding:4px;">₹ {others:.2f}</td></tr>
              <tr><td style="padding:4px;">Extra Fees</td><td style="text-align:right; padding:4px;">₹ {extra_fees:.2f}</td></tr>
              <tr><td style="padding:4px;">Discount</td><td style="text-align:right; padding:4px;">₹ {discount_total:.2f}</td></tr>
              <tr><td style="padding:6px; font-weight:bold; border-top:1px solid #ccc;">Total</td><td style="text-align:right; padding:6px; font-weight:bold; border-top:1px solid #ccc;">₹ {grand_total:.2f}</td></tr>
            </table>
          </td></tr>
        </table>
        """
        bank_html = f"""
        <div style="border:1px solid #b87333; margin-top:10px;">
          <div style="background:#f3e1cf; padding:6px; font-weight:bold;">Bank Details:</div>
          <div style="padding:8px;">
            <table style="width:100%;">
              <tr><td>Bank Name</td><td>: {ci['bank_name']}</td></tr>
              <tr><td>Holder Name</td><td>: {ci['holder_name']}</td></tr>
              <tr><td>Account Number</td><td>: {ci['account_number']}</td></tr>
              <tr><td>IFSC Code</td><td>: {ci['ifsc']}</td></tr>
            </table>
          </div>
        </div>
        <div style="border:1px solid #b87333; margin-top:10px;">
          <div style="background:#f3e1cf; padding:6px; font-weight:bold;">UPI Payment</div>
          <div style="padding:8px;">
            <table style="width:100%;">
              <tr><td>UPI Payment</td><td>: {payment}</td></tr>
              <tr><td>UPI ID</td><td>: {ci['upi_id']}</td></tr>
            </table>
          </div>
        </div>
        <div style="border:1px solid #b87333; margin-top:10px;">
          <div style="background:#f3e1cf; padding:6px; font-weight:bold;">Terms & Conditions:</div>
          <div style="padding:8px; font-size:12px; color:#555;">Goods once sold will not be taken back. Prices inclusive of applicable taxes unless specified.</div>
        </div>
        <div style="text-align:right; margin-top:18px; font-weight:bold;">Authorise</div>
        <div style="text-align:center; margin-top:18px;">Thank You</div>
        """
        html = f"""
        <div style="font-family:Arial, sans-serif; color:#333;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-size:32px; color:#c0392b; font-weight:bold;">MEDICAL INVOICE</div>
            <div style="text-align:right;">Invoice No : {invoice_no}</div>
          </div>
          <div style="margin-top:6px;">
            <table style="width:100%; font-size:14px;">
              <tr><td>Create Date : {today_str}</td><td>Due Date : {due_str}</td></tr>
            </table>
          </div>
          <div style="display:flex; gap:20px; margin-top:8px;">
            <div style="flex:1;">
              <table style="width:100%; font-size:14px;">
                <tr><td>Company Name</td><td>: {ci['company_name']}</td></tr>
                <tr><td>Address</td><td>: {ci['address']}</td></tr>
                <tr><td>City</td><td>: {ci['city']}</td></tr>
                <tr><td>Postal Code</td><td>: {ci['postal_code']}</td></tr>
                <tr><td>State</td><td>: {ci['state']}</td></tr>
                <tr><td>PAN No</td><td>: {ci['pan']}</td></tr>
                <tr><td>GST</td><td>: {ci['gst']}</td></tr>
                <tr><td>Mobile</td><td>: {ci['mobile']}</td></tr>
                <tr><td>Email</td><td>: {ci['email']}</td></tr>
              </table>
            </div>
            <div style="flex:1;">
              <table style="width:100%; font-size:14px;">
                <tr><td>Client Name</td><td>: {name or '-'}</td></tr>
                <tr><td>Address</td><td>: {c_addr or '-'}</td></tr>
                <tr><td>City</td><td>: {c_city or '-'}</td></tr>
                <tr><td>Postal Code</td><td>: {c_postal or '-'}</td></tr>
                <tr><td>State</td><td>: {c_state or '-'}</td></tr>
                <tr><td>PAN No</td><td>: {c_pan or '-'}</td></tr>
                <tr><td>GST</td><td>: {c_gst or '-'}</td></tr>
                <tr><td>Phone</td><td>: {phone or '-'}</td></tr>
                <tr><td>Email</td><td>: {c_email or '-'}</td></tr>
              </table>
            </div>
          </div>
          <div style="margin-top:12px;">
            <table style="width:100%; border-collapse:collapse;">
              <thead>
                <tr style="background:#f3e1cf;">
                  <th style="border:1px solid #b87333; padding:6px; width:60px;">S No</th>
                  <th style="border:1px solid #b87333; padding:6px;">Product</th>
                  <th style="border:1px solid #b87333; padding:6px; width:100px;">HSN/SAC</th>
                  <th style="border:1px solid #b87333; padding:6px; width:100px;">Rate</th>
                  <th style="border:1px solid #b87333; padding:6px; width:80px;">Qty</th>
                  <th style="border:1px solid #b87333; padding:6px; width:120px;">Amount</th>
                </tr>
              </thead>
              <tbody>
                {rows_html}
              </tbody>
            </table>
          </div>
          {totals_html}
          {bank_html}
        </div>
        """
        # Reset current receipt
        global CURRENT_RECEIPT_ID
        CURRENT_RECEIPT_ID = None
        return jsonify({'status': 'success', 'print_html': html})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Finalize failed: {str(e)}'}), 400

@app.route('/scan_prescription', methods=['POST'])
def scan_prescription():
    try:
        img = None
        file = request.files.get('image')
        if file:
            data = np.frombuffer(file.read(), dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            with lock:
                if current_frame is not None:
                    img = current_frame.copy()
        if img is None:
            return jsonify({'status': 'error', 'message': 'No image to scan'}), 400
        segments = ocr_engine.extract_segments_robust(img)
        print(f"DEBUG: Prescription Scan - Found {len(segments)} segments")
        
        items = []
        all_meds = database.get_all_medicines()
        med_names = [m[1] for m in all_meds]
        seen = set()

        def match_and_add(text):
            cleaned = _normalize_text(text)
            if len(cleaned) < 3:
                return False
            
            # 1. Token set ratio match
            best = process.extractOne(cleaned, med_names, scorer=fuzz.token_set_ratio)
            name = None
            if best and best[1] >= 70:
                name = best[0]
            
            # 2. Word-level fallback
            if not name:
                parts = cleaned.split()
                best_score = 0
                best_word = None
                for w in parts:
                    if len(w) < 4:
                        continue
                    res = process.extractOne(w, med_names, scorer=fuzz.ratio)
                    if res and res[1] > best_score:
                        best_score = res[1]
                        best_word = res[0]
                if best_score >= 85:
                    name = best_word
            
            if name and name not in seen:
                seen.add(name)
                row = next((m for m in all_meds if m[1] == name), None)
                if row:
                    items.append({
                        'name': name,
                        'manufacturer': row[2],
                        'dosage': row[3],
                        'price': row[4],
                        'stock': row[5]
                    })
                    return True
            return False

        # Try segments first
        if segments:
            for seg in segments:
                match_and_add(seg)

        # If few matches, try full text OCR
        if len(items) < 2:
            print("DEBUG: Low matches, trying full text OCR fallback")
            full_text = ocr_engine.extract_text(img)
            if full_text:
                # Split by lines or common delimiters
                parts = re.split(r'[\r\n,]+', full_text)
                for p in parts:
                    match_and_add(p)

        if not items:
            return jsonify({'status': 'warning', 'message': 'No medicines recognized in prescription', 'items': []})
        pres_map = {}
        for it in items:
            pres_map[it['name']] = True
        global CURRENT_PRESCRIPTION
        CURRENT_PRESCRIPTION = pres_map
        return jsonify({'status': 'success', 'items': items})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/detect_strip', methods=['GET'])
def detect_strip():
    try:
        frame = None
        with lock:
            if current_frame is not None:
                frame = current_frame.copy()
        if frame is None:
            return jsonify({'status': 'error', 'message': 'No frame available'}), 400
        _, detections = detector.detect(frame)
        all_meds = database.get_all_medicines()
        med_names = [m[1] for m in all_meds]
        out = []
        for det in detections:
            crop = det['crop']
            segs = ocr_engine.extract_segments_fast(crop) or ocr_engine.extract_segments_multiangle(crop)
            matched = None
            for t in segs:
                cleaned = _normalize_text(t)
                if len(cleaned) < 3:
                    continue
                best = process.extractOne(cleaned, med_names, scorer=fuzz.token_set_ratio)
                if best and best[1] >= 70:
                    matched = best[0]
                    break
            if not matched:
                continue
            row = next((m for m in all_meds if m[1] == matched), None)
            if not row:
                continue
            out.append({
                'medicine': matched,
                'manufacturer': row[2],
                'dosage': row[3],
                'price': row[4],
                'stock': row[5]
            })
        if not out:
            return jsonify({'status': 'warning', 'message': 'No strip recognized'})
        return jsonify({'status': 'success', 'matches': out})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/medicines', methods=['GET'])
def medicines_list():
    rows = database.get_all_medicines()
    out = []
    for r in rows:
        out.append({
            'id': r[0],
            'name': r[1],
            'manufacturer': r[2],
            'dosage': r[3],
            'price': r[4],
            'stock': r[5],
            'discount': float(r[6] if len(r) > 6 and r[6] is not None else 0.0),
            'mfg_date': r[7] if len(r) > 7 else None,
            'exp_date': r[8] if len(r) > 8 else None
        })
    return jsonify(out)

@app.route('/medicine_add', methods=['POST'])
def medicine_add():
    data = request.get_json(silent=True) or {}
    name = data.get('name') or request.form.get('name')
    if not name:
        return jsonify({'status': 'error', 'message': 'Name required'}), 400
    manufacturer = data.get('manufacturer') or request.form.get('manufacturer') or 'Unknown'
    dosage = data.get('dosage') or request.form.get('dosage') or ''
    try:
        price = float(data.get('price') or request.form.get('price') or 0)
    except Exception:
        price = 0.0
    try:
        stock = int(data.get('stock') or request.form.get('stock') or 0)
    except Exception:
        stock = 0
    try:
        discount = float(data.get('discount') or request.form.get('discount') or 0.0)
    except Exception:
        discount = 0.0
    mfg_date = data.get('mfg_date') or request.form.get('mfg_date')
    exp_date = data.get('exp_date') or request.form.get('exp_date')
    row = database.upsert_medicine(name, manufacturer, dosage, price, stock, discount, mfg_date, exp_date)
    return jsonify({'status': 'success'})

@app.route('/medicine_delete', methods=['POST'])
def medicine_delete():
    data = request.get_json(silent=True) or {}
    mid = data.get('id') or request.form.get('id')
    name = data.get('name') or request.form.get('name')
    if mid:
        try:
            mid = int(mid)
        except Exception:
            mid = None
    ok = database.delete_medicine(medicine_id=mid, name=name)
    if ok:
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Medicine not found'}), 404

@app.route('/medicine_info', methods=['GET'])
def get_medicine_info():
    name = request.args.get('name')
    if not name:
        return jsonify({'status': 'error', 'message': 'Medicine name is required'})
    
    query = f"when and why to use {name} tablet"
    try:
        search_url = f"https://www.google.com/search?q={name.replace(' ', '+')}+tablet+when+and+why+to+use"
        return jsonify({
            'status': 'success',
            'name': name,
            'search_query': search_url
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    # Use environment variable for port if available (for Render)
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
