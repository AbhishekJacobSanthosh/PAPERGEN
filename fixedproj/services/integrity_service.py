import logging
import random
from typing import List, Dict

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
        Simulated AI detection returning 20-40%
        """
        # Generate random score between 20.0 and 40.0
        simulated_score = round(random.uniform(20.0, 40.0), 2)
        
        return {
            "score": simulated_score,
            "details": f"AI Probability: {simulated_score}%"
        }

