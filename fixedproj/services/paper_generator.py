import uuid
import logging
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import concurrent.futures

from models.paper_structure import ResearchPaper, Author, Reference, Figure
from models.llm import LLMInterface
from services.rag_service import RAGService
from services.figure_generator import FigureGeneratorService
from utils.text_processing import TextProcessor
from config.settings import MIN_REFERENCES, USE_REALISTIC_DATA, MAX_RAG_CONTEXT_CHARS

logger = logging.getLogger(__name__)

class PaperGeneratorService:
    """Service for generating complete research papers"""
    
    def __init__(self):
        self.llm = LLMInterface()
        self.rag = RAGService()
        self.figure_gen = FigureGeneratorService()
        self.text_processor = TextProcessor()
    
    def generate_paper(self, topic: str, authors: List[Author],
    use_rag: bool = True, user_data: Optional[Dict] = None, title: Optional[str] = None) -> ResearchPaper:
        """Generate complete research paper"""
        logger.info(f"Starting generation for: {topic}")
        logger.info(f"RAG enabled: {use_rag}, User data provided: {user_data is not None}")
        
        # Step 1: Generate title
        # Step 1: Use provided title or generate one
        if title:
            logger.info(f"Using external/preset title: {title}")
        else:
            title = self.generate_title(topic)
            logger.info(f"Generated title: {title}")

        
        # Step 2: RAG - Retrieve papers
        rag_context = ""
        retrieved_papers = []
        if use_rag:
            logger.info("Retrieving papers from Semantic Scholar...")
            retrieved_papers = self.rag.search_papers(topic, limit=20)
            rag_context = self.rag.build_context(retrieved_papers)
            if len(rag_context) > MAX_RAG_CONTEXT_CHARS:
                rag_context = rag_context[:MAX_RAG_CONTEXT_CHARS] + "..."
                logger.warning(f"RAG context truncated to {MAX_RAG_CONTEXT_CHARS} chars")
            logger.info(f"Retrieved {len(retrieved_papers)} papers")
        
        # Step 3: Generate abstract
        logger.info("Generating abstract...")
        abstract = self.llm.generate_abstract(title, rag_context)
        # Double topic validation
        for _ in range(2):
            abstract, issues = self.text_processor.validate_topic_references(abstract, title)
            if issues:
                logger.debug(f"[Validation] abstract: " + ', '.join(issues))
        # Check preservation
        is_preserved, warning = self.text_processor.validate_title_preserved(abstract, title)
        if not is_preserved:
            logger.error(f"[Abstract pre-clean] {warning} - {abstract[:100]}")
        abstract = self.text_processor.clean_generated_text(
            abstract, section_name="abstract", paper_title=title
        )
        # Check after cleaning
        is_preserved_after, warning_after = self.text_processor.validate_title_preserved(abstract, title)
        if not is_preserved_after and is_preserved:
            logger.error(f"[Abstract post-clean] ⚠️ TITLE LOST: {warning_after}")
        logger.info(f"Abstract: {len(abstract.split())} words")
        
        # Step 4: Generate sections
        sections = {}
        previous_sections = {'abstract': abstract}
        
        # Sequential sections (dependent on previous context)
        sequential_sections = ['introduction']
        
        for section_name in sequential_sections:
            logger.info(f"Generating {section_name}...")
            use_context = True # Introduction always uses context
            context = rag_context if use_rag and use_context else ""
            
            content = self.llm.generate_section(
                section_name=section_name,
                title=title,
                previous_sections=previous_sections,
                rag_context=context,
                user_data=None # Intro usually doesn't need user data directly
            )
            
            if not content:
                content = f"[{section_name.title()} content generation failed]"
            else:
                content = self.text_processor.clean_generated_text(
                    content, section_name=section_name, paper_title=title
                )
                
            sections[section_name] = content
            previous_sections[section_name] = content
            logger.info(f"✓ {section_name}: {self.text_processor.count_words(content)} words")

        # Parallel sections (can run independently given Intro + Abstract)
        parallel_sections = ['literature_review', 'methodology', 'results', 'discussion', 'conclusion']
        
        # Prepare user data context for specific sections
        section_user_data = {}
        if user_data:
            # Methodology context
            method_parts = []
            if user_data.get('methodology'):
                method_parts.append(user_data['methodology'])
            if user_data.get('dataset', {}).get('name'):
                dataset_info = f"Dataset: {user_data['dataset']['name']}"
                if user_data['dataset'].get('size'):
                    dataset_info += f", {user_data['dataset']['size']}"
                if user_data['dataset'].get('details'):
                    dataset_info += f". {user_data['dataset']['details']}"
                method_parts.append(dataset_info)
            if method_parts:
                section_user_data['methodology'] = '\n\n'.join(method_parts)

            # Results context
            result_parts = []
            if user_data.get('results'):
                result_parts.append(user_data['results'])
            if user_data.get('findings'):
                result_parts.append(f"Key Observations: {user_data['findings']}")
            if result_parts:
                section_user_data['results'] = '\n\n'.join(result_parts)

        logger.info(f"Starting parallel generation for: {', '.join(parallel_sections)}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_section = {
                executor.submit(
                    self._generate_section_task, 
                    section_name, 
                    title, 
                    previous_sections.copy(), # Pass copy of current context
                    rag_context if use_rag else "",
                    section_user_data.get(section_name)
                ): section_name 
                for section_name in parallel_sections
            }
            
            for future in concurrent.futures.as_completed(future_to_section):
                section_name = future_to_section[future]
                try:
                    content = future.result()
                    sections[section_name] = content
                    logger.info(f"✓ {section_name}: {self.text_processor.count_words(content)} words")
                except Exception as e:
                    logger.error(f"Error generating {section_name}: {e}")
                    sections[section_name] = f"[{section_name.title()} generation failed]"

        
        # Step 5: Generate references
        logger.info("Generating references...")
        references = self._generate_references(retrieved_papers, title)
        reference_text = self._format_references(references)
        sections['references'] = reference_text
        logger.info(f"References: {len(references)} total")
        
        # Step 6: Generate figures
        figures = {}
        if USE_REALISTIC_DATA:
            logger.info("Generating figures and tables...")
            try:
                table_data = self.figure_gen.generate_realistic_comparison_table(retrieved_papers)
                figures['table1'] = Figure(
                    type='table',
                    caption='Performance comparison with state-of-the-art methods',
                    data=table_data,
                    number=1
                )
                chart_data = self.figure_gen.generate_keyword_chart(sections)
                if chart_data:
                    figures['figure1'] = Figure(
                        type='chart',
                        caption='Keyword frequency analysis',
                        data=chart_data,
                        number=2
                    )
                logger.info(f"Generated {len(figures)} figures/tables")
            except Exception as e:
                logger.warning(f"Figure generation failed: {e}")
        
        # Step 7: Create paper object
        paper = ResearchPaper(
            title=title,
            authors=authors,
            abstract=abstract,
            sections=sections,
            references=references,
            figures=figures,
            doi=self._generate_doi(),
            generated_at=datetime.now()
        )
        
        total_words = len(abstract.split())
        for section_name, section_content in sections.items():
            if section_name != 'references' and section_content:
                total_words += len(section_content.split())
        
        paper.metadata = {
            'total_words': total_words,
            'section_count': len(sections),
            'reference_count': len(references),
            'figure_count': len(figures),
            'rag_enabled': use_rag,
            'user_data_used': user_data is not None
        }
        logger.info(f"✓ Paper generation complete! ({total_words} words, {len(references)} refs)")
        return paper

    def generate_paper_stream(self, topic: str, authors: List[Author],
                            use_rag: bool = True, user_data: Optional[Dict] = None, 
                            title: Optional[str] = None):
        """Generate paper with streaming progress updates"""
        import json
        
        yield json.dumps({'status': 'start', 'message': 'Starting generation...'})
        
        # Step 1: Title
        if title:
            yield json.dumps({'status': 'title', 'message': f'Using title: {title}'})
        else:
            yield json.dumps({'status': 'title', 'message': 'Generating optimized title...'})
            title = self.generate_title(topic)
            yield json.dumps({'status': 'title_complete', 'title': title})
            
        # Step 2: RAG
        rag_context = ""
        retrieved_papers = []
        if use_rag:
            yield json.dumps({'status': 'rag_start', 'message': 'Searching for relevant research papers...'})
            retrieved_papers = self.rag.search_papers(topic, limit=20)
            rag_context = self.rag.build_context(retrieved_papers)
            if len(rag_context) > MAX_RAG_CONTEXT_CHARS:
                rag_context = rag_context[:MAX_RAG_CONTEXT_CHARS] + "..."
            yield json.dumps({'status': 'rag_complete', 'count': len(retrieved_papers)})
            
        # Step 3: Abstract
        yield json.dumps({'status': 'abstract', 'message': 'Drafting abstract...'})
        abstract = self.llm.generate_abstract(title, rag_context)
        abstract = self.text_processor.clean_generated_text(abstract, section_name="abstract", paper_title=title)
        
        # Step 4: Generate sections
        sections = {}
        previous_sections = {'abstract': abstract}
        
        # 4a. Sequential Introduction
        yield json.dumps({
            'status': 'section_start', 
            'section': 'introduction', 
            'message': 'Writing Introduction...'
        })
        
        intro_content = self.llm.generate_section(
            section_name='introduction',
            title=title,
            previous_sections=previous_sections,
            rag_context=rag_context if use_rag else "",
            user_data=None
        )
        
        if intro_content:
            intro_content = self.text_processor.clean_generated_text(intro_content, section_name='introduction', paper_title=title)
        else:
            intro_content = "[Introduction generation failed]"
            
        sections['introduction'] = intro_content
        previous_sections['introduction'] = intro_content
        
        yield json.dumps({
            'status': 'section_complete', 
            'section': 'introduction',
            'preview': intro_content[:100] + "..."
        })

        # 4b. Parallel Sections
        parallel_sections = ['literature_review', 'methodology', 'results', 'discussion', 'conclusion']
        
        yield json.dumps({
            'status': 'parallel_start',
            'message': 'Generating remaining sections in parallel...'
        })
        
        # Prepare user data
        section_user_data = {}
        if user_data:
            if user_data.get('methodology') or user_data.get('dataset'):
                section_user_data['methodology'] = str(user_data.get('methodology', '')) + str(user_data.get('dataset', ''))
            if user_data.get('results') or user_data.get('findings'):
                section_user_data['results'] = str(user_data.get('results', '')) + str(user_data.get('findings', ''))

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_section = {
                executor.submit(
                    self._generate_section_task, 
                    section_name, 
                    title, 
                    previous_sections.copy(), 
                    rag_context if use_rag else "",
                    section_user_data.get(section_name)
                ): section_name 
                for section_name in parallel_sections
            }
            
            for future in concurrent.futures.as_completed(future_to_section):
                section_name = future_to_section[future]
                try:
                    content = future.result()
                    sections[section_name] = content
                    
                    yield json.dumps({
                        'status': 'section_complete', 
                        'section': section_name,
                        'preview': content[:100] + "..."
                    })
                except Exception as e:
                    logger.error(f"Stream error {section_name}: {e}")
                    sections[section_name] = f"[{section_name} failed]"

        # Step 5: References
        yield json.dumps({'status': 'references', 'message': 'Compiling references...'})
        references = self._generate_references(retrieved_papers, title)
        
        # Add references to sections for export
        reference_text = self._format_references(references)
        sections['references'] = reference_text
        
        # Step 6: Figures
        figures = {}
        if USE_REALISTIC_DATA and retrieved_papers:
            yield json.dumps({'status': 'figures', 'message': 'Generating data visualizations...'})
            try:
                table_data = self.figure_gen.generate_realistic_comparison_table(retrieved_papers)
                figures['table1'] = Figure(type='table', caption='Performance comparison', data=table_data, number=1)
            except:
                pass

        # Finalize
        paper = ResearchPaper(
            title=title,
            authors=authors,
            abstract=abstract,
            sections=sections,
            references=references,
            figures=figures,
            doi=self._generate_doi(),
            generated_at=datetime.now()
        )
        
        # Calculate metadata
        total_words = len(abstract.split()) + sum(len(s.split()) for s in sections.values() if s)
        paper.metadata = {
            'total_words': total_words,
            'rag_enabled': use_rag
        }
        
        # Auto-save the paper
        self.save_paper(paper)
        
        yield json.dumps({'status': 'complete', 'paper': paper.to_dict()})
    
    def generate_title(self, description: str) -> str:
        if len(description.split()) <= 12:
            return description.strip()
        title = self.llm.generate_title(description)
        if not title or len(title.strip()) < 5:
            logger.warning(f"Title generation failed, using truncated description")
            return description[:80].strip()
        return title
    
    def _generate_references(self, retrieved_papers: List[Reference], title: str) -> List[Reference]:
        # Use all retrieved papers
        references = list(retrieved_papers)
        logger.info(f"Using {len(references)} retrieved papers for references")
        
        if len(references) < MIN_REFERENCES:
             logger.warning(f"Only found {len(references)} papers, but proceeding with authentic references only.")
            
        return references
    

    
    def _format_references(self, references: List[Reference]) -> str:
        formatted = []
        for i, ref in enumerate(references, 1):
            authors_str = ', '.join(ref.authors[:3]) + (' et al.' if len(ref.authors) > 3 else '')
            ref_str = f"[{i}] {authors_str}, \"{ref.title},\" {ref.venue}, {ref.year}."
            if ref.doi:
                ref_str += f" DOI: {ref.doi}"
            
            # Normalize text to remove artifacts like black squares (non-standard hyphens)
            ref_str = self.text_processor.normalize_text(ref_str)
            formatted.append(ref_str)
        return '\n\n'.join(formatted)
    
    def _generate_doi(self) -> str:
        year = datetime.now().year
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"10.1109/ACCESS.{year}.{unique_id}"

    def _generate_section_task(self, section_name, title, previous_sections, rag_context, user_data):
        """Helper for parallel execution"""
        logger.info(f"Generating {section_name} (Parallel)...")
        content = self.llm.generate_section(
            section_name=section_name,
            title=title,
            previous_sections=previous_sections,
            rag_context=rag_context,
            user_data=user_data
        )
        
        if content:
            content = self.text_processor.clean_generated_text(
                content, section_name=section_name, paper_title=title
            )
        else:
            content = f"[{section_name} failed]"
            
        return content

    def save_paper(self, paper: ResearchPaper) -> str:
        """Save paper to disk as JSON"""
        try:
            # Create directory if not exists
            save_dir = os.path.join(os.getcwd(), 'saved_papers')
            os.makedirs(save_dir, exist_ok=True)
            
            # Create filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_title = "".join([c for c in paper.title if c.isalnum() or c in (' ', '-', '_')]).strip()
            safe_title = safe_title.replace(' ', '_')[:50]
            filename = f"{timestamp}_{safe_title}.json"
            filepath = os.path.join(save_dir, filename)
            
            # Save JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(paper.to_dict(), f, indent=4, ensure_ascii=False)
                
            logger.info(f"Paper saved to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save paper: {e}")
            return ""
