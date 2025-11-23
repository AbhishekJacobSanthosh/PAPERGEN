"""
Data models for research paper structure
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

@dataclass
class Author:
    """Author information"""
    name: str
    email: str
    affiliation: str
    
    def __str__(self) -> str:
        return f"{self.name} ({self.affiliation})"

@dataclass
class Reference:
    """Research paper reference in IEEE format"""
    title: str
    authors: List[str]
    year: int
    venue: str
    doi: Optional[str] = None
    url: Optional[str] = None
    citation_count: int = 0
    abstract: Optional[str] = None
    
    def to_ieee_format(self, index: int) -> str:
        """Convert to IEEE citation format"""
        # Format authors
        if len(self.authors) == 0:
            author_str = "Unknown"
        elif len(self.authors) <= 3:
            author_str = ', '.join(self.authors)
        else:
            author_str = f"{', '.join(self.authors[:3])}, et al."
        
        # Build citation
        citation = f"[{index}] {author_str}, \"{self.title},\" {self.venue}, {self.year}"
        if self.doi:
            citation += f", doi: {self.doi}"
        citation += "."
        
        return citation

@dataclass
class Figure:
    """Figure or table in paper"""
    type: str  # 'wordcloud', 'keyword_chart', 'table', 'user_chart'
    caption: str
    data: Any  # base64 string for images, list of lists for tables
    number: int
    
    def get_key(self) -> str:
        """Get dictionary key for this figure"""
        if self.type == 'table':
            return f"table{self.number}"
        else:
            return f"figure{self.number}"

@dataclass
class PaperSection:
    """A section of the research paper"""
    name: str
    title: str
    content: str
    word_count: int
    
    def is_complete(self) -> bool:
        """Check if section content is complete (ends with punctuation)"""
        if not self.content:
            return False
        return self.content.strip()[-1] in '.!?'

@dataclass
class ResearchPaper:
    """Complete research paper structure"""
    title: str
    authors: List[Author]
    abstract: str
    sections: Dict[str, str]  # section_name: content
    references: List[Reference]
    figures: Dict[str, Figure]  # figure_key: Figure object
    doi: str
    generated_at: datetime
    metadata: Dict = field(default_factory=dict)
    
    def get_total_word_count(self) -> int:
        """Calculate total word count"""
        total = len(self.abstract.split())
        for content in self.sections.values():
            total += len(content.split())
        return total
    
    def validate(self) -> List[str]:
        """Validate paper structure and return list of issues"""
        issues = []
        
        # Check title
        if not self.title or len(self.title) < 10:
            issues.append("Title is too short or missing")
        
        # Check authors
        if not self.authors:
            issues.append("No authors specified")
        
        # Check abstract
        if not self.abstract or len(self.abstract.split()) < 100:
            issues.append("Abstract is too short (< 100 words)")
        if not self.abstract.strip().endswith('.'):
            issues.append("Abstract is incomplete (doesn't end with period)")
        
        # Check required sections
        required_sections = ['introduction', 'methodology', 'results', 'conclusion']
        for section in required_sections:
            if section not in self.sections:
                issues.append(f"Missing required section: {section}")
            elif len(self.sections[section].split()) < 50:
                issues.append(f"Section '{section}' is too short (< 50 words)")
        
        # Check references
        if len(self.references) < 5:
            issues.append(f"Too few references ({len(self.references)}) - minimum 5 required")
        
        return issues
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "title": self.title,
            "authors": [
                {
                    "name": a.name,
                    "email": a.email,
                    "affiliation": a.affiliation
                } for a in self.authors
            ],
            "abstract": self.abstract,
            "sections": self.sections,
            "references": [
                {
                    "title": r.title,
                    "authors": r.authors,
                    "year": r.year,
                    "venue": r.venue,
                    "doi": r.doi,
                    "url": r.url
                } for r in self.references
            ],
            "figures": {
                k: {
                    "type": f.type,
                    "caption": f.caption,
                    "data": f.data,
                    "number": f.number
                } for k, f in self.figures.items()
            },
            "doi": self.doi,
            "generated_at": self.generated_at.isoformat(),
            "metadata": self.metadata
        }
