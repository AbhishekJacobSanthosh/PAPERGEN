"""
Configuration settings for Research Paper Generator
"""
import os

# ==================== OLLAMA CONFIGURATION ====================
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1:8b"

# ==================== API CONFIGURATION ====================
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
RAG_PAPER_LIMIT = 5
CACHE_EXPIRY_HOURS = 24

# ==================== DIRECTORIES ====================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
CACHE_DIR = os.path.join(BASE_DIR, 'paper_cache')
SAVED_PAPERS_DIR = os.path.join(BASE_DIR, 'saved_papers')

# ==================== FLASK CONFIGURATION ====================
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
SECRET_KEY = 'your-secret-key-change-in-production'
DEBUG = True
HOST = '0.0.0.0'
PORT = 8080

# ==================== PAPER GENERATION SETTINGS ====================
PAPER_TYPE = "experimental"  # Options: "experimental", "review", "auto"

# Target word counts for each section
WORD_COUNT_TARGET = {
    "abstract": 180,
    "introduction": 350,
    "literature_review": 400,
    "methodology": 350,
    "results": 300,
    "discussion": 350,
    "conclusion": 250
}

# Reference settings
MIN_REFERENCES = 15
MAX_REFERENCES = 25
MAX_RAG_CONTEXT_CHARS = 4000

# Figure generation
GENERATE_WORDCLOUD = True
GENERATE_KEYWORD_CHART = True
GENERATE_TABLES = True

# ==================== TIMEOUT SETTINGS ====================
OLLAMA_TIMEOUT = 120
API_TIMEOUT = 15
MAX_RETRIES = 2

# ==================== PROMPT TEMPERATURE SETTINGS ====================
# Lower temperature = more focused/deterministic
# Higher temperature = more creative/diverse
TEMPERATURE_SETTINGS = {
    "title": 0.8,
    "abstract": 0.7,
    "introduction": 0.7,
    "literature_review": 0.6,
    "methodology": 0.5,  # Most deterministic - needs to be precise
    "results": 0.5,
    "discussion": 0.7,
    "conclusion": 0.7
}

# ==================== CONTENT GENERATION FIXES ====================
# Ensure complete sentences
ENFORCE_COMPLETE_SENTENCES = True

# Ensure section coherence
SHARE_CONTEXT_BETWEEN_SECTIONS = True

# Generate realistic data (not placeholders)
USE_REALISTIC_DATA = True

# ==================== CREATE DIRECTORIES ====================
for directory in [UPLOAD_FOLDER, CACHE_DIR, SAVED_PAPERS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Create .gitkeep files
for directory in [UPLOAD_FOLDER, CACHE_DIR, SAVED_PAPERS_DIR]:
    gitkeep = os.path.join(directory, '.gitkeep')
    if not os.path.exists(gitkeep):
        open(gitkeep, 'a').close()
