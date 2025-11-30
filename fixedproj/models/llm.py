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

CASUAL_STYLE_GUIDE = """
CRITICAL STYLE INSTRUCTIONS (THE "DRUNK" DRAFT):
1. **Role**: You are a cynical, burnt-out engineer writing a rant on your personal blog.
2. **Tone**: Aggressive, critical, opinionated, casual. Use slang.
3. **Structure**: Chaotic. Mix very short sentences with long rants.
4. **Content**: Cover all the technical points requested, but frame them as "why most people get this wrong" or "here's the ugly truth".
5. **Citations**: Keep the citations [1], [2] but you can be rude about them (e.g., "Smith [1] claims X, but that's garbage because...").
"""

FORMAL_STYLE_GUIDE = """
CRITICAL STYLE INSTRUCTIONS (THE "SOBER" EDIT):
1. **Role**: You are a strict editor for an IEEE transaction.
2. **Task**: Translate the text above into formal, high-quality academic English.
3. **Tone**: Professional, objective, precise.
4. **Structure**: Academic paragraphs.
5. **Preservation**:
   - KEEP all specific numbers, metrics, and data points.
   - KEEP all citations [1], [2] exactly where they are relevant.
   - KEEP the critical analysis/arguments (just phrase them politely).
   - DO NOT add fluff like "In conclusion" or "It is important to note".
"""

HUMAN_STYLE_GUIDE = """
CRITICAL HUMAN WRITING INSTRUCTIONS:
1. **NO ROBOTIC TRANSITIONS**: BANNED words: "Furthermore", "Moreover", "In conclusion", "Additionally", "Notably", "Importantly", "Consequently", "Thus", "Therefore". DO NOT USE THEM. Start sentences directly.
2. **NO AI BUZZWORDS**: BANNED words: "delve", "underscore", "pivotal", "realm", "tapestry", "landscape", "leverage", "intricate", "multifaceted", "paramount", "game-changer", "revolutionizing", "testament", "fostering", "nuances", "comprehensive", "exploration", "notable", "crucial", "vital", "significant", "enhance", "utilize", "facilitate", "optimize", "orchestrate", "synergy", "paradigm".
3. **BURSTINESS**: Write like a human. Some sentences should be 4 words. Others should be 25 words. Never write three sentences of the same length in a row.
4. **OPINIONATED TONE**: Don't be neutral. Be critical. Point out flaws. Use phrases like "Surprisingly," "Unfortunately," "In contrast," "However,".
5. **ACTIVE VOICE**: Use active voice. "Smith [1] argues..." NOT "It is argued by Smith [1]..."
6. **SYNTHESIS OVER SUMMARY**: Never summarize a paper in isolation. Always compare it to another. "While X did this, Y did that."
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
    
    def warmup(self) -> bool:
        """Warmup the LLM model to ensure it's loaded"""
        try:
            print(f"[LLM] Warming up model {self.model}...")
            result = self.generate(
                "Hello",
                max_tokens=5,
                style_guide=""
            )
            return result is not None
        except Exception as e:
            print(f"[LLM] Warmup failed: {e}")
            return False
    
    @staticmethod
    def _sanitize_user_input(text: str) -> str:
        """
        Sanitize user input to prevent prompt injection
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
                 max_tokens: int = 500, context: str = "",
                 style_guide: Optional[str] = None) -> Optional[str]:
        """
        Generate text using Ollama with retry logic and exponential backoff
        """
        # Sanitize inputs
        prompt = self._sanitize_user_input(prompt)
        context = self._sanitize_user_input(context)
        
        # Use provided style guide or default to HUMAN_STYLE_GUIDE
        current_style = style_guide if style_guide is not None else HUMAN_STYLE_GUIDE
        
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
7. Use the research context to inform your writing but SYNTHESIZE it, do not copy.
8. Be specific and avoid generic placeholder statements
9. Do NOT repeat the section title
10. Do NOT use asterisks or hashtags anywhere
11. NEVER leave blank placeholders - always use complete specific terms
12. When referring to topics, use the full specific subject name OR natural variations (e.g., "this field", "the domain").

{current_style}"""
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
11. When referring to topics, use the full specific subject name OR natural variations.

