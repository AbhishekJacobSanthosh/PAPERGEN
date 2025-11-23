"""
OCR Service - Extract text from images
"""
from PIL import Image, ImageEnhance
import easyocr
from typing import Optional

class OCRService:
    """Service for OCR text extraction"""
    
    def __init__(self):
        print("[OCR] Loading EasyOCR model...")
        self.reader = easyocr.Reader(['en'], gpu=False)
        print("[OCR] Model loaded!")
    
    def extract_text(self, image_path: str) -> str:
        """Extract text from image file"""
        try:
            # Load and preprocess image
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)
            
            # Extract text
            results = self.reader.readtext(image_path, detail=0, paragraph=False)
            text = ' '.join(results).strip()
            
            return text if text else "No text detected"
            
        except Exception as e:
            return f"OCR Error: {str(e)}"
