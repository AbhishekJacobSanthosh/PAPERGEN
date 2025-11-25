"""
Text Processing Utilities - Cleaning and formatting text
Fixed to handle all markdown artifacts and ensure clean output
"""
import re


class TextProcessor:
    """Utility class for text processing operations"""

    @staticmethod
    def validate_title_preserved(text: str, paper_title: str) -> tuple:
        """
        Check if paper title is preserved in the text's opening sentences.
        Returns: (is_preserved, warning_message_or_empty)
        """
        if not text or not paper_title:
            return False, "Text or title is empty"
        # Check if title appears in opening of string (case-insensitive)
        first_200_chars = text[:200].lower()
        title_lower = paper_title.lower()
        if title_lower in first_200_chars:
            return True, ""
        return False, f"Title '{paper_title}' not found at start of section"

    
    @staticmethod
    def clean_generated_text(text: str, section_name: str = "", paper_title: str = "") -> str:
        """
        Clean LLM-generated text by removing unwanted formatting
        
        Args:
            text: Raw generated text
            section_name: Name of the section for context
            paper_title: Paper title to remove if present
            
        Returns:
            Cleaned text
        """
        if not text:
            return text
        
        # Remove markdown headers (###, ##, #)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        if paper_title:
            # Remove title ONLY if it's a heading at the start of a line
            text = re.sub(rf'^{re.escape(paper_title)}\s*:?\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
            # Remove ONLY if preceded by markdown (e.g., "## Title")
            text = re.sub(rf'^#{1,6}\s*{re.escape(paper_title)}\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
            # Do NOT remove title from normal prose!
        
        # Remove section titles (standalone or with markdown)
        section_keywords = [
            'Abstract', 'Introduction', 'Literature Review', 'Background',
            'Methodology', 'Methods', 'Results', 'Discussion', 'Conclusion',
            'References', 'Objectives', 'Problem Statement', 'Related Work',
            'Future Work', 'Acknowledgments', 'Keywords'
        ]
        
        for keyword in section_keywords:
            # Remove section titles at start of line
            text = re.sub(rf'^{keyword}\s*:?\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
            text = re.sub(rf'^#{1,6}\s*{keyword}\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        
        # Remove bold formatting (**text** or __text__)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        
        # Remove italic formatting (*text* or _text_)
        text = re.sub(r'\*([^\*]+?)\*', r'\1', text)
        text = re.sub(r'_([^_]+?)_', r'\1', text)
        
        # Remove bullet points and numbered lists
        text = re.sub(r'^\s*[\-\*•]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+[\.\)]\s+', '', text, flags=re.MULTILINE)
        
        # Remove horizontal rules
        text = re.sub(r'^[\-\*_]{3,}\s*$', '', text, flags=re.MULTILINE)
        
        # Clean up multiple blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove extra spaces
        text = re.sub(r' {2,}', ' ', text)
        
        # Clean up first person references if not in methodology/results
        if section_name not in ['methodology', 'results']:
            text = TextProcessor.remove_first_person(text)
        
        return text.strip()
    
    @staticmethod
    def clean_survey_text(text: str) -> str:
        """
        Clean literature survey text - aggressive markdown removal
        
        Args:
            text: Raw survey text
            
        Returns:
            Cleaned survey text
        """
        if not text:
            return text
        
        # Remove all markdown headers (###, ##, #)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Remove bold (**text** or __text__)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        
        # Remove italic (*text* or _text_)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        
        # Remove bullet points (-, *, •)
        text = re.sub(r'^[\-\*•]\s+', '', text, flags=re.MULTILINE)
        
        # Remove numbered lists (1., 2., etc)
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Remove extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def validate_topic_references(text: str, topic: str) -> tuple:
        """
        Detect and fix more blank topic reference scenarios, including:
        - "on ,", "in ,", "of ,", "for ,", etc.
        - "on .", "for .", etc.
        - Lines starting with 'is', 'are', 'was' (missing subject)
        - Standalone lines/phrases that begin with punctuation
        """
        issues = []

        # Fix blanks after common prepositions - use generic term instead of full topic
        preps = ['on', 'in', 'of', 'for', 'with', 'to', 'about', 'as', 'at', 'by']
        for kw in preps:
            text, n1 = re.subn(rf'\b{kw}\s*[,\.]', f'{kw} this domain,', text)
            if n1: issues.append(f"Fixed {n1} instances of '{kw} ,'")
            text, n2 = re.subn(rf'\b{kw}\s*\.', f'{kw} this domain.', text)
            if n2: issues.append(f"Fixed {n2} trailing preposition blanks")

        # Fix sentences that start with a verb - use "This study" or "The system"
        text, n3 = re.subn(
            r'(^|\n+)\s*(is|are|was|were|has|have|can|will|may|provides|offers|represents)\b',
            f'\nThis study \\2', text, flags=re.IGNORECASE
        )
        if n3: issues.append("Fixed lines starting with a verb (inserted 'This study').")

        # Fix lines that start with punctuation - remove the punctuation instead of inserting title
        text, n4 = re.subn(r'(^|\n)[\.,;:]\s*', r'\1', text)
        if n4: issues.append("Removed leading punctuation.")

        # Fix 'for future work in .' and similar endings
        text, n5 = re.subn(r'in\s*\.', f'in this field.', text)
        if n5: issues.append("Fixed 'in .' endings.")
        text, n6 = re.subn(r'for\s*\.', f'for future research.', text)
        if n6: issues.append("Fixed 'for .' endings.")
        
        return text, issues

    @staticmethod
    def remove_first_person(text: str) -> str:
        """Remove or replace first-person references"""
        replacements = {
            r'\bWe\b': 'This research',
            r'\bwe\b': 'this research',
            r'\bOur\b': 'The',
            r'\bour\b': 'the',
            r'\bI\b': 'This study',
            r'\bMy\b': 'The'
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        
        return text
    
    @staticmethod
    def ensure_complete_sentence(text: str) -> str:
        """Ensure text ends with complete sentence"""
        if not text:
            return text
        
        # Check if ends with punctuation
        if text[-1] not in '.!?':
            # Find last complete sentence
            sentences = text.split('.')
            if len(sentences) > 1:
                # Keep all but last incomplete sentence
                text = '.'.join(sentences[:-1]) + '.'
        
        return text.strip()
    
    @staticmethod
    def count_words(text: str) -> int:
        """Count words in text"""
        if not text:
            return 0
        return len(text.split())
