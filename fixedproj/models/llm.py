"""
LLM Interface with ALL FIXES APPLIED
- Fixed blank topic references
- Added input sanitization (security)
- Exponential backoff retry
- Configuration constants
- Proper error handling
"""
import requests
import time
import re
from typing import Optional, Dict, List
from config.settings import (
    OLLAMA_API_URL, MODEL_NAME, OLLAMA_TIMEOUT, MAX_RETRIES,
    TEMPERATURE_SETTINGS, WORD_COUNT_TARGET, ENFORCE_COMPLETE_SENTENCES
)

# Human-style writing guide to reduce AI detection
HUMAN_STYLE_GUIDE = """
STYLE GUIDELINES (CRITICAL):
1. VARIETY: Vary sentence length significantly. Mix short, punchy sentences with longer, complex ones.
2. VOCABULARY: Avoid these "AI buzzwords": delve, underscore, pivotal, realm, tapestry, landscape, leverage, intricate, multifaceted, paramount.
3. TONE: Write with a specific, opinionated academic voice. Avoid generic neutrality.
4. TRANSITIONS: Avoid robotic transitions like "Furthermore", "Moreover", "In conclusion". Use natural flow.
5. STRUCTURE: Do not use perfect symmetry in paragraphs. Make it feel organic.
"""

# Generation configuration constants
TOKEN_MULTIPLIER = 1.8
RETRY_BASE_DELAY = 2
RETRY_BACKOFF_FACTOR = 2
MIN_ABSTRACT_WORDS = 150
MAX_USER_DATA_CHARS = 10000

