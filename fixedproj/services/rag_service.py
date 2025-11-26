"""
RAG Service - Semantic Scholar paper retrieval with caching
"""
import requests
import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import List, Optional
from models.paper_structure import Reference
from config.settings import (
    SEMANTIC_SCHOLAR_API, RAG_PAPER_LIMIT, 
    CACHE_DIR, CACHE_EXPIRY_HOURS, API_TIMEOUT, MAX_RETRIES
)

class RAGService:
    """Service for retrieving research papers from Semantic Scholar"""
    
    def __init__(self):
        self.api_base = SEMANTIC_SCHOLAR_API
        self.cache_dir = CACHE_DIR
    
    def search_papers(self, query: str, limit: int = RAG_PAPER_LIMIT) -> List[Reference]:
        """
        Search for papers on Semantic Scholar with caching
        
        Args:
            query: Search query
            limit: Number of papers to retrieve
            
        Returns:
            List of Reference objects
        """
        # Check cache first
        cached = self._load_from_cache(query)
        if cached:
            print(f"[RAG] Using cached papers for: {query[:50]}...")
            return cached[:limit]
        
        # Search API
        print(f"[RAG] Searching Semantic Scholar: {query[:50]}...")
        papers = self._search_api(query, limit)
        
        # Fallback for long queries if no papers found
        if not papers and len(query.split()) > 5:
            simplified_query = self._simplify_query(query)
            if simplified_query != query:
                print(f"[RAG] No papers found. Retrying with simplified query: {simplified_query}")
                papers = self._search_api(simplified_query, limit)
        
        # Second fallback: Minimal query
        if not papers:
            # Try just the first few significant words
            words = [w for w in query.split() if len(w) > 3]
            if len(words) >= 2:
                minimal_query = ' '.join(words[:3])
                if minimal_query != query and minimal_query != self._simplify_query(query):
                    print(f"[RAG] Still no papers. Retrying with minimal query: {minimal_query}")
                    papers = self._search_api(minimal_query, limit)
        
        if papers:
            # Save to cache
            self._save_to_cache(query, papers)
            print(f"[RAG] Retrieved {len(papers)} papers")
        else:
            print("[RAG] No papers found")
        
        return papers
    
    def build_context(self, papers: List[Reference]) -> str:
        """
        Build formatted context string from retrieved papers for LLM
        
        Args:
            papers: List of Reference objects
            
        Returns:
            Formatted context string
        """
        if not papers:
            return ""
        
        context_parts = []
        
        for i, paper in enumerate(papers, 1):
            # Format authors
            if len(paper.authors) > 3:
                authors_str = ', '.join(paper.authors[:3]) + ' et al.'
            else:
                authors_str = ', '.join(paper.authors)
            
            # Build paper context
            paper_context = f"Paper {i}:\n"
            paper_context += f"Title: {paper.title}\n"
            paper_context += f"Authors: {authors_str}\n"
            paper_context += f"Year: {paper.year}\n"
            paper_context += f"Venue: {paper.venue or 'Unknown'}\n"
            paper_context += f"Citations: {paper.citation_count}\n"
            
            if paper.abstract:
                # Limit abstract to 500 chars for context
                abstract_preview = paper.abstract[:500]
                if len(paper.abstract) > 500:
                    abstract_preview += "..."
                paper_context += f"Abstract: {abstract_preview}\n"
            
            context_parts.append(paper_context)
        
        return "\n".join(context_parts)


    def _search_api(self, query: str, limit: int) -> List[Reference]:
        """Search Semantic Scholar API with retry logic"""
        url = f"{self.api_base}/paper/search"
        # Fetch more candidates to account for filtering
        fetch_limit = limit * 3
        params = {
            'query': query,
            'limit': fetch_limit,
            'fields': 'title,abstract,authors,year,citationCount,venue,externalIds,url'
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, params=params, timeout=API_TIMEOUT)
                
                if response.status_code == 200:
                    data = response.json()
                    papers_data = data.get('data', [])
                    
                    # Convert to Reference objects
                    references = []
                    for paper in papers_data:
                        if paper.get('abstract'):  # Only papers with abstracts
                            ref = Reference(
                                title=paper.get('title', 'Unknown Title'),
                                authors=[a.get('name', 'Unknown') for a in paper.get('authors', [])],
                                year=paper.get('year', 0),
                                venue=paper.get('venue', 'Unknown Venue'),
                                doi=paper.get('externalIds', {}).get('DOI'),
                                url=paper.get('url'),
                                citation_count=paper.get('citationCount', 0),
                                abstract=paper.get('abstract', '')
                            )
                            references.append(ref)
                            
                            if len(references) >= limit:
                                break
                    
                    return references
                
                elif response.status_code == 429:
                    print(f"[RAG] Rate limited, waiting... (attempt {attempt + 1})")
                    import time
                    time.sleep(5)
                else:
                    print(f"[RAG] API error {response.status_code}")
                    
            except Exception as e:
                print(f"[RAG] Error: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    import time
                    time.sleep(2)
        
        return []
    
    def format_context(self, papers: List[Reference]) -> str:
        """Format papers as context string for LLM"""
        if not papers:
            return ""
        
        context_parts = []
        for i, paper in enumerate(papers, 1):
            authors_str = ', '.join(paper.authors[:3])
            if len(paper.authors) > 3:
                authors_str += ' et al.'
            
            context_parts.append(f"""
Paper {i}: {paper.title}
Authors: {authors_str} ({paper.year})
Venue: {paper.venue}
Citations: {paper.citation_count}
Abstract: {paper.abstract[:400]}...
""")
        
        return '\n'.join(context_parts)
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key from query"""
        return hashlib.md5(query.lower().encode()).hexdigest()
    
    def _load_from_cache(self, query: str) -> Optional[List[Reference]]:
        """Load cached papers if available and fresh"""
        cache_key = self._get_cache_key(query)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check expiry
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cached_time > timedelta(hours=CACHE_EXPIRY_HOURS):
                print("[RAG] Cache expired")
                return None
            
            # Convert back to Reference objects
            references = []
            for paper_data in cache_data['papers']:
                ref = Reference(
                    title=paper_data['title'],
                    authors=paper_data['authors'],
                    year=paper_data['year'],
                    venue=paper_data['venue'],
                    doi=paper_data.get('doi'),
                    url=paper_data.get('url'),
                    citation_count=paper_data.get('citation_count', 0),
                    abstract=paper_data.get('abstract', '')
                )
                references.append(ref)
            
            return references
            
        except Exception as e:
            print(f"[RAG] Cache read error: {e}")
            return None
    
    def _save_to_cache(self, query: str, papers: List[Reference]):
        """Save papers to cache"""
        cache_key = self._get_cache_key(query)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'papers': [
                    {
                        'title': p.title,
                        'authors': p.authors,
                        'year': p.year,
                        'venue': p.venue,
                        'doi': p.doi,
                        'url': p.url,
                        'citation_count': p.citation_count,
                        'abstract': p.abstract
                    } for p in papers
                ]
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            print(f"[RAG] Cache save error: {e}")

    def _simplify_query(self, query: str) -> str:
        """Simplify query by removing common stopwords and keeping key terms"""
        stopwords = {'investigating', 'the', 'efficacy', 'of', 'in', 'preventing', 'a', 'an', 'and', 'for', 'to', 'with', 'on', 'at', 'by'}
        words = query.lower().split()
        key_terms = [w for w in words if w not in stopwords]
        return ' '.join(key_terms)
