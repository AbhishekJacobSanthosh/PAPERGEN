import uuid
import logging
from datetime import datetime
from typing import List, Dict, Optional

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
            retrieved_papers = self.rag.search_papers(topic, limit=5)
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
        section_order = [
            'introduction', 'literature_review', 'methodology',
            'results', 'discussion', 'conclusion'
        ]
        
        for idx, section_name in enumerate(section_order, 1):
            logger.info(f"[{idx}/6] Generating {section_name}...")
            use_context = section_name in ['introduction', 'literature_review', 'discussion']
            context = rag_context if use_rag and use_context else ""
            
            # User data prep
            user_context = None
            if user_data:
                if section_name == 'methodology':
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
                        user_context = '\n\n'.join(method_parts)
                elif section_name == 'results':
                    result_parts = []
                    if user_data.get('results'):
                        result_parts.append(user_data['results'])
                    if user_data.get('findings'):
                        result_parts.append(f"Key Observations: {user_data['findings']}")
                    if result_parts:
                        user_context = '\n\n'.join(result_parts)
            
            # LLM Generation
            content = self.llm.generate_section(
                section_name=section_name,
                title=title,
                previous_sections=previous_sections,
                rag_context=context,
                user_data=user_context
            )

            if not content:
                logger.error(f"Failed to generate {section_name}, using fallback")
                content = f"[{section_name.title()} content generation failed]"
            else:
                # Debug pre-clean
                is_preserved, warning = self.text_processor.validate_title_preserved(content, title)
                if not is_preserved:
                    logger.error(f"[Pre-clean] {warning} - Content starts with: {content[:120]}")
                for _ in range(2):
                    content, issues = self.text_processor.validate_topic_references(content, title)
                    if issues:
                        logger.debug(f"[Validation] {section_name}: " + ', '.join(issues))
                content = self.text_processor.clean_generated_text(
                    content, section_name=section_name, paper_title=title
                )
                # Debug post-clean
                is_preserved_after, warning_after = self.text_processor.validate_title_preserved(content, title)
                if not is_preserved_after and is_preserved:
                    logger.error(f"[Post-clean] ⚠️ TITLE LOST DURING CLEANING: {warning_after}")

            sections[section_name] = content
            previous_sections[section_name] = content
            logger.info(f"✓ {section_name}: {self.text_processor.count_words(content)} words")
        
        # Step 5: Generate references
        logger.info("Generating references...")
        references = self._generate_references(retrieved_papers, title)
        reference_text = self._format_references(references)
        sections['references'] = reference_text
        logger.info(f"References: {len(references)} total")
        
        # Step 6: Generate figures
        figures = {}
        if USE_REALISTIC_DATA and retrieved_papers:
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
    
    def generate_title(self, description: str) -> str:
        if len(description.split()) <= 12:
            return description.strip()
        title = self.llm.generate_title(description)
        if not title or len(title.strip()) < 5:
            logger.warning(f"Title generation failed, using truncated description")
            return description[:80].strip()
        return title
    
    def _generate_references(self, retrieved_papers: List[Reference], title: str) -> List[Reference]:
        references = list(retrieved_papers[:min(len(retrieved_papers), 5)])
        needed = MIN_REFERENCES - len(references)
        if needed > 0:
            generic_refs = self._get_generic_references(title, needed)
            references.extend(generic_refs)
        return references
    
    def _get_generic_references(self, title: str, count: int) -> List[Reference]:
        generic_refs = []
        current_year = datetime.now().year
        stopwords = {'the', 'a', 'an', 'in', 'on', 'for', 'to', 'of', 'and', 'using', 'with'}
        words = [w for w in title.split() if w.lower() not in stopwords and len(w) > 3]
        keyword_phrase = ' '.join(words[:3]) if len(words) >= 3 else (
            ' '.join(words) if words else "Advanced Research"
        )
        keyword_phrase = keyword_phrase.title()
        templates = [
            "Recent Advances in {topic}: A Comprehensive Survey",
            "Deep Learning Approaches for {topic} Applications",
            "{topic}: State-of-the-Art Methods and Future Directions",
            "A Systematic Review of {topic} Techniques",
            "Novel Architectures for {topic} Systems",
            "Transformer-Based Methods in {topic}",
            "Comparative Analysis of {topic} Algorithms",
            "Automated {topic} Using Machine Learning",
            "Multi-Modal Approaches to {topic}",
            "Attention Mechanisms for Improved {topic}",
            "Scalable Solutions for {topic} Challenges",
            "Optimization Strategies in {topic}",
            "Robust {topic} Methods for Real-World Applications",
            "Explainable AI for {topic}",
            "Transfer Learning in {topic} Domains"
        ]
        venues = [
            "IEEE Transactions on Pattern Analysis and Machine Intelligence",
            "International Conference on Computer Vision (ICCV)",
            "Conference on Neural Information Processing Systems (NeurIPS)",
            "International Conference on Machine Learning (ICML)",
            "IEEE Transactions on Industrial Informatics",
            "ACM Computing Surveys",
            "International Journal of Computer Vision",
            "Computer Vision and Pattern Recognition (CVPR)",
            "European Conference on Computer Vision (ECCV)",
            "IEEE Access",
            "Nature Machine Intelligence",
            "Journal of Machine Learning Research"
        ]
        author_pools = [
            ["Smith", "Johnson", "Williams"],
            ["Zhang", "Li", "Wang"],
            ["Kumar", "Patel", "Singh"],
            ["Garcia", "Martinez", "Rodriguez"],
            ["Kim", "Park", "Lee"]
        ]
        for i in range(count):
            template = templates[i % len(templates)]
            title_text = template.format(topic=keyword_phrase)
            authors_group = author_pools[i % len(author_pools)]
            authors_list = [f"{name[0]}. {name}" for name in authors_group]
            ref = Reference(
                title=title_text,
                authors=authors_list,
                year=current_year - (i % 8) - 1,
                venue=venues[i % len(venues)],
                doi=f"10.{1000 + i}/{current_year - (i % 8)}.{1000 + i}",
                citation_count=max(10, 100 - i * 7)
            )
            generic_refs.append(ref)
        return generic_refs
    
    def _format_references(self, references: List[Reference]) -> str:
        formatted = []
        for i, ref in enumerate(references, 1):
            authors_str = ', '.join(ref.authors[:3]) + (' et al.' if len(ref.authors) > 3 else '')
            ref_str = f"[{i}] {authors_str}, \"{ref.title},\" {ref.venue}, {ref.year}."
            if ref.doi:
                ref_str += f" DOI: {ref.doi}"
            formatted.append(ref_str)
        return '\n'.join(formatted)
    
    def _generate_doi(self) -> str:
        year = datetime.now().year
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"10.1109/ACCESS.{year}.{unique_id}"
