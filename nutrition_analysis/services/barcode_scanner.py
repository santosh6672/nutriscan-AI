import cv2
import numpy as np
import torch
from pyzbar import pyzbar
import base64
import os
import logging
from typing import Dict, Any, Optional, Union, List
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Model Initialization ---
MODEL = None
DEVICE = None

def initialize_models():
    """Initialize YOLOv5 model only (no OCR)."""
    global MODEL, DEVICE
    try:
        DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {DEVICE}")

        model_path = r'nutrition_analysis\services\model.pt'
        if not os.path.exists(model_path):
            current_dir = Path(__file__).parent
            model_path = current_dir / "model.pt"
            if not model_path.exists():
                logger.error(f"Model file not found at {model_path}")
                return False

        MODEL = torch.hub.load(
            'ultralytics/yolov5',
            'custom',
            path=str(model_path),
            force_reload=False,
            trust_repo=True,
            _verbose=False
        ).to(DEVICE)

        MODEL.conf = 0.5
        MODEL.iou = 0.45
        logger.info("YOLOv5 model loaded successfully")

        return True

    except Exception as e:
        logger.error(f"Error loading YOLOv5 model: {e}")
        MODEL = None
        return False


# --- Utility Functions ---

def preprocess_for_barcode(img: np.ndarray) -> np.ndarray:
    """Simple preprocessing for better barcode detection."""
    if img is None or img.size == 0:
        return img
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh
    except Exception as e:
        logger.warning(f"Preprocessing failed: {e}")
        return img


def safe_decode(img: np.ndarray) -> List[Any]:
    """Safely decodes barcodes with pyzbar."""
    if img is None or img.size == 0:
        return []
    try:
        decoded = pyzbar.decode(img)
        return decoded
    except Exception as e:
        logger.debug(f"Pyzbar decoding failed: {e}")
        return []


def image_to_base64(image: np.ndarray) -> str:
    """Convert OpenCV image to base64 string."""
    try:
        _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        logger.error(f"Base64 conversion failed: {e}")
        return ""


def load_image(input_file: Union[str, bytes, object]) -> Optional[np.ndarray]:
    """Load image from various input formats."""
    try:
        if hasattr(input_file, 'read'):
            file_bytes = np.frombuffer(input_file.read(), np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if hasattr(input_file, 'seek'):
                input_file.seek(0)
            return image
        elif isinstance(input_file, (str, Path)):
            if not os.path.exists(input_file):
                logger.error(f"Image file not found: {input_file}")
                return None
            return cv2.imread(str(input_file))
        elif isinstance(input_file, bytes):
            file_bytes = np.frombuffer(input_file, np.uint8)
            return cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        else:
            logger.error(f"Unsupported input type: {type(input_file)}")
            return None
    except Exception as e:
        logger.error(f"Image loading failed: {e}")
        return None


def draw_barcode_boxes(image: np.ndarray, detections) -> np.ndarray:
    """Draw bounding boxes on detected barcode regions."""
    image_with_boxes = image.copy()
    for _, detection in detections.iterrows():
        try:
            x1, y1, x2, y2 = map(int, [detection['xmin'], detection['ymin'], detection['xmax'], detection['ymax']])
            conf = detection['confidence']
            cv2.rectangle(image_with_boxes, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"Barcode {conf:.2f}"
            cv2.putText(image_with_boxes, label, (x1, max(y1 - 10, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        except Exception as e:
            logger.warning(f"Error drawing box: {e}")
            continue
    return image_with_boxes


# --- Main Pipeline ---

def scan_barcode_with_display(input_file, debug=False) -> Dict[str, Any]:
    """
    Barcode scanning pipeline:
    1. Try direct Pyzbar decoding
    2. If fails, use YOLO + OpenCV BarcodeDetector
    3. Return base64 image with drawn boxes
    """
    global MODEL

    if MODEL is None:
        if not initialize_models():
            return {"success": False, "message": "Model initialization failed", "image_with_boxes": "", "barcode_data": None, "detection_count": 0}

    image = load_image(input_file)
    if image is None:
        return {"success": False, "message": "Failed to load image", "image_with_boxes": "", "barcode_data": None, "detection_count": 0}

    original_image = image.copy()
    barcode_data = None
    detection_count = 0
    image_with_boxes = original_image.copy()

    try:
        # Step 1: Direct Pyzbar decoding
        logger.info("Attempting direct barcode decoding...")
        direct_barcodes = safe_decode(image)

        if direct_barcodes:
            barcode_data = direct_barcodes[0].data.decode('utf-8')
            detection_count = len(direct_barcodes)
            logger.info(f"Direct decoding successful: {barcode_data}")

            for barcode in direct_barcodes:
                x, y, w, h = barcode.rect
                cv2.rectangle(image_with_boxes, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(image_with_boxes, "Direct", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Step 2: YOLO + OpenCV Barcode Detector
        if not barcode_data:
            logger.info("Direct decoding failed, using YOLO + BarcodeDetector...")
            with torch.no_grad():
                results = MODEL(image)

            detections = results.pandas().xyxy[0]
            detection_count = len(detections)

            detector = cv2.barcode_BarcodeDetector()

            for _, det in detections.iterrows():
                try:
                    x1, y1, x2, y2 = map(int, [det['xmin'], det['ymin'], det['xmax'], det['ymax']])
                    crop = image[y1:y2, x1:x2]
                    if crop.size == 0:
                        continue

                    pre = preprocess_for_barcode(crop)
                    try:
                        detector = cv2.barcode_BarcodeDetector()
                        result = detector.detectAndDecode(preprocessed_region)
                        if len(result) == 4:
                            ok, decoded_info, points, _ = result
                        elif len(result) == 3:
                             ok, decoded_info, points = result
                        else:
                             ok, decoded_info, points = False, None, None
                    except Exception:
                        ok, decoded_info, points = False, None, None

                    if ok and decoded_info:
                        barcode_data = decoded_info[0] if isinstance(decoded_info, list) else decoded_info
                        logger.info(f"YOLO+BarcodeDetector successful: {barcode_data}")
                        break
                    
                except Exception as e:
                    logger.warning(f"Error in YOLO region decoding: {e}")
                    continue

            if not barcode_data:
                image_with_boxes = draw_barcode_boxes(original_image, detections)

        # Step 3: Encode image to base64
        image_base64 = image_to_base64(image_with_boxes)

        # Step 4: Return result
        if barcode_data:
            return {
                "success": True,
                "message": "Barcode successfully decoded",
                "image_with_boxes": image_base64,
                "barcode_data": barcode_data,
                "detection_count": detection_count
            }
        else:
            return {
                "success": False,
                "message": "No barcode decoded",
                "image_with_boxes": image_base64,
                "barcode_data": None,
                "detection_count": detection_count
            }

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        image_base64 = image_to_base64(original_image)
        return {
            "success": False,
            "message": f"Processing error: {str(e)}",
            "image_with_boxes": image_base64,
            "barcode_data": None,
            "detection_count": 0
        }
