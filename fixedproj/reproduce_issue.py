import sys
import os
import logging

# Add project root to path
sys.path.append('/home/cselab3/Documents/ms22cs006/PAPERGEN/fixedproj')

# Mock missing dependencies
from unittest.mock import MagicMock
sys.modules['wordcloud'] = MagicMock()
sys.modules['easyocr'] = MagicMock()

from services.rag_service import RAGService
from services.paper_generator import PaperGeneratorService
from models.paper_structure import Reference

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_rag_retrieval():
    print("\n=== Testing RAG Retrieval ===")
    rag = RAGService()
    query = "Investigating the Efficacy of Predictive Analytics in Preventing Chronic Diseases"
    limit = 10
    
    print(f"Searching for '{query}' with limit {limit}...")
    papers = rag.search_papers(query, limit)
    
    print(f"Retrieved {len(papers)} papers.")
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper.title} (Abstract len: {len(paper.abstract)})")
        
    if len(papers) < limit:
        print(f"FAIL: Retrieved fewer papers ({len(papers)}) than limit ({limit}).")
    else:
        print("PASS: Retrieved expected number of papers.")

def test_reference_generation():
    print("\n=== Testing Reference Generation ===")
    generator = PaperGeneratorService()
    
    # Test case 1: No retrieved papers
    print("Test Case 1: No retrieved papers")
    retrieved_papers = []
    title = "Advanced Deep Learning Methods"
    
    refs = generator._generate_references(retrieved_papers, title)
    print(f"Generated {len(refs)} references.")
    if len(refs) >= 15:
        print("PASS: Generated enough references.")
    else:
        print(f"FAIL: Generated only {len(refs)} references (expected >= 15).")
        
    # Test case 2: Some retrieved papers
    print("\nTest Case 2: 2 retrieved papers")
    retrieved_papers = [
        Reference(title="Paper 1", authors=["A. Author"], year=2023, venue="Conf 1", citation_count=10),
        Reference(title="Paper 2", authors=["B. Author"], year=2022, venue="Conf 2", citation_count=20)
    ]
    
    refs = generator._generate_references(retrieved_papers, title)
    print(f"Generated {len(refs)} references.")
    if len(refs) >= 15:
        print("PASS: Generated enough references.")
    else:
        print(f"FAIL: Generated only {len(refs)} references (expected >= 15).")

if __name__ == "__main__":
    test_rag_retrieval()
    test_reference_generation()
