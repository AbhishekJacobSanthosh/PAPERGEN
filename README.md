# 🎓 AI Research Paper Generator v3.0

Professional research paper generator with Literature Survey, RAG, and IEEE formatting.

## Features

- 📚 **Literature Survey Generator** - Retrieve and analyze papers from Semantic Scholar
- 📝 **Research Paper Generator** - AI-powered paper generation with proper structure
- 🎨 **Dynamic Figures** - Automatic generation of charts, tables, and word clouds
- 📄 **IEEE Format Export** - Professional PDF and DOCX outputs
- 🔍 **OCR Support** - Extract text from images
- 🌐 **RAG Enhanced** - Context from real research papers

## Installation

1. **Install Ollama and pull the model:**

ollama pull qwen2.5-coder:7b

2. **Clone and setup:**

git clone <your-repo>
cd research-paper-generator
pip install -r requirements.txt


3. **Run the application:**

python app.py

4. **Open browser:**

http://localhost:8080

Make sure to have python version 3.10.11

## Project Structure

research-paper-generator/
├── app.py # Main Flask application
├── config/ # Configuration
├── models/ # Data models and LLM interface
├── services/ # Business logic
├── utils/ # Utilities
├── static/ # CSS, JS, images
└── templates/ # HTML templates

## Usage

### Literature Survey
1. Enter research topic
2. Retrieve relevant papers
3. Generate comprehensive survey
4. Download as PDF/DOCX

### Paper Generation
1. Enter title or description
2. Add authors
3. Generate complete paper
4. Export in IEEE format

## Configuration

Edit `config/settings.py` to customize:
- Model selection
- Paper generation parameters
- API endpoints
- Cache settings

## License

MIT License
