"""
Standalone script to evaluate saved papers and generate BLEU/ROUGE scores
Can be run independently without starting the Flask server
"""
import sys
import os
import json
import glob
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.evaluation_service import EvaluationService
from services.rag_service import RAGService

def main():
    """Main evaluation script"""
    print("=" * 80)
    print("PAPER EVALUATION - BLEU & ROUGE Score Generator")
    print("=" * 80)
    print()
    
    # Initialize services
    print("Initializing evaluation service...")
    try:
        eval_service = EvaluationService()
        rag_service = RAGService()
        print("✓ Services initialized successfully")
    except Exception as e:
        print(f"✗ Error initializing services: {e}")
        print("\nPlease install required packages:")
        print("  pip install nltk rouge-score")
        return
    
    print()
    
    # Find saved papers
    saved_papers_dir = os.path.join(os.getcwd(), 'saved_papers')
    paper_files = glob.glob(os.path.join(saved_papers_dir, 'paper_*.json'))
    
    if not paper_files:
        print(f"No papers found in {saved_papers_dir}")
        return
    
    # Get latest paper
    latest_paper = max(paper_files, key=os.path.getctime)
    print(f"Found {len(paper_files)} saved paper(s)")
    print(f"Evaluating latest: {os.path.basename(latest_paper)}")
    print()
    
    # Load paper
    with open(latest_paper, 'r', encoding='utf-8') as f:
        paper_data = json.load(f)
    
    print(f"Paper Title: {paper_data.get('title', 'Unknown')}")
    print(f"Generated: {paper_data.get('generated_at', 'Unknown')}")
    print()
    
    # Evaluate paper
    print("-" * 80)
    print("EVALUATING PAPER SECTIONS...")
    print("-" * 80)
    print()
    
    evaluation = eval_service.evaluate_paper(paper_data)
    
    if 'error' in evaluation:
        print(f"✗ Evaluation failed: {evaluation['error']}")
        return
    
    # Print results
    print_evaluation_results(evaluation)
    
    # Save evaluation report
    eval_filename = os.path.basename(latest_paper).replace('.json', '_evaluation.json')
    eval_filepath = os.path.join(saved_papers_dir, eval_filename)
    
    with open(eval_filepath, 'w', encoding='utf-8') as f:
        json.dump(evaluation, f, indent=4)
    
    print()
    print(f"✓ Evaluation report saved to: {eval_filepath}")
    
    # Generate text report
    text_report = eval_service.generate_report_text(evaluation)
    text_report_path = eval_filepath.replace('.json', '.txt')
    
    with open(text_report_path, 'w', encoding='utf-8') as f:
        f.write(text_report)
    
    print(f"✓ Text report saved to: {text_report_path}")
    print()
    
    # Offer to evaluate literature survey if available
    print("-" * 80)
    print("LITERATURE SURVEY EVALUATION")
    print("-" * 80)
    
    # Check if there's a survey in sections
    sections = paper_data.get('sections', {})
    if 'literature_review' in sections and sections['literature_review']:
        print("\nEvaluating Literature Review section...")
        
        # Get references
        references = paper_data.get('references', [])
        
        if references:
            survey_eval = eval_service.evaluate_literature_survey(
                sections['literature_review'],
                references
            )
            
            print_survey_evaluation(survey_eval)
            
            # Save survey evaluation
            survey_eval_path = eval_filepath.replace('_evaluation.json', '_survey_evaluation.json')
            with open(survey_eval_path, 'w', encoding='utf-8') as f:
                json.dump(survey_eval, f, indent=4)
            
            print(f"\n✓ Survey evaluation saved to: {survey_eval_path}")
        else:
            print("No reference papers available for survey evaluation")
    else:
        print("No literature review section found in paper")
    
    print()
    print("=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)

def print_evaluation_results(evaluation):
    """Print formatted evaluation results"""
    print("OVERALL SCORES")
    print("-" * 80)
    
    overall_bleu = evaluation['overall_scores']['bleu']
    overall_rouge = evaluation['overall_scores']['rouge']
    
    print("\nBLEU Scores:")
    print(f"  BLEU-1:  {overall_bleu['bleu-1']:.4f}")
    print(f"  BLEU-2:  {overall_bleu['bleu-2']:.4f}")
    print(f"  BLEU-3:  {overall_bleu['bleu-3']:.4f}")
    print(f"  BLEU-4:  {overall_bleu['bleu-4']:.4f}")
    print(f"  Average: {overall_bleu['bleu-avg']:.4f}")
    
    print("\nROUGE Scores:")
    for rouge_type in ['rouge-1', 'rouge-2', 'rouge-l']:
        r = overall_rouge[rouge_type]
        print(f"  {rouge_type.upper()}:")
        print(f"    Precision: {r['precision']:.4f}")
        print(f"    Recall:    {r['recall']:.4f}")
        print(f"    F1:        {r['f1']:.4f}")
    
    print()
    print("-" * 80)
    print("INTERPRETATION")
    print("-" * 80)
    
    interp = evaluation['interpretation']
    print(f"\nBLEU Quality: {interp['bleu_quality']}")
    print(f"  → {interp['bleu_note']}")
    print(f"\nROUGE Quality: {interp['rouge_quality']}")
    print(f"  → {interp['rouge_note']}")
    print(f"\nOverall: {interp['overall_assessment']}")
    
    print()
    print("-" * 80)
    print("SECTION-WISE SCORES")
    print("-" * 80)
    
    for section_name, section_eval in evaluation['section_evaluations'].items():
        print(f"\n{section_name.upper().replace('_', ' ')}:")
        print(f"  Words: {section_eval['word_count']}")
        print(f"  BLEU-Avg: {section_eval['bleu']['bleu-avg']:.4f}")
        print(f"  ROUGE-1 F1: {section_eval['rouge']['rouge-1']['f1']:.4f}")
        print(f"  ROUGE-2 F1: {section_eval['rouge']['rouge-2']['f1']:.4f}")
        print(f"  ROUGE-L F1: {section_eval['rouge']['rouge-l']['f1']:.4f}")

def print_survey_evaluation(survey_eval):
    """Print formatted survey evaluation"""
    print(f"\nWord Count: {survey_eval['word_count']}")
    print(f"Reference Papers: {survey_eval['reference_count']}")
    
    print("\nBLEU Scores:")
    bleu = survey_eval['bleu']
    print(f"  BLEU-1:  {bleu['bleu-1']:.4f}")
    print(f"  BLEU-2:  {bleu['bleu-2']:.4f}")
    print(f"  BLEU-3:  {bleu['bleu-3']:.4f}")
    print(f"  BLEU-4:  {bleu['bleu-4']:.4f}")
    print(f"  Average: {bleu['bleu-avg']:.4f}")
    
    print("\nROUGE Scores:")
    rouge = survey_eval['rouge']
    for rouge_type in ['rouge-1', 'rouge-2', 'rouge-l']:
        r = rouge[rouge_type]
        print(f"  {rouge_type.upper()}: P={r['precision']:.4f}, R={r['recall']:.4f}, F1={r['f1']:.4f}")
    
    print("\nInterpretation:")
    interp = survey_eval['interpretation']
    print(f"  {interp['overall_assessment']}")

if __name__ == '__main__':
    main()
