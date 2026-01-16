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
   - REMOVE all fluff, redundancy, and filler words.
   - Make the text DENSE and information-rich found in top-tier IEEE papers.
   - SHORTEN the text if possible while keeping the core information.
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

CRITICAL FORMATTING RULES:
1. SUBSECTION HEADERS must be on their OWN LINE: "A. Problem Setup" (newline) then content.
2. BULLET POINTS (•) - each bullet on its OWN LINE with a line break before and after.
3. EQUATIONS inline: Attention = softmax(QK^T / sqrt(d)) * V
4. PSEUDOCODE as numbered steps (NO backticks ```):
   ALGORITHM BlockSparseAttention:
   1. Partition input into blocks
   2. Compute sparse attention
   3. Return weighted output
5. NO ASCII TABLES with |pipes| - use bullet comparisons instead:
   • Baseline: 28ms, 6GB
   • Proposed: 12ms, 3.6GB
6. EACH NEW ITEM ON ITS OWN LINE. Line breaks are critical.
7. Be DENSE and TECHNICAL.
8. Use IEEE citations [1], [2].

{current_style}"""
        else:
            full_prompt = f"""{prompt}

CRITICAL FORMATTING RULES:
1. SUBSECTION HEADERS on their OWN LINE.
2. BULLETS (•) on separate lines.
3. EQUATIONS inline. NO ASCII tables with |pipes|.
4. PSEUDOCODE as numbered steps, NO backticks.
5. EACH NEW ITEM = NEW LINE.
6. Be DENSE and TECHNICAL.

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

The abstract must cover these elements in flowing prose (NO bullets, NO numbered lists, NO subsections):

- Background: Establish the research domain and current challenges
- Research Gap: What problem hasn't been solved
- Objectives: What this research achieves
- Methodology: Approach and techniques used
- Results: Main quantitative findings with specific metrics
- Conclusion: Significance and implications

CRITICAL REQUIREMENTS:
- MUST be {target_words} words (±10 words)
- Write as CONTINUOUS FLOWING PARAGRAPHS - NO bullets, NO numbered lists, NO "A." "B." subsections
- MUST end with a complete sentence about impact
- Use past tense for completed work
- Include specific numerical results
- NO vague placeholders - always use the complete topic "{title}"
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
        - KEEP all mathematical formulas.
        - START paragraphs with bold headings like `<b>Key Insight:</b>` where appropriate.
        - CUT FLUFF: Remove "It is worth noting", "In conclusion", etc.
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
        
        # STEP 4: FORMAT STRUCTURED CONTENT (Insert line breaks)
        formatted = self._format_structured_content(final_clean)
        
        return formatted

    def _format_structured_content(self, text: str) -> str:
        """
        Post-process LLM output to:
        1. Fix character encoding issues (â€¢ → •, Â² → ², etc.)
        2. Remove triple backticks
        3. Insert line breaks before structural patterns
        """
        import re
        
        result = text
        
        # STEP 1: Fix common encoding issues (UTF-8 misinterpreted as Windows-1252)
        encoding_fixes = {
            'â€¢': '•',      # Bullet point
            'Â²': '²',       # Superscript 2
            'Â³': '³',       # Superscript 3
            'Ã©': 'é',       # e with acute
            'Ã¡': 'á',       # a with acute
            'Ã­': 'í',       # i with acute
            'Ã³': 'ó',       # o with acute
            'Ãº': 'ú',       # u with acute
            'Ã±': 'ñ',       # n with tilde
            'Ã¼': 'ü',       # u with umlaut
            'Ã¶': 'ö',       # o with umlaut
            'Ã¤': 'ä',       # a with umlaut
            'â€"': '—',      # Em dash
            'â€"': '–',      # En dash
            'â€™': "'",      # Right single quote
            'â€œ': '"',      # Left double quote
            'â€': '"',       # Right double quote (partial)
            '\\u2022': '•',  # Bullet (unicode escape)
        }
        
        for bad, good in encoding_fixes.items():
            result = result.replace(bad, good)
        
        # STEP 2: Remove triple backticks (code fences)
        result = re.sub(r'```\s*', '', result)
        result = re.sub(r'\s*```', '', result)
        
        # STEP 3: Insert line breaks before structural patterns
        # Only for sections that need subsections (Methodology, Results, Discussion)
        # NOT for abstract or introduction
        subsection_patterns = [
            r'(\w)\s+(A\.\s+\w)',      # A. subsection (after any word)
            r'(\w)\s+(B\.\s+\w)',      # B. subsection
            r'(\w)\s+(C\.\s+\w)',      # C. subsection
            r'(\w)\s+(D\.\s+\w)',      # D. subsection
            r'(\w)\s+(E\.\s+\w)',      # E. subsection
        ]
        
        for pattern in subsection_patterns:
            result = re.sub(pattern, r'\1\n\n\2', result)
        
        # STEP 3B: Handle bullet points more aggressively
        # Replace any bullet that comes after text (except at start of string)
        result = re.sub(r'(\S)\s*•\s*', r'\1\n\n• ', result)
        
        # Handle numbered lists (1. 2. 3.) - put on own lines
        # Must have word character before, then space, then digit+period
        result = re.sub(r'(\w)\s+(\d+)\.\s+', r'\1\n\n\2. ', result)
        
        # Algorithm headers
        result = re.sub(r'(\w)\s+(ALGORITHM)', r'\1\n\n\2', result)
        
        # STEP 3C: Put labels on their own lines
        labels = ['Key Insight:', 'Key Finding:', 'Key Observation:', 'Problem Statement:',
                  'Significance:', 'Objectives:', 'Methodology:', 'Conclusion:',
                  'Limitations:', 'Future Work:', 'Recommendations:', 'Summary:',
                  'Data Protection Concerns:', 'The Problem:', 'Need for Standardization:',
                  'Complexity of Existing Solutions:', 'Comparative Analysis:', 
                  'Research Gaps:', 'Critical Implications:']
        for label in labels:
            result = re.sub(rf'(\w)\s+({re.escape(label)})', rf'\1\n\n\2', result)
        
        # Put formulas on their own lines
        result = re.sub(r'(\w)\s*(Speedup\w*\s*=)', r'\1\n\n\2', result)
        result = re.sub(r'(\w)\s*(O\([^)]+\)\s*complexity)', r'\1\n\n\2', result, flags=re.IGNORECASE)
        
        # STEP 4: Clean up formatting artifacts
        result = re.sub(r'-{3,}', '', result)          # Remove dashes like ----
        result = re.sub(r'\*{2,}', '', result)         # Remove ** markdown bold
        result = re.sub(r'#{1,6}\s*', '', result)      # Remove markdown headers (###)
        
        # STEP 5: Remove LLM meta-commentary
        meta_patterns = [
            r'Note:\s*The above.*?(?:tone|content|format|style)\.?',
            r'Note:\s*This study.*?(?:tone|format)\.?',
            r'I have (?:maintained|preserved|kept).*?\.?',
            r'The (?:above|following) (?:rewritten )?text.*?\.?',
            r'\(as depicted in Figure \d+\)',  # Remove figure references since no figs
            r'See Figure \d+\.?',
        ]
        for pattern in meta_patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        result = re.sub(r'\n{3,}', '\n\n', result)     # Multiple newlines
        result = re.sub(r'  +', ' ', result)           # Multiple spaces
        
        return result.strip()

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

    CITATION RULE: Use IEEE style citations [1], [2] for papers discussed.

    STRUCTURE YOUR OUTPUT LIKE THIS:

    Start with 2-3 sentences of background context.
    
    Then discuss the problem. If mathematical, include the core equation:
    - Example: The standard attention has O(N²) complexity.
    
    State your objectives using bullets or a short list:
    • Objective 1
    • Objective 2
    
    End with the significance (2 sentences).

    REQUIREMENTS:
    - Target {word_count} words.
    - Be CONCISE and TECHNICAL.
    - Include at least one equation or complexity notation if applicable.
    - Use IEEE citations [1], [2].

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

    STRUCTURE YOUR OUTPUT EXACTLY LIKE THIS:

    A. Problem Formulation
    State the core mathematical problem. Include the key equation:
    - Example: mean = (1/N) * Σ a_i for all i
    
    B. Algorithm Design
    Describe the algorithm with PSEUDOCODE:
    
    function algorithm_name(input[]):
        initialization step
        for each element:
            processing step
        return result
    
    Explain the pseudocode briefly (2 sentences).
    
    C. Implementation Details
    Use BULLET POINTS for specifications:
    • Framework: (e.g., PyTorch 2.1, TensorFlow)
    • Hardware: (e.g., NVIDIA A100, 4 GPUs)
    • Dataset: (name, size, splits)
    • Hyperparameters: (learning rate, batch size, epochs)
    
    D. Experimental Protocol
    Describe the test procedure in 2-3 sentences.

    CRITICAL REQUIREMENTS:
    - Target {word_count} words total.
    - MANDATORY: Include at least 1 mathematical equation.
    - MANDATORY: Include pseudocode block.
    - MANDATORY: Include bullet list for specs.
    - Use subsection headers (A. B. C. D.).
    - If user provided data, use their EXACT values.
    - Be DENSE and TECHNICAL.

    Write the Methodology section now:"""

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

STRUCTURE YOUR OUTPUT EXACTLY LIKE THIS:

A. Key Findings
Start with a brief summary (2 sentences), then use BULLET POINTS:
• Finding 1: (specific metric, e.g., "2.4x speedup over baseline")
• Finding 2: (specific comparison)
• Finding 3: (statistical significance if applicable)

B. Performance Comparison
Use BULLETS for comparison (NO tables with |pipes|):
• Baseline: speed Xms, memory YMB
• Proposed: speed Xms, memory YMB
• Improvement: X% faster

C. Detailed Analysis
Discuss WHY these results occurred. Reference Figure 1 if applicable.
Include statistical significance: (p < 0.05).

D. Comparison with State-of-the-Art
Compare with methods from [1], [2]. Use specific numbers.

CRITICAL REQUIREMENTS:
- Target {word_count} words total.
- MANDATORY: Include bullet list of key findings.
- MANDATORY: Include comparison table.
- Use subsection headers (A. B. C. D.).
- If user provided data, use their EXACT values.
- Be SPECIFIC with numbers.

Write the Results section now:"""

    def _prompt_discussion(self, title: str, word_count: int,
                          paper_context: str, rag_context: str, user_data: Optional[str]) -> str:
        rag_section = f"Research context to compare against:\n{rag_context}\n" if rag_context else ""
        
        return f"""Write the Discussion section for this research paper on "{title}":

{paper_context}
{rag_section}

STRUCTURE YOUR OUTPUT LIKE THIS:

A. Interpretation of Results
Explain WHY the results occurred. If applicable, include an equation:
- Example: Speedup_max = 1 / (f + (1-f)/p) where f is serial fraction

B. Comparison with Literature
Compare with [1], [2]. Use specific metrics:
• Consistent with [1]: (specific finding)
• Different from [2]: (specific finding)

C. Limitations
Use bullets:
• Limitation 1
• Limitation 2

D. Future Directions
Suggest 2-3 specific improvements in brief bullet form.

REQUIREMENTS:
- Target {word_count} words.
- Use subsection headers (A. B. C. D.).
- Include equations where applicable.
- Use citations [1], [2].

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
