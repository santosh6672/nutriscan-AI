import cv2
import numpy as np
import torch
from pyzbar import pyzbar
import base64
import sys, os
import easyocr # <-- Added import
import re      # <-- Added import for cleaning OCR results

# --- Model and OCR Initialization ---
# This section should run only once when your application starts for best performance.

try:
    # Initialize YOLOv5 Model
    DEVICE = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    MODEL = torch.hub.load(
        'ultralytics/yolov5',
        'custom',
        path=r'C:\Users\kuruv\Desktop\new nutriscan\nutriscan_ai\nutrition_analysis\services\model.pt', # Ensure this path is correct
        _verbose=False
    ).to(DEVICE)
    MODEL.conf = 0.5
except Exception as e:
    MODEL = None
    print(f"Error loading YOLOv5 model: {e}", file=sys.stderr)

try:
    # Initialize EasyOCR Reader
    # This will download the required models on its first run.
    OCR_READER = easyocr.Reader(['en'])
except Exception as e:
    OCR_READER = None
    print(f"Error loading EasyOCR model: {e}", file=sys.stderr)


# --- Helper Functions ---

def preprocess_for_barcode(img):
    """Applies preprocessing to improve barcode decoding."""
    if len(img.shape) > 2 and img.shape[2] == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    gray = cv2.equalizeHist(gray)
    enlarged = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    blurred = cv2.GaussianBlur(enlarged, (3, 3), 0)
    sharpened = cv2.addWeighted(enlarged, 1.5, blurred, -0.5, 0)
    return sharpened

def safe_decode(img):
    """Safely decodes barcodes with pyzbar."""
    if img is None or img.size == 0:
        return []
    try:
        return pyzbar.decode(img)
    except Exception:
        return []

def get_numbers_from_ocr(image_crop, reader):
    """Uses EasyOCR to extract and clean numbers from an image crop."""
    if reader is None or image_crop is None or image_crop.size == 0:
        return None
    
    try:
        results = reader.readtext(image_crop)
        full_text = "".join([res[1] for res in results])
        numbers = re.findall(r'\d', full_text)
        if numbers:
            return "".join(numbers)
    except Exception:
        return None
    return None

def draw_barcode_boxes(image, detections):
    """Draws bounding boxes and labels on the image."""
    image_with_boxes = image.copy()
    for _, detection in detections.iterrows():
        x1, y1, x2, y2 = map(int, [detection['xmin'], detection['ymin'], detection['xmax'], detection['ymax']])
        cv2.rectangle(image_with_boxes, (x1, y1), (x2, y2), (0, 0, 255), 2)
        label = f"Barcode: {detection['confidence']:.2f}"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        cv2.rectangle(image_with_boxes, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), (0, 0, 255), -1)
        cv2.putText(image_with_boxes, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return image_with_boxes

def image_to_base64(image):
    """Converts an OpenCV image to a base64 string."""
    _, buffer = cv2.imencode('.jpg', image)
    return base64.b64encode(buffer).decode('utf-8')


# --- Main Service Function ---

def scan_barcode_with_display(input_file, debug=False):
    """
    Scans a barcode using YOLOv5, decodes with Pyzbar, and falls back to EasyOCR.
    """
    if MODEL is None:
        return {"success": False, "message": "YOLOv5 model is not loaded."}
    if OCR_READER is None:
        return {"success": False, "message": "EasyOCR model is not loaded."}

    # 1. Load image (Unchanged)
    image = None
    try:
        if hasattr(input_file, 'read'):
            file_bytes = np.frombuffer(input_file.read(), np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if hasattr(input_file, 'seek'):
                input_file.seek(0)
        elif isinstance(input_file, str):
            image = cv2.imread(input_file)
        else:
            return {"success": False, "message": f"Invalid input type: {type(input_file)}"}
    except Exception as e:
        return {"success": False, "message": f"Could not read or decode the image file: {e}"}

    if image is None:
        return {"success": False, "message": "Image could not be loaded."}

    # 2. Detect with YOLOv5 (Unchanged)
    results = MODEL(image)
    detections = results.pandas().xyxy[0]

    if detections.empty:
        image_base64 = image_to_base64(image)
        return {
            "success": False, "message": "No barcode detected in the image.",
            "image_with_boxes": image_base64, "barcode_data": None, "detection_count": 0
        }

    # 3. Draw bounding boxes (Unchanged)
    image_with_boxes = draw_barcode_boxes(image, detections)
    image_base64 = image_to_base64(image_with_boxes)

    # 4. Try decoding each detection with Pyzbar, then OCR
    barcode_data = None
    for _, detection in detections.iterrows():
        x1, y1, x2, y2 = map(int, [detection['xmin'], detection['ymin'], detection['xmax'], detection['ymax']])
        pad = 10
        x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
        x2, y2 = min(image.shape[1], x2 + pad), min(image.shape[0], y2 + pad)
        cropped_img = image[y1:y2, x1:x2]
        
        # Attempt 1: Decode with Pyzbar
        processed = preprocess_for_barcode(cropped_img)
        barcodes = safe_decode(processed)
        if not barcodes:
            barcodes = safe_decode(cropped_img) # Fallback to raw crop

        if barcodes:
            barcode_data = barcodes[0].data.decode('utf-8')
            break  # Success! Exit loop.

        # **NEW: Attempt 2: Fallback to OCR if Pyzbar fails**
        if not barcode_data:
            ocr_result = get_numbers_from_ocr(cropped_img, OCR_READER)
            # Basic sanity check: most barcodes have 8+ digits
            if ocr_result and len(ocr_result) >= 8:
                barcode_data = ocr_result
                break # Success! Exit loop.

    # 5. Fallback to whole image (Kept as a final measure)
    if not barcode_data:
        barcodes = safe_decode(preprocess_for_barcode(image))
        if barcodes:
            barcode_data = barcodes[0].data.decode('utf-8')

    # 6. Return final result
    if barcode_data:
        return {
            "success": True, "message": f"Barcode successfully processed: {barcode_data}",
            "image_with_boxes": image_base64, "barcode_data": barcode_data, "detection_count": len(detections)
        }
    else:
        return {
            "success": False, "message": "Barcode detected but could not be read. Try a clearer image.",
            "image_with_boxes": image_base64, "barcode_data": None, "detection_count": len(detections)
        }

# Keep original function for backward compatibility
def scan_barcode(input_file, debug=False):
    return scan_barcode_with_display(input_file, debug)