{current_style}"""
        
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
            max_tokens=60,
            style_guide="" # No style guide needed for title
        )
        
        if result:
            # Clean up the title
            title = result.replace('"', '').replace("'", "").strip()
            # Remove "Title:" prefix if present
            if title.lower().startswith('title:'):
                title = title[6:].strip()
            return title
    
    # ==================== MULTIPLE TITLE GENERATION ====================

    def generate_title_options(self, description: str, count: int = 3) -> List[str]:
        """
        Generate multiple title options from description
        """
        description = self._sanitize_user_input(description)
        
        # Request more titles than needed (buffer)
        buffer_count = count + 2
        
        prompt = f"""Task: Generate {buffer_count} concise academic research paper titles based on the description below.

    Description:
    "{description}"

    Constraints:
    1. Max 15 words per title.
    2. NO full sentences.
    3. NO "Title 1" or "Option 1" prefixes in the text (just the numbered list).
    4. Professional, academic style.

    Example Output:
    1. Deep Learning Approaches for Medical Imaging
    2. Novel Architectures in Convolutional Neural Networks
    3. Automated Disease Detection using AI

    Generate the numbered list of {buffer_count} titles now:"""

        result = self.generate(
            prompt,
            temperature=0.8,
            max_tokens=500,
            style_guide=""
        )
        
        titles = []
        if result:
            # Parse the numbered list
            lines = result.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                # Match patterns like "1. Title" or "1) Title" or "1 - Title"
                if re.match(r'^[\d]+[\.\)\-\:]', line):
                    # Remove the number prefix
                    title = re.sub(r'^[\d]+[\.\)\-\:]\s*', '', line)
                    title = title.replace('"', '').replace("'", "").strip()
                    
                    # Validation: Check length and sentence structure
                    if len(title.split()) > 25:
                        # Truncate if too long
                        title = ' '.join(title.split()[:20]) + "..."
                    
                    if title and len(titles) < count:
                        titles.append(title)
            
            # If parsing failed, try to split by newlines
            if len(titles) < count:
                for line in lines:
                    line = line.strip().replace('"', '').replace("'", "")
                    if line and not line.lower().startswith(('generate', 'title', 'output', 'task', 'description')):
                        # Remove number prefix if present
                        line = re.sub(r'^[\d]+[\.\)\-\:]\s*', '', line)
                        if line and len(titles) < count:
                            titles.append(line)
        
        # Smart Fallback: Extract keywords if we don't have enough titles
        if len(titles) < count:
            # Simple keyword extraction
            stopwords = {'the', 'a', 'an', 'in', 'on', 'for', 'to', 'of', 'and', 'using', 'with', 'this', 'paper', 'study', 'proposes', 'presents', 'we', 'is', 'are'}
            words = [w for w in description.split() if w.lower() not in stopwords and len(w) > 2]
            
            # Create variations
            while len(titles) < count:
                idx = len(titles)
                if idx == 0 and len(words) >= 4:
                    # Variation 1: First few keywords
                    titles.append(' '.join(words[:8]).title())
                elif idx == 1 and len(words) >= 6:
                    # Variation 2: Middle keywords or combination
                    titles.append(f"Research on {' '.join(words[:6])}".title())
                elif idx == 2:
                    # Variation 3: Analysis of...
                    titles.append(f"Analysis of {' '.join(words[:5])}".title())
                else:
                    # Last resort
                    titles.append(f"Research Paper Option {idx + 1}")
            
        return titles[:count]
    
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
            context=context,
            style_guide=""
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
    
    # ==================== SECTION GENERATION (UPDATED FOR STYLE TRANSFER) ====================
    
    def generate_section(self, section_name: str, title: str, 
                        previous_sections: Dict[str, str],
                        rag_context: str = "",
                        user_data: Optional[str] = None) -> str:
        """
        Generate section using "Write Drunk, Edit Sober" strategy.
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
        
        # Get the base content prompt
        base_prompt = prompt_func(title, target_words, paper_context, rag_context, user_data)
        
        # STEP 1: THE "DRUNK" DRAFT
        # We append the Casual Style Guide instructions to the prompt
        casual_draft = self.generate(
            base_prompt,
            temperature=0.9, # High temperature for creativity/burstiness
            max_tokens=int(target_words * TOKEN_MULTIPLIER),
            context="", # Context is already in base_prompt
            style_guide=CASUAL_STYLE_GUIDE
        )
        
        if not casual_draft:
            return f"[{section_name.title()} generation failed at Step 1]"
            
        # STEP 2: THE "SOBER" EDIT
        formal_prompt = f"""You are an expert academic editor.
        
        TASK: Rewrite the following "rough draft" into a formal, high-quality IEEE research paper section.
        
        ROUGH DRAFT:
        "{casual_draft}"
        
        REQUIREMENTS:
        - Maintain the unique arguments and critical perspective of the draft.
        - Fix the slang and casual tone to be professional and academic.
        - KEEP all citations [1], [2] and specific numbers/data.
        - Ensure varied sentence structures (burstiness).
        - Output ONLY the rewritten text.
        """
        
        formal_version = self.generate(
            formal_prompt,
            temperature=0.6, # Lower temperature for precision
            max_tokens=int(target_words * TOKEN_MULTIPLIER),
            style_guide=FORMAL_STYLE_GUIDE
        )
        
        if not formal_version:
            return casual_draft # Fallback to draft if formalization fails (better than nothing)
            
        # STEP 3: NUCLEAR FILTER (Safety Net)
        final_clean = self._force_remove_banned_words(formal_version)
        
        return final_clean

    def humanize_text(self, text: str, section_name: str) -> str:
        """
        Second pass to rewrite text to be more human-like.
        Forces burstiness and removes AI buzzwords.
        """
        # Don't humanize references or very short text
        if section_name == 'references' or len(text) < 100:
            return text
            
        prompt = f"""You are a strict, skeptical editor. Rewrite the following text to make it sound like a human wrote it.

    Original Text:
    "{text}"

    RULES:
    1. **Kill the Robot**: Remove all "AI-isms" like "delve", "landscape", "paramount", "tapestry".
    2. **Be Blunt**: Use active voice. Say "We tested X" instead of "X was tested".
    3. **Vary Length**: Write some very short sentences. (e.g. "This failed.")
    4. **No Fluff**: Remove "It is important to note that", "In conclusion", "Furthermore". Just say the point.
    5. **Keep Data**: Do not change any numbers, percentages, or citations [1].

    Rewrite it now:"""

        humanized = self.generate(
            prompt,
            temperature=0.85, 
            max_tokens=len(text.split()) * 3
        )
        
        return humanized if humanized else text

    def _force_remove_banned_words(self, text: str) -> str:
        """
        Python-side regex replacement for stubborn banned words.
        """
        replacements = {
            "delve into": "investigate",
            "delve": "investigate",
            "underscore": "highlight",
            "pivotal": "key",
            "realm": "field",
            "tapestry": "complex set",
            "landscape": "context",
            "leverage": "use",
            "intricate": "complex",
            "multifaceted": "complex",
            "paramount": "critical",
            "game-changer": "major advance",
            "revolutionizing": "transforming",
            "testament": "proof",
            "fostering": "encouraging",
            "nuances": "details",
            "comprehensive": "thorough",
            "exploration": "study",
            "notable": "key",
            "crucial": "critical",
            "vital": "important",
            "significant": "major",
            "enhance": "improve",
            "utilize": "use",
            "facilitate": "help",
            "optimize": "improve",
            "orchestrate": "manage",
            "synergy": "combination",
            "paradigm": "model",
            "furthermore,": "",
            "moreover,": "",
            "additionally,": "",
            "in conclusion,": "",
            "importantly,": "",
            "notably,": "",
            "consequently,": "so,",
            "thus,": "so,",
            "therefore,": "so,"
        }
        
        for word, replacement in replacements.items():
            # Case insensitive replacement
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            text = pattern.sub(replacement, text)
            
        # Clean up double spaces created by removals
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _build_paper_context(self, title: str, previous_sections: Dict[str, str]) -> str:
        """Build enhanced context summary from previous sections"""
        context_parts = [
            f"Paper Title: {title}",
            f"\nREMINDER: The research topic is '{title}'. When referring to the research area, application domain, or field of study, you can use the title or natural variations like 'this field', 'the domain', or 'such systems'."
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
        rag_section = rag_context if rag_context else f"Focus on general approaches in {title}."
        
        return f"""Write the Introduction section for this research paper.
    
    THE RESEARCH TOPIC IS: {title}

    {paper_context}

    Research papers to review:
    {rag_section}

    CITATION RULE: You MUST use IEEE style citations like [1], [2] for EVERY paper discussed. Do NOT use (Author, Year).

    Write a {word_count}-word Introduction that includes:

    1. Background (1 paragraph):
    Start broadly about the field and narrow down to the specific topic.
    
    2. Problem Statement (1 paragraph):
    Discuss the challenges and limitations of current approaches.

    3. Research Objectives (1 paragraph):
    State clearly what this paper aims to achieve.

    4. Significance (1 paragraph):
    Why is this research important?

    {HUMAN_STYLE_GUIDE}

    Write the Introduction now:"""

    def _prompt_literature_review(self, title: str, word_count: int, 
                                 paper_context: str, rag_context: str, user_data: Optional[str]) -> str:
        rag_section = rag_context if rag_context else f"Focus on general approaches in {title}."
        
        return f"""Write the Literature Review section for this research paper.

    THE RESEARCH TOPIC IS: {title}

    {HUMAN_STYLE_GUIDE}

    {paper_context}

    Research papers to review:
    {rag_section}
    
    CITATION RULE: You MUST use IEEE style citations like [1], [2] for EVERY paper discussed. Do NOT use (Author, Year).

    PLAGIARISM DEFENSE (CRITICAL):
    - Do NOT copy abstracts.
    - SYNTHESIZE findings: Group similar papers together (e.g., "Several studies [1], [3] have addressed...").
    - Do NOT start every sentence with "Recent work by..." or "Smith et al. proposed...". This is robotic.
    - Use varied sentence structures.

    Write a {word_count}-word Literature Review that includes:

    1. Overview (2 sentences):
    Briefly summarize the state of the field.

    2. Key Research Areas (4 paragraphs):
    Discuss the retrieved papers. Group them by theme or methodology if possible. 
    - Instead of listing them one by one, weave them into a narrative.
    - Compare and contrast their approaches.
    - Example: "While [1] focused on X, [2] argued that Y is more effective..."

    3. Comparative Analysis (1 paragraph):
    Compare the different approaches discussed.

    4. Research Gaps (1 paragraph):
    Identify what is missing in the current literature.

    Write the Literature Review now:"""
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

    Write a {word_count}-word Methodology section that includes:

    1. Research Design (2-3 sentences):
    Describe the overall experimental approach.
    
    2. Data Collection (1-2 paragraphs):
    - Dataset description: name, source, size, characteristics
    - Data collection procedures
    - Selection criteria or sampling method
    - Preprocessing steps applied

    3. Methods and Techniques (2-3 paragraphs):
    - Specific algorithms/models/methods used
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
    - Write in plain text only, no markdown formatting
    - Use third person: "This research used" NOT "We used"
    - Include ALL user-provided details: specific tools, versions, parameters, dataset info, testing duration

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
   - Summary of results
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
   - How results compare to state-of-the-art
   - Percentage improvements over existing methods
   - Notable achievements

REQUIREMENTS:
- Target {word_count} words
- Use REALISTIC quantitative values (e.g., accuracy 92.4%, precision 0.91)
- Reference Table 1 and Figures 1-2
- Use past tense: "The model achieved", "Results showed"
- Be specific with numbers
- If user data provided, use their actual metrics
- NO vague statements like "good results were obtained"
- Write in plain text only, no formatting

Write the Results section with realistic metrics now:"""

    def _prompt_discussion(self, title: str, word_count: int,
                          paper_context: str, rag_context: str, user_data: Optional[str]) -> str:
        rag_section = f"Research context to compare against:\n{rag_context}\n" if rag_context else ""
        
        return f"""Write the Discussion section for this research paper on "{title}":

{paper_context}
{rag_section}

Write a {word_count}-word Discussion section that includes:

1. Interpretation of Results (2 paragraphs):
   - What do the findings mean?
   - Do they support the initial hypothesis?
   - Explain WHY the results occurred (the underlying mechanisms)

2. Comparison with Literature (2 paragraphs):
   - Compare your findings with the papers in the context.
   - "Consistent with Smith [1], we found..." or "Contrary to Jones [2]..."

3. Limitations (1 paragraph):
   - Honest assessment of study limitations (e.g., dataset size, specific conditions)

4. Future Work (1 paragraph):
   - Suggest 2-3 specific directions for future research

REQUIREMENTS:
- Target {word_count} words
- Be analytical, not just descriptive
- Use citations [1], [2] when comparing
- Write in plain text only, no formatting

Write the Discussion section now:"""

    def _prompt_conclusion(self, title: str, word_count: int,
                          paper_context: str, rag_context: str, user_data: Optional[str]) -> str:
        return f"""Write the Conclusion section for this research paper on "{title}":

{paper_context}

Write a {word_count}-word Conclusion that includes:

1. Summary of Contributions (1 paragraph):
   - Restate the main problem and your solution
   - Highlight the key achievements

2. Key Findings (1 paragraph):
   - Recap the most important quantitative results
   - Emphasize the impact

3. Final Remarks (1 paragraph):
   - Broader implications for the field

REQUIREMENTS:
- Target {word_count} words
- No new citations
- Strong closing statement
- Write in plain text only, no formatting

Write the Conclusion now:"""