class LLMInterface:
    """Interface for interacting with Ollama LLM"""
    
    def __init__(self):
        self.api_url = OLLAMA_API_URL
        self.model = MODEL_NAME
    
    @staticmethod
    def _sanitize_user_input(text: str) -> str:
        """
        Sanitize user input to prevent prompt injection
        
        Args:
            text: Raw user input
            
        Returns:
            Sanitized text safe for prompt embedding
        """
        if not text:
            return text
        
        # Remove potential prompt injection patterns
        dangerous_patterns = [
            r'"""',  # Triple quotes
            r"'''",  # Triple single quotes
            r'CRITICAL:',  # Hijacking our instruction keywords
            r'REQUIREMENTS:',
            r'FORBIDDEN:',
            r'IGNORE PREVIOUS',
            r'IGNORE ALL',
            r'SYSTEM:',
            r'<\|im_start\|>',  # Common LLM control tokens
            r'<\|im_end\|>',
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Limit length to prevent token overflow
        if len(text) > MAX_USER_DATA_CHARS:
            text = text[:MAX_USER_DATA_CHARS] + "..."
        
        return text.strip()
    
    def generate(self, prompt: str, temperature: float = 0.7, 
                 max_tokens: int = 500, context: str = "") -> Optional[str]:
        """
        Generate text using Ollama with retry logic and exponential backoff
        
        Args:
            prompt: The generation prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            context: Additional context from RAG
            
        Returns:
            Generated text or None if failed
        """
        # Sanitize inputs
        prompt = self._sanitize_user_input(prompt)
        context = self._sanitize_user_input(context)
        
        # Build full prompt with context
        if context:
            full_prompt = f"""Context from research literature:
{context}

Based on the above research context, {prompt}

CRITICAL RULES:
1. Write ONLY plain text content - NO markdown formatting
2. NO headers with ### or ##
3. NO bold text with ** or *
4. NO bullet points or numbered lists
5. Write in continuous prose paragraphs only
6. End with a complete sentence (proper punctuation)
7. Use the research context to inform your writing
8. Be specific and avoid generic placeholder statements
9. Do NOT repeat the section title
10. Do NOT use asterisks or hashtags anywhere
11. NEVER leave blank placeholders - always use complete specific terms
12. When referring to topics, use the full specific subject name

{HUMAN_STYLE_GUIDE}"""
        else:
            full_prompt = f"""{prompt}

CRITICAL RULES:
1. Write ONLY plain text content - NO markdown formatting
2. NO headers with ### or ##
3. NO bold text with ** or *
4. NO bullet points or numbered lists
5. Write in continuous prose paragraphs only
6. End with a complete sentence (proper punctuation)
7. Be specific and avoid generic statements
8. Do NOT repeat the section title
9. Do NOT use asterisks or hashtags anywhere
10. NEVER leave blank placeholders - always use complete specific terms
11. When referring to topics, use the full specific subject name

{HUMAN_STYLE_GUIDE}"""
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    self.api_url,
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "top_p": 0.9,
                            "num_predict": max_tokens
                        }
                    },
                    timeout=OLLAMA_TIMEOUT
                )
                if response.status_code == 200:
                    result = response.json()
                    generated_text = result.get('response', '').strip()
                    
                    # Ensure complete sentences if enforced
                    if ENFORCE_COMPLETE_SENTENCES:
                        generated_text = self._ensure_complete_sentence(generated_text)
                    
                    return generated_text
                else:
                    print(f"[LLM] HTTP {response.status_code} on attempt {attempt + 1}")
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_BASE_DELAY * (RETRY_BACKOFF_FACTOR ** attempt)
                        time.sleep(delay)
                        
            except requests.exceptions.Timeout:
                print(f"[LLM] Timeout on attempt {attempt + 1}")
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (RETRY_BACKOFF_FACTOR ** attempt)
                    time.sleep(delay)
            except Exception as e:
                print(f"[LLM] Error: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (RETRY_BACKOFF_FACTOR ** attempt)
                    time.sleep(delay)
        
        return None
    
    def _ensure_complete_sentence(self, text: str) -> str:
        """Ensure text ends with complete sentence"""
        if not text:
            return text
        
        # Remove incomplete last sentence if doesn't end with punctuation
        if text[-1] not in '.!?':
            # Find last complete sentence
            sentences = text.split('.')
            if len(sentences) > 1:
                # Keep all but last incomplete sentence
                text = '.'.join(sentences[:-1]) + '.'
        
        return text.strip()
    
    # ==================== TITLE GENERATION ====================
    
    def generate_title(self, description: str) -> str:
        """Generate concise academic title from description"""
        description = self._sanitize_user_input(description)
        
        prompt = f"""Generate ONE concise academic research paper title from this description:

"{description}"

Requirements:
- Maximum 12 words
- Professional academic tone
- Capture core research focus
- No quotation marks or extra formatting
- Title case capitalization

Generate ONLY the title, nothing else."""

        result = self.generate(
            prompt,
            temperature=TEMPERATURE_SETTINGS["title"],
            max_tokens=60
        )
        
        if result:
            # Clean up the title
            title = result.replace('"', '').replace("'", "").strip()
            # Remove "Title:" prefix if present
            if title.lower().startswith('title:'):
                title = title[6:].strip()
            return title
        
        # Fallback: use first 10 words of description
        return ' '.join(description.split()[:10])
    
    # ==================== MULTIPLE TITLE GENERATION ====================

    def generate_title_options(self, description: str, count: int = 3) -> List[str]:
        """
        Generate multiple title options from description
        
        Args:
            description: Research description/brief
            count: Number of title options to generate (default 3)
            
        Returns:
            List of title strings
        """
        description = self._sanitize_user_input(description)
        
        prompt = f"""Generate {count} different concise academic research paper titles from this description:

    "{description}"

    Requirements for EACH title:
    - Maximum 18 words
    - MUST be a complete, standalone title that makes sense on its own
    - DO NOT end mid-sentence or with incomplete phrases like "directly on" or "involves deploying"
    - Professional academic tone
    - Capture core research focus clearly and completely
    - No quotation marks or extra formatting
    - Title case capitalization
    - Each title should emphasize a different aspect of the research

    Output format (exactly like this):
    1. [First Title]
    2. [Second Title]
    3. [Third Title]

    Generate ONLY the numbered list of titles, nothing else."""

        result = self.generate(
            prompt,
            temperature=0.8,  # Higher temperature for variety
            max_tokens=200
        )
        
        if result:
            # Parse the numbered list
            titles = []
            lines = result.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                # Match patterns like "1. Title" or "1) Title" or "1 - Title"
                if re.match(r'^[\d]+[\.\)\-\:]', line):
                    # Remove the number prefix
                    title = re.sub(r'^[\d]+[\.\)\-\:]\s*', '', line)
                    title = title.replace('"', '').replace("'", "").strip()
                    if title and len(titles) < count:
                        titles.append(title)
            
            # If parsing failed, try to split by newlines
            if len(titles) < count:
                titles = []
                for line in lines:
                    line = line.strip().replace('"', '').replace("'", "")
                    if line and not line.lower().startswith(('generate', 'title', 'output')):
                        # Remove number prefix if present
                        line = re.sub(r'^[\d]+[\.\)\-\:]\s*', '', line)
                        if line and len(titles) < count:
                            titles.append(line)
            
            # Ensure we have exactly 'count' titles
            while len(titles) < count:
                # Generate fallback titles
                words = description.split()
                if len(words) > 12:
                    titles.append(' '.join(words[:12]))
                else:
                    titles.append(description[:80])
            
            return titles[:count]
        
        # Complete fallback: generate simple variants
        words = description.split()
        fallback_titles = []
        fallback_titles.append(' '.join(words[:10]))
        fallback_titles.append(f"A Study on {' '.join(words[:7])}")
        fallback_titles.append(f"Research on {' '.join(words[:7])}")
        
        return fallback_titles[:count]

    
    # ==================== ABSTRACT GENERATION (FIXED - LONGER) ====================
    
    def generate_abstract(self, title: str, context: str = "") -> str:
        """
        Generate complete abstract (FIXED - 200-250 words, no blanks!)
        """
        title = self._sanitize_user_input(title)
        target_words = 220
        
        prompt = f"""Write a comprehensive {target_words}-word abstract for a research paper titled:
"{title}"

The abstract must cover these elements in order:

1. Background (3 sentences): 
   - Establish the research domain using specific terms from the title
   - Explain current challenges in "{title}" field
   - Why this research area matters

2. Research Gap (2 sentences):
   - What specific problem hasn't been solved
   - Limitations of existing approaches in this exact field

3. Objectives (2 sentences):
   - Clear statement of what this research achieves
   - Specific goals related to "{title}"

4. Methodology (3 sentences):
   - Approach and techniques used
   - Dataset or experimental setup
   - Key technical methods employed

5. Results (3 sentences):
   - Main quantitative findings with specific metrics
   - Performance improvements
   - Comparative results with baselines

6. Conclusion & Impact (2 sentences):
   - Significance of findings for "{title}" field
   - Broader implications and applications

CRITICAL REQUIREMENTS:
- MUST be {target_words} words (±10 words)
- MUST end with a complete sentence about impact
- Use past tense for completed work
- Include specific numerical results
- NO vague placeholders - always use the complete topic "{title}"
- When referring to the research area, use the full specific subject
- NEVER write "applications in" without specifying the application
- End with a strong concluding statement
- Output ONLY the abstract text. Do NOT start with "Here is...", "This paper...", "Abstract:", or any other introductory phrase.

Write the complete abstract now:"""

        result = self.generate(
            prompt,
            temperature=TEMPERATURE_SETTINGS["abstract"],
            max_tokens=400,
            context=context
        )
        
        if result:
            # Clean up common conversational prefixes
            cleaned = result.strip()
            # Remove "Here is the abstract..." type prefixes
            cleaned = re.sub(r'^(Here is|Sure,|Certainly,|I have generated|The following is).*?(abstract|paper|titled).*?:\s*', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
            # Remove "Abstract" or "Abstract-" prefix
            cleaned = re.sub(r'^(Abstract|Summary)[:\-\s]+', '', cleaned, flags=re.IGNORECASE)
            return cleaned
        
        return "Abstract generation failed."
    
    # ==================== SECTION GENERATION (FIXED WITH BETTER CONTEXT) ====================
    
    def generate_section(self, section_name: str, title: str, 
                        previous_sections: Dict[str, str],
                        rag_context: str = "",
                        user_data: Optional[str] = None) -> str:
        """
        Generate section with awareness of previous sections and user data
        
        Args:
            section_name: Name of section to generate
            title: Paper title
            previous_sections: Dict of already generated sections
            rag_context: RAG context from retrieved papers
            user_data: User-provided experimental data
        """
        # Sanitize all inputs
        title = self._sanitize_user_input(title)
        rag_context = self._sanitize_user_input(rag_context)
        if user_data:
            user_data = self._sanitize_user_input(user_data)
        
        target_words = WORD_COUNT_TARGET.get(section_name, 300)
        
        # Build enhanced context
        paper_context = self._build_paper_context(title, previous_sections)
        
        # Section-specific prompts
        prompts = {
            "introduction": self._prompt_introduction,
            "literature_review": self._prompt_literature_review,
            "methodology": self._prompt_methodology,
            "results": self._prompt_results,
            "discussion": self._prompt_discussion,
            "conclusion": self._prompt_conclusion
        }
        
        prompt_func = prompts.get(section_name)
        if not prompt_func:
            return f"[Section {section_name} not implemented]"
        
        prompt = prompt_func(title, target_words, paper_context, rag_context, user_data)
        
        result = self.generate(
            prompt,
            temperature=TEMPERATURE_SETTINGS.get(section_name, 0.7),
            max_tokens=int(target_words * TOKEN_MULTIPLIER),
            context=""  # Context already in prompt
        )
        
        return result if result else f"[{section_name.title()} generation failed]"
    
    def _build_paper_context(self, title: str, previous_sections: Dict[str, str]) -> str:
        """Build enhanced context summary from previous sections"""
        context_parts = [
            f"Paper Title: {title}",
            f"\nREMINDER: The research topic is '{title}'. When referring to the research area, application domain, or field of study, ALWAYS use this specific subject. Never leave it blank or use vague terms."
        ]
        
        if "abstract" in previous_sections:
            abstract_preview = ' '.join(previous_sections["abstract"].split()[:60])
            context_parts.append(f"\n\nAbstract (first 60 words): {abstract_preview}...")
        
        if "introduction" in previous_sections:
            intro_preview = ' '.join(previous_sections["introduction"].split()[:50])
            context_parts.append(f"\n\nIntroduction (preview): {intro_preview}...")
        
        return '\n'.join(context_parts)
    
    # ==================== SECTION-SPECIFIC PROMPTS (ALL FIXED) ====================
    
    def _prompt_introduction(self, title: str, word_count: int, 
                            paper_context: str, rag_context: str, user_data: Optional[str]) -> str:
        rag_section = f"Research literature context:\n{rag_context}\n" if rag_context else ""
        
        return f"""Write the Introduction section for this research paper:

        CITATION RULE: You MUST use IEEE style citations like [1], [2] when referring to the provided research context. Do NOT use (Author, Year).

{paper_context}

{rag_section}

Write a {word_count}-word Introduction that includes:

1. Opening Context (3-4 sentences):
   - Establish the broader research area of "{title}"
   - Explain why "{title}" is important
   - Current state of the field

2. Problem Statement (3 sentences):
   - Identify specific challenges in "{title}"
   - Explain limitations of existing approaches
   - Why this problem in "{title}" matters

3. Research Objectives (2 sentences):
   - Clear statement: "This research aims to..."
   - Specific goals related to "{title}"

4. Paper Organization (1 sentence):
   - Brief overview of remaining sections

REQUIREMENTS:
- Target {word_count} words (±30 acceptable)
- Use third person: "This research" not "My research"
- Reference the specific subject "{title}" - never leave it blank
- Be specific, not generic
- End with complete sentence about paper structure
- Use present tense for current state, past tense for previous work
- Write in plain text only, no formatting

Write the Introduction section now:"""

    def _prompt_literature_review(self, title: str, word_count: int,
                              paper_context: str, rag_context: str, user_data: Optional[str]) -> str:
        rag_section = rag_context if rag_context else f"Focus on general approaches in {title}."
        
        # ULTRA-EXPLICIT: Use actual topic in examples
        return f"""Write the Literature Review section for this research paper.

    THE RESEARCH TOPIC IS: {title}

    {paper_context}

    Research papers to review:
    {rag_section}

    ABSOLUTE REQUIREMENT - READ THIS CAREFULLY:
    Whenever you write about research work, you MUST write the complete phrase "{title}" after "on".
    
    CITATION RULE: You MUST use IEEE style citations like [1], [2] for EVERY paper discussed. Do NOT use (Author, Year).

    CORRECT EXAMPLES (using the actual topic "{title}"):
    ✓ "Recent work by Smith et al. [1] on {title} explores..."
    ✓ "The literature review on {title} provides..."
    ✓ "Research on {title} [2] has demonstrated..."
    ✓ "Studies on {title} have shown..."

    WRONG EXAMPLES (DO NOT DO THIS):
    ✗ "Recent work by Smith et al. on , explores..." ← FORBIDDEN
    ✗ "Research on provides..." ← FORBIDDEN  
    ✗ "Work on investigates..." ← FORBIDDEN

    Write a {word_count}-word Literature Review that includes:

    1. Overview (2 sentences):
    Start with: "The literature review on {title} provides..." or "Research on {title} encompasses..."

    2. Key Research Areas (4 paragraphs):
    For EACH paper, write: "Recent work by [Author Names] et al. on {title} explores [specific contribution]."
    Example: "Recent work by Johnson et al. on {title} explores adaptive learning mechanisms using reinforcement learning algorithms."

    3. Comparative Analysis (1 paragraph):
    Write: "Comparing different approaches in {title} research reveals..."

    4. Research Gaps (1 paragraph):
    Write: "Despite progress in {title} research, several gaps remain..."

    CRITICAL - COPY THESE EXACT PATTERNS:
    - "work on {title} explores"
    - "research on {title} demonstrates"  
    - "studies on {title} reveal"
    - "approaches to {title} include"

    DO NOT LEAVE "{title}" BLANK. Always write the full phrase: {title}

    Write the Literature Review now, using "{title}" in every reference to the research topic:"""


    def _prompt_methodology(self, title: str, word_count: int,
                       paper_context: str, rag_context: str, user_data: Optional[str]) -> str:
        user_section = ""
        if user_data:
            user_section = f"""

    USER-PROVIDED EXPERIMENTAL DETAILS (USE THESE EXACT DETAILS):
    {user_data}

    CRITICAL: Integrate ALL the user-provided details above. Use their specific numbers, tools, and procedures EXACTLY as given."""

        return f"""Write the Methodology section for this research paper.

    THE RESEARCH TOPIC IS: {title}

    {paper_context}{user_section}

    ABSOLUTE REQUIREMENT:
    The opening sentence MUST include the complete phrase "{title}".

    CORRECT OPENING EXAMPLES:
    ✓ "This research employed a computational approach to investigate {title} using machine learning techniques."
    ✓ "This study used Random Forest and Neural Networks to address challenges in {title}."
    ✓ "The methodology for studying {title} involved a mixed-methods approach combining quantitative and qualitative data."

    WRONG OPENING EXAMPLES (DO NOT DO THIS):
    ✗ "This research employed a computational approach to investigate ." ← FORBIDDEN
    ✗ "The study focused on using advanced techniques." ← MISSING TOPIC
    ✗ "We used machine learning for analysis." ← MISSING TOPIC

    Write a {word_count}-word Methodology section that includes:

    1. Research Design (2-3 sentences):
    MUST start with: "This research employed [approach type] to investigate {title} using [specific methods]."
   - Overall experimental approach for studying {title}
   - Type of study (experimental, computational, analytical, etc.)
   - Example good phrasing: "This research employed a computational approach to investigate {title} using blockchain technology..."
   - Example BAD phrasing: "This research employed a computational approach to investigate ." ← NEVER DO THIS

2. Data Collection (1-2 paragraphs):
   - Dataset description: name, source, size, characteristics
   - Data collection procedures for {title} research
   - Selection criteria or sampling method
   - Preprocessing steps applied

3. Methods and Techniques (2-3 paragraphs):
   - Specific algorithms/models/methods used for {title}
   - If user provided blockchain details (Hyperledger, consensus, nodes, etc.), include ALL of them
   - If user provided ML details (models, frameworks, parameters), include ALL of them
   - Technical implementation details with specific version numbers
   - Parameters and configurations (learning rate, batch size, epochs, consensus algorithm, etc.)
   - Tools and frameworks (TensorFlow, PyTorch, Hyperledger Fabric, AWS, etc.)
   - Architecture details (number of layers, nodes, organizations, peer nodes, orderer nodes, etc.)
   - Smart contracts or code implementation details if applicable

4. Evaluation Metrics (1 paragraph):
   - Metrics used: accuracy, precision, recall, F1-score, throughput, latency, etc.
   - Validation approach (cross-validation, train-test split, testing period)
   - Statistical analysis methods

CRITICAL REQUIREMENTS:
- Target {word_count} words (±50 acceptable)
- Be SPECIFIC with all technical details
- Use past tense: "The research used", "The model was trained", "The system was deployed"
- Include realistic technical specifications
- If user data provided, integrate it seamlessly and use ALL their details
- Always reference "{title}" as the application domain - NEVER leave it blank
- NO vague statements like "various techniques were used"
- NO incomplete references like "methodology for ." or "approach to ,"
- Write in plain text only, no markdown formatting
- Use third person: "This research used" NOT "We used"
- Include ALL user-provided details: specific tools, versions, parameters, dataset info, testing duration

Example of GOOD opening sentence:
"This research employed a permissioned blockchain architecture using Hyperledger Fabric to address {title} challenges..."

Example of BAD opening sentence:
"This research employed a computational approach to investigate ." ← FORBIDDEN

Write a detailed, specific Methodology section now:"""

    def _prompt_results(self, title: str, word_count: int,
                       paper_context: str, rag_context: str, user_data: Optional[str]) -> str:
        user_section = ""
        if user_data:
            user_section = f"""

USER-PROVIDED RESULTS:
{user_data}

IMPORTANT: Incorporate the user's actual results and metrics above. Use their specific numbers."""

        return f"""Write the Results section for this research paper on "{title}":

{paper_context}{user_section}

Write a {word_count}-word Results section that includes:

1. Overview (2 sentences):
   - Summary of results for "{title}" experiments
   - Structure of results section

2. Primary Results (3 paragraphs):
   - Present main quantitative findings clearly
   - Include specific metrics: accuracy X.X%, precision 0.XX, F1-score 0.XX
   - Reference "as shown in Table 1" and "illustrated in Figure 1"
   - Compare with baseline methods

3. Detailed Analysis (2 paragraphs):
   - Performance across different conditions
   - Statistical significance (p < 0.05)
   - Strengths and weaknesses observed
   
4. Comparative Results (1 paragraph):
   - How results compare to state-of-the-art in "{title}"
   - Percentage improvements over existing methods
   - Notable achievements

REQUIREMENTS:
- Target {word_count} words
- Use REALISTIC quantitative values (e.g., accuracy 92.4%, precision 0.91)
- Reference Table 1 and Figures 1-2
- Use past tense: "The model achieved", "Results showed"
- Be specific with numbers
- If user data provided, use their actual metrics
- Always specify the application: "{title}"
- NO vague statements like "good results were obtained"
- Write in plain text only, no formatting

Write the Results section with realistic metrics now:"""

    def _prompt_discussion(self, title: str, word_count: int,
                          paper_context: str, rag_context: str, user_data: Optional[str]) -> str:
        rag_section = f"Research context to compare against:\n{rag_context}\n" if rag_context else ""
        
        return f"""Write the Discussion section for this research paper on "{title}":

        CITATION RULE: Use IEEE style citations [1], [2] when comparing your results with previous work.

{paper_context}

{rag_section}

Write a {word_count}-word Discussion section that includes:

1. Interpretation (2 paragraphs):
   - Explain what the results mean for "{title}"
   - Why were these results obtained?
   - Connect results to research objectives

2. Comparison with Literature (2 paragraphs):
   - How do results compare to previous work on "{title}"?
   - Better/worse/similar performance and why?
   - What's novel about these findings in "{title}" research?

3. Implications (1 paragraph):
   - Practical implications for "{title}" applications
   - Theoretical contributions to the field
   - Significance to "{title}" domain

4. Limitations (1 paragraph):
   - Acknowledge limitations honestly
   - Factors affecting generalizability
   - Constraints of current approach to "{title}"

REQUIREMENTS:
- Target {word_count} words
- Be analytical and critical
- Reference the research literature provided
- Connect back to objectives from introduction
- Use present tense for interpretations, past tense for results
- Always specify the field: "{title}"
- Use third person: "This research demonstrates" not "My research"
- Be honest about limitations
- Write in plain text only, no formatting

Write the Discussion section now:"""

    def _prompt_conclusion(self, title: str, word_count: int,
                          paper_context: str, rag_context: str, user_data: Optional[str]) -> str:
        return f"""Write the Conclusion section for this research paper on "{title}":

{paper_context}

Write a {word_count}-word Conclusion section that includes:

   - Open questions in "{title}" to address

4. Closing Statement (1 sentence):
   - Broader impact on "{title}" field
   - End on a strong, forward-looking note

REQUIREMENTS:
- Target {word_count} words
- Be concise and impactful
- NO new information (only summarize)
- Use past tense for what was done
- Use future tense for future work
- Always reference the specific field: "{title}"
- Use third person: "This research" not "Our research"
- End with a complete, strong concluding sentence
- Write in plain text only, no formatting

Write the Conclusion section now:"""

    # ==================== UTILITY METHODS ====================
    
    def warmup(self) -> bool:
        """Warmup the model with a simple request"""
        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": "Test",
                    "stream": False,
                    "options": {"num_predict": 10}
                },
                timeout=30
            )
            return response.status_code == 200
        except:
            return False
