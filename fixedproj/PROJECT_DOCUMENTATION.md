# AI Research Paper Generator - Complete Technical Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Core Components](#core-components)
6. [Configuration](#configuration)
7. [API Endpoints](#api-endpoints)
8. [Workflow & Data Flow](#workflow--data-flow)
9. [Key Algorithms](#key-algorithms)
10. [Export Formats](#export-formats)
11. [Quality Evaluation](#quality-evaluation)
12. [Troubleshooting](#troubleshooting)

---

## Project Overview

The **AI Research Paper Generator** is a Flask-based web application that automatically generates IEEE-formatted academic research papers using:
- **Large Language Model (LLM)**: Ollama with Llama 3.1 8B for text generation
- **RAG (Retrieval-Augmented Generation)**: Semantic Scholar API for real research paper citations
- **Multi-format Export**: HTML, DOCX, PPTX output formats
- **Quality Evaluation**: BLEU and ROUGE score metrics

### What It Does
1. User inputs a research topic/description
2. System searches Semantic Scholar for relevant papers (RAG)
3. LLM generates each section (Abstract, Introduction, Literature Review, Methodology, Results, Discussion, Conclusion)
4. Paper is formatted in IEEE style with proper citations
5. User can download in multiple formats

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Web UI)                         │
│  templates/index.html + static/js/paper-generation.js + CSS     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK APPLICATION (app.py)                  │
│  Routes: /api/generate, /api/download-html, /api/evaluate, etc. │
└─────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
         ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
         │ Paper        │ │ RAG          │ │ Export       │
         │ Generator    │ │ Service      │ │ Service      │
         │ Service      │ │              │ │              │
         └──────────────┘ └──────────────┘ └──────────────┘
                │                │                │
                ▼                ▼                ▼
         ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
         │ LLM          │ │ Semantic     │ │ ReportLab    │
         │ Interface    │ │ Scholar API  │ │ python-docx  │
         │ (Ollama)     │ │              │ │              │
         └──────────────┘ └──────────────┘ └──────────────┘
```

---

## Technology Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Flask | 3.0.0 | Web framework |
| Python | 3.10+ | Runtime |
| Ollama | Latest | Local LLM inference |
| Llama 3.1 8B | - | Language model |

### Frontend
| Technology | Purpose |
|------------|---------|
| HTML5 | Structure |
| CSS3 | Styling (custom design system) |
| JavaScript | Interactivity, API calls |

### External APIs
| API | Purpose |
|-----|---------|
| Semantic Scholar | Research paper retrieval |
| Ollama REST API | LLM text generation |

### Libraries
| Library | Purpose |
|---------|---------|
| requests | HTTP client |
| reportlab | PDF generation |
| python-docx | DOCX generation |
| python-pptx | PowerPoint generation |
| easyocr | OCR for image text extraction |
| nltk | Text processing, tokenization |
| rouge-score | ROUGE evaluation metrics |
| scikit-learn | ML utilities |
| matplotlib/seaborn | Figure generation |
| wordcloud | Word cloud visualization |

---

## Project Structure

```
fixedproj/
├── app.py                      # Main Flask application (40KB)
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
├── .gitignore                  # Git ignore rules
│
├── config/
│   ├── __init__.py
│   └── settings.py             # All configuration constants
│
├── models/
│   ├── __init__.py
│   ├── llm.py                  # LLM interface & prompts (36KB)
│   └── paper_structure.py      # Data classes for paper structure
│
├── services/
│   ├── __init__.py
│   ├── paper_generator.py      # Main paper generation orchestrator
│   ├── rag_service.py          # Semantic Scholar integration
│   ├── export_service.py       # PDF/DOCX/HTML export
│   ├── evaluation_service.py   # BLEU/ROUGE scoring
│   ├── integrity_service.py    # AI detection simulation
│   ├── figure_generator.py     # Chart/graph generation
│   ├── presentation_generator.py # PPTX generation
│   └── ocr_service.py          # Image text extraction
│
├── utils/
│   ├── __init__.py
│   ├── cache_manager.py        # RAG cache management
│   └── text_processing.py      # Text utilities
│
├── static/
│   ├── css/style.css           # Main stylesheet
│   └── js/paper-generation.js  # Frontend JavaScript
│
├── templates/
│   └── index.html              # Main HTML template
│
├── paper_cache/                # Cached Semantic Scholar results
├── saved_papers/               # Auto-saved generated papers
└── uploads/                    # User uploaded files
```

---

## Core Components

### 1. Main Application (`app.py`)

The Flask application entry point containing:

**Routes:**
- `GET /` - Serve main page
- `POST /api/generate` - Generate research paper
- `POST /api/generate-stream` - SSE streaming generation
- `POST /api/generate-titles` - Generate title options
- `POST /api/warmup` - Warmup LLM model
- `GET /api/latest-paper` - Get most recent paper
- `GET /api/list-papers` - List all saved papers
- `POST /api/recover-paper` - Recover specific paper
- `POST /api/download-html` - Export as HTML
- `POST /api/download-docx` - Export as DOCX
- `POST /api/download-pptx` - Export as PPTX
- `POST /api/retrieve-papers` - Search Semantic Scholar
- `POST /api/generate-survey` - Generate literature survey
- `POST /api/evaluate-paper` - Evaluate paper quality
- `POST /api/extract-ocr` - Extract text from images

**Key Features:**
- Input validation with `RequestValidator` class
- Error handling decorator `@handle_api_errors`
- Auto-save papers to `saved_papers/` directory
- UTF-8 encoding fixes for Windows console

---

### 2. LLM Interface (`models/llm.py`)

The core text generation engine with 36KB of carefully crafted prompts.

**Class: `LLMInterface`**

**Key Methods:**

```python
warmup()                    # Pre-load model for faster first response
generate(prompt, ...)       # Core generation with retry logic
generate_title(description) # Generate paper title
generate_title_options(...) # Generate multiple title choices
generate_abstract(title)    # Generate 200-250 word abstract
generate_section(...)       # Generate any paper section
humanize_text(text, ...)    # Make text more human-like
```

**"Write Drunk, Edit Sober" Strategy:**

The system uses a two-pass generation approach:
1. **Pass 1 (Casual Draft)**: Generate content with high creativity (temp=0.85)
2. **Pass 2 (Formal Edit)**: Rewrite in academic style (temp=0.6)

```python
# Step 1: Casual draft (high creativity)
casual_draft = self.generate(prompt, temperature=0.85, ...)

# Step 2: Formalize
formal_version = self.generate(formalization_prompt, temperature=0.6, ...)

# Step 3: Clean banned words
final_clean = self._force_remove_banned_words(formal_version)

# Step 4: Format structured content
formatted = self._format_structured_content(final_clean)
```

**Post-Processing (`_format_structured_content`):**

Fixes common LLM output issues:
- Character encoding: `â€¢` → `•`, `Â²` → `²`, `Ã©` → `é`
- Remove triple backticks (```)
- Insert line breaks before: subsections (A., B., C.), bullets (•), numbered lists (1., 2.)
- Insert line breaks before labels: "Key Insight:", "Objectives:", etc.
- Remove dashes (----) and markdown bold (**)

**Section Prompts:**

Each section has a specialized prompt:
- `_prompt_introduction()` - Background, problem, objectives
- `_prompt_literature_review()` - Critical analysis of related work
- `_prompt_methodology()` - A. Problem, B. Algorithm, C. Implementation, D. Protocol
- `_prompt_results()` - A. Findings, B. Comparison, C. Analysis, D. State-of-art
- `_prompt_discussion()` - A. Interpretation, B. Literature compare, C. Limitations, D. Future
- `_prompt_conclusion()` - Summary, contributions, implications

---

### 3. Paper Structure (`models/paper_structure.py`)

Data classes defining the paper structure:

```python
@dataclass
class Author:
    name: str
    affiliation: str
    email: str

@dataclass
class Reference:
    title: str
    authors: List[str]
    year: int
    venue: str
    doi: Optional[str]
    url: Optional[str]
    citation_count: int
    abstract: str

@dataclass
class Figure:
    caption: str
    data: str  # Base64 encoded image

@dataclass
class ResearchPaper:
    title: str
    authors: List[Author]
    abstract: str
    sections: Dict[str, str]  # introduction, methodology, etc.
    references: List[Reference]
    figures: Dict[str, Figure]
    doi: str
    generated_at: datetime
    metadata: Dict[str, Any]  # word counts, generation time, etc.
```

---

### 4. Paper Generator Service (`services/paper_generator.py`)

Orchestrates the entire paper generation process.

**Class: `PaperGeneratorService`**

**Main Method: `generate_paper(topic, authors, use_rag, user_data, title)`**

**Workflow:**
1. Search for papers via RAG service (if enabled)
2. Build context from retrieved papers
3. Generate title (if not provided)
4. Generate abstract
5. Generate each section in order
6. Compile references
7. Return complete `ResearchPaper` object

**Section Order:**
```python
sections = ['introduction', 'literature_review', 'methodology', 
            'results', 'discussion', 'conclusion']
```

**Word Count Targets (from settings):**
```python
SECTION_WORD_COUNTS = {
    'introduction': 400,
    'literature_review': 500,
    'methodology': 600,
    'results': 500,
    'discussion': 400,
    'conclusion': 300
}
```

---

### 5. RAG Service (`services/rag_service.py`)

Retrieves real research papers from Semantic Scholar.

**Class: `RAGService`**

**Search Strategy (Multi-pass):**
1. **Exact query**: Search full topic string
2. **Simplified query**: Remove stopwords
3. **Minimal query**: First 3 significant words
4. **Broad query**: Last 2 words of topic

**Caching:**
- Results cached in `paper_cache/` directory
- Cache key: `{topic_name}_{hash}.json` (readable names)
- Cache expiry: 24 hours (configurable)

**Methods:**
```python
search_papers(query, limit)      # Main search method
build_context(papers)            # Format papers for LLM context
_search_api(query, limit)        # Direct API call
_load_from_cache(query)          # Load cached results
_save_to_cache(query, papers)    # Save to cache
_get_cache_key(query)            # Generate readable cache filename
```

**API Fields Retrieved:**
- title, abstract, authors, year
- citationCount, venue, externalIds (DOI)
- url

---

### 6. Export Service (`services/export_service.py`)

Generates output files in multiple formats.

**Class: `ExportService`**

**Methods:**

**`generate_html(paper)`** - IEEE-style HTML with:
- Two-column layout (CSS columns)
- Times New Roman font
- Centered title and authors
- Abstract with italic styling
- Proper section headers (I., II., III., etc.)
- Encoding fix for special characters

**`generate_pdf(paper)`** - ReportLab PDF with:
- IEEE format layout
- First page: full-width header, then two columns
- Subsequent pages: two columns throughout
- References section

**`generate_docx(paper)`** - Word document with:
- IEEE-style formatting
- Proper headings and sections

**Encoding Fix Helper:**
```python
def _fix_encoding(self, text):
    encoding_fixes = {
        'â€¢': '•', 'Â²': '²', 'Â³': '³',
        'Ã©': 'é', 'Ã¡': 'á', ...
    }
    for bad, good in encoding_fixes.items():
        result = result.replace(bad, good)
    return result
```

---

### 7. Evaluation Service (`services/evaluation_service.py`)

Evaluates generated paper quality.

**Class: `EvaluationService`**

**Metrics:**

**BLEU Score** (0-100):
- Measures n-gram overlap with reference
- Uses NLTK's sentence_bleu
- Weights: unigram=0.25, bigram=0.25, trigram=0.25, 4-gram=0.25

**ROUGE Score** (0-100):
- ROUGE-1: Unigram overlap
- ROUGE-2: Bigram overlap
- ROUGE-L: Longest common subsequence

**Interpretation:**
| Score Range | Quality |
|-------------|---------|
| 70-100 | Excellent - High similarity to sources |
| 40-70 | Good - Reasonable synthesis |
| 20-40 | Fair - Original but may lack depth |
| 0-20 | Poor - Too different from sources |

**Special Handling:**
- Academic papers should NOT have very high scores (would indicate plagiarism)
- Target: 30-60% range indicates good synthesis

---

### 8. Integrity Service (`services/integrity_service.py`)

Simulates AI detection and plagiarism checking.

**Class: `ContentIntegrityService`**

**Modes:**
1. **Simulation Mode**: Returns random 20-40% scores
2. **API Mode**: Calls ZeroGPT API (if key provided)

**Returns:**
```python
{
    'ai_detection': {'score': 25.5, ...},
    'plagiarism': {'score': 18.2, ...}
}
```

---

### 9. Cache Manager (`utils/cache_manager.py`)

Manages RAG cache operations.

**Class: `CacheManager`**

**Features:**
- Readable filenames: `topic_name_hash.json`
- Automatic expiry checking
- Clear expired/all cache methods

**Cache Key Generation:**
```python
def get_cache_key(self, query):
    clean = re.sub(r'[^\w\s-]', '', query.lower())
    clean = re.sub(r'\s+', '_', clean.strip())[:60]
    hash_suffix = hashlib.md5(query.encode()).hexdigest()[:8]
    return f"{clean}_{hash_suffix}"
```

---

## Configuration

### settings.py

```python
# API Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1:8b"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"

# Generation Parameters
TEMPERATURE_SETTINGS = {
    "title": 0.7,
    "abstract": 0.6,
    "introduction": 0.7,
    "literature_review": 0.65,
    "methodology": 0.6,
    "results": 0.5,
    "discussion": 0.7,
    "conclusion": 0.6
}

# Section Word Counts
SECTION_WORD_COUNTS = {
    'introduction': 400,
    'literature_review': 500,
    'methodology': 600,
    'results': 500,
    'discussion': 400,
    'conclusion': 300
}

# RAG Settings
RAG_PAPER_LIMIT = 20
CACHE_EXPIRY_HOURS = 24

# Directories
CACHE_DIR = 'paper_cache'
SAVED_PAPERS_DIR = 'saved_papers'
UPLOAD_FOLDER = 'uploads'
```

---

## API Endpoints

### Paper Generation

**POST `/api/generate`**
```json
Request:
{
    "topic": "Federated Learning for Medical Imaging",
    "title": "Optional explicit title",
    "authors": [
        {"name": "John Doe", "affiliation": "MIT", "email": "john@mit.edu"}
    ],
    "use_rag": true,
    "user_data": "Optional experimental data to include"
}

Response:
{
    "success": true,
    "paper": {
        "title": "...",
        "abstract": "...",
        "sections": {...},
        "references": [...],
        "doi": "10.1109/ACCESS.2026.XXXXX",
        "metadata": {"total_words": 2500, "generation_time": 45.2}
    }
}
```

### Export

**POST `/api/download-html`**
```json
Request:
{
    "paper": { /* full paper object */ }
}

Response: HTML file download
```

### Evaluation

**POST `/api/evaluate-paper`**
```json
Request:
{
    "paper": { /* paper object */ }
}

Response:
{
    "success": true,
    "evaluation": {
        "bleu_score": 42.5,
        "rouge_scores": {"rouge1": 45.2, "rouge2": 28.1, "rougeL": 38.5},
        "overall_quality": "Good"
    }
}
```

---

## Workflow & Data Flow

### Complete Paper Generation Flow

```
1. User Input
   └─► Topic: "Federated Learning for Medical Imaging"
   └─► Authors: [{name, affiliation, email}]
   └─► Options: use_rag=true, user_data="..."

2. Validation (RequestValidator)
   └─► Check topic length (10-500 chars)
   └─► Validate author format
   └─► Sanitize input

3. RAG Search (if enabled)
   └─► Check cache: paper_cache/federated_learning_xxx.json
   └─► If miss: Search Semantic Scholar API
       └─► Strategy 1: Exact query
       └─► Strategy 2: Simplified query
       └─► Strategy 3: Minimal query
       └─► Strategy 4: Broad query
   └─► Cache results
   └─► Build context string from papers

4. Title Generation (if not provided)
   └─► LLM prompt for academic title
   └─► Clean and format

5. Abstract Generation
   └─► Prompt: flowing prose, 220 words
   └─► Post-process: remove prefixes, clean encoding

6. Section Generation (loop)
   FOR each in [intro, lit_review, methodology, results, discussion, conclusion]:
       └─► Build section-specific prompt
       └─► Pass 1: Casual draft (temp=0.85)
       └─► Pass 2: Formalize (temp=0.6)
       └─► Remove banned words
       └─► Format structured content (line breaks, encoding)
       └─► Store in paper.sections[name]

7. Reference Compilation
   └─► Format RAG papers as IEEE citations
   └─► Add DOIs where available

8. Paper Assembly
   └─► Create ResearchPaper object
   └─► Calculate metadata (word counts, time)
   └─► Generate fake DOI

9. Auto-Save
   └─► Save to: saved_papers/20260116_Federated_Learning_xxx.json

10. Response
    └─► Return JSON with complete paper
```

---

## Key Algorithms

### 1. Multi-Strategy RAG Search

```python
def search_papers(query, limit):
    # Strategy 1: Exact query
    papers = search_api(query)
    
    # Strategy 2: Simplified (remove stopwords)
    if len(papers) < limit:
        simplified = remove_stopwords(query)
        papers += search_api(simplified)
    
    # Strategy 3: Minimal (first 3 keywords)
    if len(papers) < limit:
        minimal = first_n_keywords(query, 3)
        papers += search_api(minimal)
    
    # Strategy 4: Broad (last 2 words)
    if len(papers) < limit:
        broad = last_n_words(query, 2)
        papers += search_api(broad)
    
    return deduplicate(papers)[:limit]
```

### 2. Write Drunk, Edit Sober

```python
def generate_section(section_name, title, context, ...):
    # DRUNK: Creative first draft
    casual_prompt = build_casual_prompt(section_name, title, context)
    casual_draft = llm.generate(casual_prompt, temperature=0.85)
    
    # SOBER: Formalize to academic style
    formal_prompt = f"""
    You are a strict editor. Translate this to formal academic English:
    {casual_draft}
    Rules:
    - Professional, objective, precise tone
    - Keep all numbers and citations
    - Academic paragraph structure
    """
    formal = llm.generate(formal_prompt, temperature=0.6)
    
    # CLEANUP: Remove AI-isms
    clean = remove_banned_words(formal)
    formatted = format_structured_content(clean)
    
    return formatted
```

### 3. Content Formatting Post-Processor

```python
def _format_structured_content(text):
    # 1. Fix encoding
    fixes = {'â€¢': '•', 'Â²': '²', ...}
    for bad, good in fixes.items():
        text = text.replace(bad, good)
    
    # 2. Remove code fences
    text = re.sub(r'```', '', text)
    
    # 3. Line breaks before subsections (A., B., C.)
    for letter in 'ABCDE':
        text = re.sub(rf'(\w)\s+({letter}\.\s+\w)', r'\1\n\n\2', text)
    
    # 4. Line breaks before bullets
    text = re.sub(r'(\S)\s*•\s*', r'\1\n\n• ', text)
    
    # 5. Line breaks before numbered lists
    text = re.sub(r'(\w)\s+(\d+)\.\s+', r'\1\n\n\2. ', text)
    
    # 6. Line breaks before labels
    labels = ['Key Insight:', 'Objectives:', 'Methodology:', ...]
    for label in labels:
        text = re.sub(rf'(\w)\s+({label})', rf'\1\n\n\2', text)
    
    # 7. Remove artifacts
    text = re.sub(r'-{3,}', '', text)   # Dashes
    text = re.sub(r'\*{2,}', '', text)  # Bold markers
    text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines
    
    return text.strip()
```

---

## Export Formats

### HTML Export

**Features:**
- Two-column CSS layout (`column-count: 2`)
- IEEE-style formatting
- Times New Roman font
- Print-friendly (@media print rules)
- Encoding-safe output

**CSS Structure:**
```css
.two-column { column-count: 2; column-gap: 20px; }
.section-title { font-weight: bold; text-align: center; }
.abstract { font-style: italic; column-span: all; }
h1 { text-align: center; column-span: all; }
```

### DOCX Export

**Features:**
- IEEE heading styles
- Justified paragraphs
- Proper section breaks

### PPTX Export

**Features:**
- Title slide
- Section slides
- Bullet points for key content

---

## Quality Evaluation

### BLEU Score Calculation

```python
def calculate_bleu(generated, references):
    # Tokenize
    gen_tokens = word_tokenize(generated.lower())
    ref_tokens = [word_tokenize(r.lower()) for r in references]
    
    # Calculate with smoothing
    score = sentence_bleu(
        ref_tokens, gen_tokens,
        weights=(0.25, 0.25, 0.25, 0.25),
        smoothing_function=smoothing.method1
    )
    
    return score * 100
```

### ROUGE Score Calculation

```python
def calculate_rouge(generated, reference):
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'])
    scores = scorer.score(reference, generated)
    
    return {
        'rouge1': scores['rouge1'].fmeasure * 100,
        'rouge2': scores['rouge2'].fmeasure * 100,
        'rougeL': scores['rougeL'].fmeasure * 100
    }
```

---

## Troubleshooting

### Common Issues

**1. Ollama Connection Error**
```
Error: Connection refused to localhost:11434
Solution: Start Ollama server: `ollama serve`
```

**2. Model Not Found**
```
Error: Model llama3.1:8b not found
Solution: Pull model: `ollama pull llama3.1:8b`
```

**3. Encoding Issues in Output**
```
Symptom: â€¢ instead of •
Solution: Already fixed in _format_structured_content()
```

**4. Cache Not Updating**
```
Solution: Delete files in paper_cache/ directory
```

**5. Generation Takes Too Long**
```
Cause: LLM warmup on first request
Solution: Call /api/warmup on page load
```

---

## Running the Application

### Prerequisites
1. Python 3.10+
2. Ollama installed and running
3. Llama 3.1 8B model pulled

### Installation
```bash
# Clone repository
git clone https://github.com/AbhishekJacobSanthosh/PAPERGEN.git
cd PAPERGEN/fixedproj

# Install dependencies
pip install -r requirements.txt

# Start Ollama (separate terminal)
ollama serve

# Pull model (first time only)
ollama pull llama3.1:8b

# Run application
python app.py
```

### Access
Open http://127.0.0.1:8080 in browser

---

## Authors
- Abhishek Jacob Santhosh

## License
MIT License

---

*Documentation generated: January 16, 2026*
