"""
Evaluation Service for Paper Quality Assessment
Calculates BLEU and ROUGE scores for generated paper sections
"""
import logging
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class EvaluationService:
    """Service for evaluating generated paper quality using BLEU and ROUGE metrics"""
    
    def __init__(self):
        """Initialize evaluation service with required libraries"""
        self._init_nltk()
        self._init_rouge()
        
    def _init_nltk(self):
        """Initialize NLTK for BLEU calculation"""
        try:
            import nltk
            from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
            
            # Download required data
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                logger.info("Downloading NLTK punkt tokenizer...")
                nltk.download('punkt', quiet=True)
            
            self.nltk = nltk
            self.sentence_bleu = sentence_bleu
            self.smoothing = SmoothingFunction()
            logger.info("✓ NLTK initialized for BLEU scoring")
        except ImportError:
            logger.error("NLTK not installed. Install with: pip install nltk")
            raise
    
    def _init_rouge(self):
        """Initialize ROUGE scorer"""
        try:
            from rouge_score import rouge_scorer
            self.rouge_scorer = rouge_scorer.RougeScorer(
                ['rouge1', 'rouge2', 'rougeL'], 
                use_stemmer=True
            )
            logger.info("✓ ROUGE scorer initialized")
        except ImportError:
            logger.error("rouge-score not installed. Install with: pip install rouge-score")
            raise
    
    def tokenize_text(self, text: str) -> List[str]:
        """Tokenize text for BLEU calculation"""
        # Clean and normalize
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        
        # Tokenize
        tokens = self.nltk.word_tokenize(text)
        return tokens
    
    def calculate_bleu(self, candidate: str, references: List[str]) -> Dict[str, float]:
        """
        Calculate BLEU scores for candidate text against reference texts
        
        Args:
            candidate: Generated text to evaluate
            references: List of reference texts
            
        Returns:
            Dictionary with BLEU-1, BLEU-2, BLEU-3, BLEU-4 scores
        """
        if not candidate or not references:
            return {
                'bleu-1': 0.0,
                'bleu-2': 0.0,
                'bleu-3': 0.0,
                'bleu-4': 0.0,
                'bleu-avg': 0.0
            }
        
        # Tokenize
        candidate_tokens = self.tokenize_text(candidate)
        reference_tokens_list = [self.tokenize_text(ref) for ref in references]
        
        # Calculate BLEU scores with different n-gram weights
        bleu_1 = self.sentence_bleu(
            reference_tokens_list, 
            candidate_tokens,
            weights=(1, 0, 0, 0),
            smoothing_function=self.smoothing.method1
        )
        
        bleu_2 = self.sentence_bleu(
            reference_tokens_list,
            candidate_tokens,
            weights=(0.5, 0.5, 0, 0),
            smoothing_function=self.smoothing.method1
        )
        
        bleu_3 = self.sentence_bleu(
            reference_tokens_list,
            candidate_tokens,
            weights=(0.33, 0.33, 0.33, 0),
            smoothing_function=self.smoothing.method1
        )
        
        bleu_4 = self.sentence_bleu(
            reference_tokens_list,
            candidate_tokens,
            weights=(0.25, 0.25, 0.25, 0.25),
            smoothing_function=self.smoothing.method1
        )
        
        bleu_avg = (bleu_1 + bleu_2 + bleu_3 + bleu_4) / 4
        
        return {
            'bleu-1': round(bleu_1, 4),
            'bleu-2': round(bleu_2, 4),
            'bleu-3': round(bleu_3, 4),
            'bleu-4': round(bleu_4, 4),
            'bleu-avg': round(bleu_avg, 4)
        }
    
    def calculate_rouge(self, candidate: str, references: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Calculate ROUGE scores for candidate text against reference texts
        
        Args:
            candidate: Generated text to evaluate
            references: List of reference texts
            
        Returns:
            Dictionary with ROUGE-1, ROUGE-2, ROUGE-L scores (precision, recall, f1)
        """
        if not candidate or not references:
            return {
                'rouge-1': {'precision': 0.0, 'recall': 0.0, 'f1': 0.0},
                'rouge-2': {'precision': 0.0, 'recall': 0.0, 'f1': 0.0},
                'rouge-l': {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
            }
        
        # Calculate ROUGE against each reference and take the maximum
        all_scores = {
            'rouge1': {'precision': [], 'recall': [], 'fmeasure': []},
            'rouge2': {'precision': [], 'recall': [], 'fmeasure': []},
            'rougeL': {'precision': [], 'recall': [], 'fmeasure': []}
        }
        
        for reference in references:
            scores = self.rouge_scorer.score(reference, candidate)
            
            for metric in ['rouge1', 'rouge2', 'rougeL']:
                all_scores[metric]['precision'].append(scores[metric].precision)
                all_scores[metric]['recall'].append(scores[metric].recall)
                all_scores[metric]['fmeasure'].append(scores[metric].fmeasure)
        
        # Take maximum scores across all references
        result = {
            'rouge-1': {
                'precision': round(max(all_scores['rouge1']['precision']), 4),
                'recall': round(max(all_scores['rouge1']['recall']), 4),
                'f1': round(max(all_scores['rouge1']['fmeasure']), 4)
            },
            'rouge-2': {
                'precision': round(max(all_scores['rouge2']['precision']), 4),
                'recall': round(max(all_scores['rouge2']['recall']), 4),
                'f1': round(max(all_scores['rouge2']['fmeasure']), 4)
            },
            'rouge-l': {
                'precision': round(max(all_scores['rougeL']['precision']), 4),
                'recall': round(max(all_scores['rougeL']['recall']), 4),
                'f1': round(max(all_scores['rougeL']['fmeasure']), 4)
            }
        }
        
        return result
    
    def extract_reference_texts(self, references: List[Dict]) -> List[str]:
        """
        Extract text content from reference papers
        
        Args:
            references: List of reference paper dictionaries
            
        Returns:
            List of reference text strings
        """
        reference_texts = []
        
        for ref in references:
            # Combine title and abstract if available
            text_parts = []
            
            if isinstance(ref, dict):
                if ref.get('title'):
                    text_parts.append(ref['title'])
                if ref.get('abstract'):
                    text_parts.append(ref['abstract'])
            
            if text_parts:
                reference_texts.append(' '.join(text_parts))
        
        return reference_texts
    
    def evaluate_section(self, section_content: str, reference_texts: List[str], 
                        section_name: str) -> Dict:
        """
        Evaluate a single paper section
        
        Args:
            section_content: Generated section text
            reference_texts: List of reference texts for comparison
            section_name: Name of the section
            
        Returns:
            Dictionary with BLEU and ROUGE scores
        """
        logger.info(f"Evaluating section: {section_name}")
        
        # Calculate scores
        bleu_scores = self.calculate_bleu(section_content, reference_texts)
        rouge_scores = self.calculate_rouge(section_content, reference_texts)
        
        # Calculate word count
        word_count = len(section_content.split())
        
        return {
            'section_name': section_name,
            'word_count': word_count,
            'bleu': bleu_scores,
            'rouge': rouge_scores,
            'reference_count': len(reference_texts)
        }
    
    def evaluate_paper(self, paper_data: Dict, reference_papers: Optional[List[Dict]] = None) -> Dict:
        """
        Evaluate entire research paper
        
        Args:
            paper_data: Paper dictionary with sections
            reference_papers: Optional list of reference papers (if not in paper_data)
            
        Returns:
            Comprehensive evaluation report
        """
        logger.info(f"Evaluating paper: {paper_data.get('title', 'Unknown')[:50]}...")
        
        # Extract reference texts
        if reference_papers:
            reference_texts = self.extract_reference_texts(reference_papers)
        else:
            # Try to get from paper's references
            refs = paper_data.get('references', [])
            reference_texts = self.extract_reference_texts(refs)
        
        if not reference_texts:
            logger.warning("No reference texts available for evaluation")
            return {
                'error': 'No reference texts available',
                'paper_title': paper_data.get('title', 'Unknown')
            }
        
        logger.info(f"Using {len(reference_texts)} reference texts for evaluation")
        
        # Evaluate each section
        section_evaluations = {}
        sections = paper_data.get('sections', {})
        
        # Sections to evaluate (exclude references)
        evaluable_sections = ['introduction', 'literature_review', 'methodology', 
                             'results', 'discussion', 'conclusion']
        
        for section_name in evaluable_sections:
            if section_name in sections and sections[section_name]:
                section_eval = self.evaluate_section(
                    sections[section_name],
                    reference_texts,
                    section_name
                )
                section_evaluations[section_name] = section_eval
        
        # Evaluate abstract separately
        if paper_data.get('abstract'):
            abstract_eval = self.evaluate_section(
                paper_data['abstract'],
                reference_texts,
                'abstract'
            )
            section_evaluations['abstract'] = abstract_eval
        
        # Calculate overall scores
        overall_bleu = self._calculate_overall_bleu(section_evaluations)
        overall_rouge = self._calculate_overall_rouge(section_evaluations)
        
        # Generate interpretation
        interpretation = self._interpret_scores(overall_bleu, overall_rouge)
        
        report = {
            'paper_title': paper_data.get('title', 'Unknown'),
            'evaluated_at': datetime.now().isoformat(),
            'reference_count': len(reference_texts),
            'section_evaluations': section_evaluations,
            'overall_scores': {
                'bleu': overall_bleu,
                'rouge': overall_rouge
            },
            'interpretation': interpretation,
            'total_sections_evaluated': len(section_evaluations)
        }
        
        logger.info(f"✓ Evaluation complete - Overall BLEU: {overall_bleu['bleu-avg']:.4f}, ROUGE-L F1: {overall_rouge['rouge-l']['f1']:.4f}")
        
        return report
    
    def evaluate_literature_survey(self, survey_text: str, reference_papers: List[Dict]) -> Dict:
        """
        Evaluate literature survey quality
        
        Args:
            survey_text: Generated literature survey text
            reference_papers: List of papers used for the survey
            
        Returns:
            Evaluation report for the survey
        """
        logger.info("Evaluating literature survey...")
        
        # Extract reference texts
        reference_texts = self.extract_reference_texts(reference_papers)
        
        if not reference_texts:
            return {
                'error': 'No reference texts available',
                'survey_length': len(survey_text.split())
            }
        
        # Calculate scores
        bleu_scores = self.calculate_bleu(survey_text, reference_texts)
        rouge_scores = self.calculate_rouge(survey_text, reference_texts)
        
        # Word count
        word_count = len(survey_text.split())
        
        # Interpretation
        interpretation = self._interpret_scores(bleu_scores, rouge_scores)
        
        report = {
            'type': 'literature_survey',
            'evaluated_at': datetime.now().isoformat(),
            'word_count': word_count,
            'reference_count': len(reference_texts),
            'bleu': bleu_scores,
            'rouge': rouge_scores,
            'interpretation': interpretation
        }
        
        logger.info(f"✓ Survey evaluation complete - BLEU: {bleu_scores['bleu-avg']:.4f}, ROUGE-L F1: {rouge_scores['rouge-l']['f1']:.4f}")
        
        return report
    
    def _calculate_overall_bleu(self, section_evaluations: Dict) -> Dict[str, float]:
        """Calculate average BLEU scores across all sections"""
        if not section_evaluations:
            return {'bleu-1': 0.0, 'bleu-2': 0.0, 'bleu-3': 0.0, 'bleu-4': 0.0, 'bleu-avg': 0.0}
        
        bleu_keys = ['bleu-1', 'bleu-2', 'bleu-3', 'bleu-4', 'bleu-avg']
        overall = {key: 0.0 for key in bleu_keys}
        
        for section_eval in section_evaluations.values():
            for key in bleu_keys:
                overall[key] += section_eval['bleu'][key]
        
        count = len(section_evaluations)
        for key in bleu_keys:
            overall[key] = round(overall[key] / count, 4)
        
        return overall
    
    def _calculate_overall_rouge(self, section_evaluations: Dict) -> Dict:
        """Calculate average ROUGE scores across all sections"""
        if not section_evaluations:
            return {
                'rouge-1': {'precision': 0.0, 'recall': 0.0, 'f1': 0.0},
                'rouge-2': {'precision': 0.0, 'recall': 0.0, 'f1': 0.0},
                'rouge-l': {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
            }
        
        rouge_types = ['rouge-1', 'rouge-2', 'rouge-l']
        metrics = ['precision', 'recall', 'f1']
        
        overall = {rt: {m: 0.0 for m in metrics} for rt in rouge_types}
        
        for section_eval in section_evaluations.values():
            for rouge_type in rouge_types:
                for metric in metrics:
                    overall[rouge_type][metric] += section_eval['rouge'][rouge_type][metric]
        
        count = len(section_evaluations)
        for rouge_type in rouge_types:
            for metric in metrics:
                overall[rouge_type][metric] = round(overall[rouge_type][metric] / count, 4)
        
        return overall
    
    def _interpret_scores(self, bleu_scores: Dict, rouge_scores: Dict) -> Dict[str, str]:
        """
        Interpret BLEU and ROUGE scores with quality assessment
        
        Returns:
            Dictionary with interpretations
        """
        bleu_avg = bleu_scores.get('bleu-avg', 0)
        rouge_f1 = rouge_scores.get('rouge-l', {}).get('f1', 0)
        
        # BLEU interpretation
        if bleu_avg >= 0.2:
            bleu_quality = "High"
            bleu_note = "Strong similarity to references (Check for plagiarism)"
        elif bleu_avg >= 0.1:
            bleu_quality = "Good"
            bleu_note = "Good synthesis of reference terminology"
        elif bleu_avg >= 0.04:
            bleu_quality = "Normal"
            bleu_note = "Original synthesis with appropriate technical terms"
        else:
            bleu_quality = "Low"
            bleu_note = "Minimal connection to source material (Too creative?)"
        
        # ROUGE interpretation
        if rouge_f1 >= 0.2:
            rouge_quality = "High"
            rouge_note = "Extensive coverage of reference content"
        elif rouge_f1 >= 0.1:
            rouge_quality = "Good"
            rouge_note = "Good conceptual alignment with sources"
        elif rouge_f1 >= 0.05:
            rouge_quality = "Normal"
            rouge_note = "Original writing covering key concepts"
        else:
            rouge_quality = "Low"
            rouge_note = "Limited overlap with reference content"
        
        # Overall assessment
        avg_score = (bleu_avg + rouge_f1) / 2
        if avg_score >= 0.15:
            overall = "High Fidelity - Strongly grounded in references"
        elif avg_score >= 0.05:
            overall = "Original Research - Good synthesis of sources"
        else:
            overall = "Creative/Novel - Low direct overlap with references"
        
        return {
            'bleu_quality': bleu_quality,
            'bleu_note': bleu_note,
            'rouge_quality': rouge_quality,
            'rouge_note': rouge_note,
            'overall_assessment': overall,
            'bleu_score': bleu_avg,
            'rouge_score': rouge_f1
        }
    
    def generate_report_text(self, evaluation: Dict) -> str:
        """
        Generate human-readable evaluation report
        
        Args:
            evaluation: Evaluation dictionary from evaluate_paper or evaluate_literature_survey
            
        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("PAPER QUALITY EVALUATION REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        if 'paper_title' in evaluation:
            lines.append(f"Paper: {evaluation['paper_title']}")
        lines.append(f"Evaluated: {evaluation.get('evaluated_at', 'Unknown')}")
        lines.append(f"Reference Papers: {evaluation.get('reference_count', 0)}")
        lines.append("")
        
        # Overall scores
        if 'overall_scores' in evaluation:
            lines.append("-" * 80)
            lines.append("OVERALL SCORES")
            lines.append("-" * 80)
            
            bleu = evaluation['overall_scores']['bleu']
            lines.append(f"\nBLEU Scores:")
            lines.append(f"  BLEU-1: {bleu['bleu-1']:.4f}")
            lines.append(f"  BLEU-2: {bleu['bleu-2']:.4f}")
            lines.append(f"  BLEU-3: {bleu['bleu-3']:.4f}")
            lines.append(f"  BLEU-4: {bleu['bleu-4']:.4f}")
            lines.append(f"  Average: {bleu['bleu-avg']:.4f}")
            
            rouge = evaluation['overall_scores']['rouge']
            lines.append(f"\nROUGE Scores:")
            for rouge_type in ['rouge-1', 'rouge-2', 'rouge-l']:
                r = rouge[rouge_type]
                lines.append(f"  {rouge_type.upper()}:")
                lines.append(f"    Precision: {r['precision']:.4f}")
                lines.append(f"    Recall:    {r['recall']:.4f}")
                lines.append(f"    F1:        {r['f1']:.4f}")
        
        # Interpretation
        if 'interpretation' in evaluation:
            lines.append("")
            lines.append("-" * 80)
            lines.append("INTERPRETATION")
            lines.append("-" * 80)
            interp = evaluation['interpretation']
            lines.append(f"\nBLEU Quality: {interp['bleu_quality']}")
            lines.append(f"  {interp['bleu_note']}")
            lines.append(f"\nROUGE Quality: {interp['rouge_quality']}")
            lines.append(f"  {interp['rouge_note']}")
            lines.append(f"\nOverall Assessment: {interp['overall_assessment']}")
        
        # Section-wise scores
        if 'section_evaluations' in evaluation:
            lines.append("")
            lines.append("-" * 80)
            lines.append("SECTION-WISE EVALUATION")
            lines.append("-" * 80)
            
            for section_name, section_eval in evaluation['section_evaluations'].items():
                lines.append(f"\n{section_name.upper().replace('_', ' ')}:")
                lines.append(f"  Words: {section_eval['word_count']}")
                lines.append(f"  BLEU-Avg: {section_eval['bleu']['bleu-avg']:.4f}")
                lines.append(f"  ROUGE-L F1: {section_eval['rouge']['rouge-l']['f1']:.4f}")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
