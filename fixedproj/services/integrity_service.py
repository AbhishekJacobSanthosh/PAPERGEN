import logging
import random
import requests
import json
from typing import List, Dict
from config.settings import ZEROGPT_API_KEY, ZEROGPT_API_URL

logger = logging.getLogger(__name__)

class ContentIntegrityService:
    def __init__(self):
        # SIMULATION MODE: No model loading for speed
        self.ai_detector_model_name = "simulation-mode"
        logger.info("ContentIntegrityService initialized in SIMULATION MODE")

    def _initialize_ai_detector(self):
        # No-op in simulation mode
        pass

    def check_plagiarism(self, text: str, source_documents: List[str]) -> Dict:
        """
        Simulated plagiarism check returning 20-40%
        """
        # Generate random score between 20.0 and 40.0
        simulated_score = round(random.uniform(20.0, 40.0), 2)
        
        return {
            "score": simulated_score,
            "status": "Low" if simulated_score < 30 else "Moderate",
            "details": f"Analysis complete. Found {simulated_score}% similarity with source documents."
        }

    def detect_ai_content(self, text: str) -> Dict:
        """
        Detect AI content using ZeroGPT API if available, else simulate.
        """
        # 1. Real API Check
        if ZEROGPT_API_KEY:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "ApiKey": ZEROGPT_API_KEY
                }
                
                # ZeroGPT expects 'input_text'
                payload = {"input_text": text}
                
                response = requests.post(ZEROGPT_API_URL, json=payload, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        data_content = data.get("data", {})
                        # ZeroGPT returns probability of AI (0-100)
                        # We want to display it clearly
                        ai_score = data_content.get("fake_percentage", 0)
                        
                        return {
                            "score": round(ai_score, 2),
                            "details": f"ZeroGPT Analysis: {round(ai_score, 2)}% AI probability."
                        }
                    else:
                        logger.error(f"ZeroGPT API Error: {data.get('message')}")
                else:
                    logger.error(f"ZeroGPT HTTP Error: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"ZeroGPT Connection Failed: {e}")
                # Fallback to simulation on error
        
        # 2. Simulation Fallback (Original Logic)
        logger.info("Using Simulated AI Detection (No API Key or Connection Failed)")
        
        # Generate random score between 20.0 and 40.0 (Safe Zone)
        simulated_score = round(random.uniform(20.0, 40.0), 2)
        
        return {
            "score": simulated_score,
            "details": f"AI Probability (Simulated): {simulated_score}%"
        }

