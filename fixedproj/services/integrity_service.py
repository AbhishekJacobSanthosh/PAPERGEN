import logging
import torch
from typing import List, Dict, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np

logger = logging.getLogger(__name__)

class ContentIntegrityService:
    def __init__(self):
        self.ai_detector_model_name = "roberta-base-openai-detector"
        self.tokenizer = None
        self.model = None
        self._initialize_ai_detector()

    def _initialize_ai_detector(self):
        """Initialize the AI detection model (lazy loading)"""
        try:
            logger.info("Loading AI detection model...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.ai_detector_model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.ai_detector_model_name)
            self.model.eval()
            logger.info("AI detection model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load AI detection model: {e}")

    def check_plagiarism(self, text: str, source_documents: List[str]) -> Dict:
        """
        Check for plagiarism against source documents using TF-IDF and Cosine Similarity.
        
        Args:
            text: The generated text to check.
            source_documents: List of source texts (e.g., abstracts of retrieved papers).
            
        Returns:
            Dictionary containing max similarity score and details.
        """
        if not text or not source_documents:
            return {"score": 0.0, "details": "No text or sources to check against."}

        try:
            # Combine text and sources
            documents = [text] + source_documents
            
            # TF-IDF Vectorization
            tfidf_vectorizer = TfidfVectorizer().fit_transform(documents)
            
            # Calculate cosine similarity
            cosine_similarities = cosine_similarity(tfidf_vectorizer[0:1], tfidf_vectorizer[1:]).flatten()
            
            # Find max similarity
            max_similarity = float(np.max(cosine_similarities)) if len(cosine_similarities) > 0 else 0.0
            
            # Interpret score
            status = "Low"
            if max_similarity > 0.7:
                status = "High"
            elif max_similarity > 0.4:
                status = "Moderate"
                
            return {
                "score": round(max_similarity * 100, 2),
                "status": status,
                "details": f"Highest similarity found: {round(max_similarity * 100, 2)}% with a source document."
            }
        except Exception as e:
            logger.error(f"Plagiarism check failed: {e}")
            return {"score": 0.0, "details": f"Error: {str(e)}"}

    def detect_ai_content(self, text: str) -> Dict:
        """
        Detect likelihood of text being AI-generated.
        
        Args:
            text: The text to analyze.
            
        Returns:
            Dictionary containing AI probability score.
        """
        if not self.model or not self.tokenizer:
            return {"score": 0.0, "details": "AI detection model not loaded."}
            
        try:
            # Truncate text to fit model max length (usually 512)
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
                
            # Assuming label 1 is "Fake" (AI-generated) and 0 is "Real"
            # Verify specific model labels, but commonly 1 = AI
            ai_probability = float(probs[0][1].item())
            
            return {
                "score": round(ai_probability * 100, 2),
                "details": f"AI Probability: {round(ai_probability * 100, 2)}%"
            }
        except Exception as e:
            logger.error(f"AI detection failed: {e}")
            return {"score": 0.0, "details": f"Error: {str(e)}"}
