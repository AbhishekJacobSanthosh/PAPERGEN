import sys
import os
import logging
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

# Mock dependencies to avoid full environment setup
sys.modules['wordcloud'] = MagicMock()
sys.modules['easyocr'] = MagicMock()

from services.paper_generator import PaperGeneratorService
from models.paper_structure import Author

# Mock LLM to avoid real calls and speed up test
class MockLLM:
    def generate_title(self, desc):
        return "Test Title"
    
    def generate_abstract(self, title, context):
        return "This is a test abstract."
    
    def generate_section(self, section_name, **kwargs):
        import time
        time.sleep(1) # Simulate work
        return f"Content for {section_name}"

def test_parallel_generation():
    logging.basicConfig(level=logging.INFO)
    
    generator = PaperGeneratorService()
    generator.llm = MockLLM() # Inject mock
    generator.rag = MagicMock()
    generator.rag.search_papers.return_value = []
    
    print("Starting generation...")
    import time
    start = time.time()
    
    paper = generator.generate_paper(
        topic="Test Topic",
        authors=[Author(name="Test Author", email="test@test.com", affiliation="Test Univ")],
        use_rag=False
    )
    
    end = time.time()
    duration = end - start
    
    print(f"Generation took {duration:.2f} seconds")
    print(f"Sections generated: {list(paper.sections.keys())}")
    
    # Expected: Intro (1s) + Parallel (1s for max(others)) = ~2s total (plus overhead)
    # Sequential would be 1+1+1+1+1+1 = 6s
    if duration < 4:
        print("PASS: Parallel execution confirmed (fast execution)")
    else:
        print("FAIL: Execution too slow, likely sequential")

if __name__ == "__main__":
    test_parallel_generation()
