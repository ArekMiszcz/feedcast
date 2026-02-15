"""Script Generator - generates podcast scripts using LLM."""

import re
import logging
from datetime import datetime

import requests

from .models import Speaker, Segment, PodcastScript
from .prompts import get_system_prompt, get_user_prompt
from ..scraper.models import Article
from ..config import LLMConfig, PodcastConfig

logger = logging.getLogger(__name__)


class ScriptGenerator:
    """Generates podcast scripts using local LLM (Ollama)."""
    
    def __init__(
        self, 
        llm_config: LLMConfig | None = None,
        podcast_config: PodcastConfig | None = None,
    ):
        self.llm_config = llm_config or LLMConfig()
        self.podcast_config = podcast_config or PodcastConfig()
    
    @property
    def language(self) -> str:
        return self.podcast_config.language
    
    def generate(self, articles: list[Article]) -> PodcastScript:
        """
        Generate a podcast script from articles using multi-step approach.
        
        Args:
            articles: List of articles to discuss.
        
        Returns:
            PodcastScript with dialogue segments.
        """
        logger.info(f"Generating script from {len(articles)} articles...")
        
        # Step 1: Format articles for prompt
        articles_text = self._format_articles(articles)
        
        # Step 2: Generate detailed script in multiple parts for longer output
        raw_script = self._generate_detailed_script(articles_text)
        
        # Step 3: Parse script into segments
        segments = self._parse_script(raw_script)
        
        script = PodcastScript(
            title=self._generate_title(articles),
            segments=segments,
            source_article_ids=[a.id for a in articles],
            language=self.language,
            generated_at=datetime.now(),
        )
        
        logger.info(f"Generated script with {len(segments)} segments")
        return script
    
    def _generate_detailed_script(self, articles_text: str) -> str:
        """Generate a detailed script, potentially in multiple LLM calls."""
        # First call - generate the main script
        main_script = self._call_llm(articles_text)
        logger.info(f"Initial script: {len(main_script)} characters")
        
        # Keep requesting continuations until we have enough content
        # 15000 chars ≈ 15-20 minutes of audio
        min_length = 15000
        max_continuations = 5
        continuation_count = 0
        
        while len(main_script) < min_length and continuation_count < max_continuations:
            continuation_count += 1
            logger.info(f"Script at {len(main_script)} chars (target: {min_length}), requesting continuation {continuation_count}/{max_continuations}...")
            continuation = self._call_llm_continuation(articles_text, main_script)
            if not continuation or len(continuation) < 300:
                logger.warning(f"Continuation too short ({len(continuation) if continuation else 0} chars), stopping")
                break
            main_script = main_script + "\n\n" + continuation
            logger.info(f"Total script length: {len(main_script)} characters")
        
        logger.info(f"Final script: {len(main_script)} characters after {continuation_count} continuations")
        return main_script
    
    def _call_llm_continuation(self, articles_text: str, existing_script: str) -> str:
        """Request continuation of the script."""
        # Get the last discussed topics to avoid repetition
        last_part = existing_script[-3000:] if len(existing_script) > 3000 else existing_script
        
        if self.language == "pl":
            continuation_prompt = f"""Jesteś scenarzystą podcastu technologicznego. Masz kontynuować poniższy scenariusz.

DOTYCHCZASOWA ROZMOWA (końcówka):
{last_part}

ARTYKUŁY DO WYKORZYSTANIA:
{articles_text[:20000]}

ZADANIE: Napisz KONTYNUACJĘ scenariusza. Omów KOLEJNE 4-5 nowych tematów z artykułów (innych niż już omówione).
- Pisz TYLKO dialogi [HOST] i [CO-HOST]
- Każdy temat: minimum 6 wymian dialogowych
- Szczegółowo wyjaśniaj każdy temat
- Używaj naturalnego języka polskiego
- Minimum 2000 znaków!

KONTYNUUJ:"""
        else:
            continuation_prompt = f"""You are a tech podcast scriptwriter. Continue the script below.

EXISTING SCRIPT (end):
{last_part}

Continue with 4-5 NEW topics from the articles. Use [HOST] and [CO-HOST] format. Minimum 2000 characters."""
        
        response = requests.post(
            f"{self.llm_config.base_url}/api/chat",
            json={
                "model": self.llm_config.model,
                "messages": [
                    {"role": "user", "content": continuation_prompt},
                ],
                "stream": False,
                "options": {
                    "temperature": self.llm_config.temperature,
                    "num_predict": self.llm_config.max_tokens,
                },
            },
            timeout=self.llm_config.timeout,
        )
        
        if response.status_code != 200:
            logger.warning(f"Continuation failed: {response.text}")
            return ""
        
        continuation = response.json()["message"]["content"]
        logger.info(f"Continuation generated: {len(continuation)} characters")
        return continuation

    def _format_articles(self, articles: list[Article], max_chars: int = 80000) -> str:
        """Format articles as text for LLM prompt."""
        lines = []
        total_chars = 0
        
        for article in articles:
            content = article.get_text()
            
            article_text = f"""
SOURCE: {article.source}
DATE: {article.published.strftime('%Y-%m-%d')}
TITLE: {article.title}
URL: {article.url}
CONTENT:
{content}
---"""
            
            if total_chars + len(article_text) > max_chars:
                break
            
            lines.append(article_text)
            total_chars += len(article_text)
        
        return "\n".join(lines)
    
    def _call_llm(self, articles_text: str) -> str:
        """Call Ollama API to generate script."""
        system_prompt = get_system_prompt(self.language)
        user_prompt = get_user_prompt(articles_text, self.language)
        
        logger.info(f"Calling LLM: {self.llm_config.model}")
        
        response = requests.post(
            f"{self.llm_config.base_url}/api/chat",
            json={
                "model": self.llm_config.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {
                    "temperature": self.llm_config.temperature,
                    "num_predict": self.llm_config.max_tokens,
                },
            },
            timeout=self.llm_config.timeout,
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Ollama API error: {response.text}")
        
        script = response.json()["message"]["content"]
        logger.info(f"LLM generated {len(script)} characters")
        logger.debug(f"Raw script preview: {script[:500]}...")
        
        return script
    
    def _parse_script(self, raw_script: str) -> list[Segment]:
        """Parse raw script text into Segment objects."""
        segments = []
        
        # Try multiple patterns - LLMs use different formats
        patterns = [
            # [HOST] or [CO-HOST] format
            (r'\[(HOST|CO-HOST)\]\s*(.+?)(?=\[(?:HOST|CO-HOST)\]|$)', {}),
            # **HOST:** or **CO-HOST:** format  
            (r'\*\*(HOST|CO-HOST)\*\*[:\s]+(.+?)(?=\*\*(?:HOST|CO-HOST)\*\*|$)', {}),
            # **Host (H):** or **Co-Host (C):** format (Qwen style)
            (r'\*\*(?:Host|HOST)\s*\([HC]\)\*?\*?[:\s]+(.+?)(?=\*\*(?:Host|Co-Host|HOST|CO-HOST)|$)', {"single": "HOST"}),
            (r'\*\*(?:Co-Host|CO-HOST)\s*\([HC]\)\*?\*?[:\s]+(.+?)(?=\*\*(?:Host|Co-Host|HOST|CO-HOST)|$)', {"single": "CO-HOST"}),
            # HOST: or CO-HOST: at line start
            (r'^(HOST|CO-HOST)[:\s]+(.+?)(?=^(?:HOST|CO-HOST)[:\s]|\Z)', {"multiline": True}),
            # H: or C: format
            (r'^([HC])[:\s]+(.+?)(?=^[HC][:\s]|\Z)', {"multiline": True, "short": True}),
        ]
        
        matches = []
        for pattern, opts in patterns:
            flags = re.DOTALL
            if opts.get("multiline"):
                flags |= re.MULTILINE
            
            found = re.findall(pattern, raw_script, flags)
            if found:
                if opts.get("single"):
                    # Single speaker pattern - convert to tuples
                    matches = [(opts["single"], text) for text in found]
                elif opts.get("short"):
                    # H/C format
                    matches = [("HOST" if s == "H" else "CO-HOST", text) for s, text in found]
                else:
                    matches = found
                logger.debug(f"Pattern matched: {pattern[:40]}... ({len(matches)} matches)")
                break
        
        if not matches:
            # Fallback: parse **Speaker:** format more loosely
            logger.warning("No speaker patterns found, attempting loose parsing")
            loose_pattern = r'\*\*([^*]+)\*\*[:\s]+(.+?)(?=\*\*[^*]+\*\*|\Z)'
            found = re.findall(loose_pattern, raw_script, re.DOTALL)
            
            for speaker_raw, text in found:
                speaker_lower = speaker_raw.lower()
                if 'host' in speaker_lower and 'co' not in speaker_lower:
                    matches.append(("HOST", text))
                elif 'co' in speaker_lower or 'guest' in speaker_lower:
                    matches.append(("CO-HOST", text))
        
        if not matches:
            # Last resort fallback
            logger.warning("Fallback: alternating speakers from paragraphs")
            lines = [l.strip() for l in raw_script.split('\n\n') if l.strip() and not l.startswith('#') and not l.startswith('*')]
            for i, line in enumerate(lines[:20]):
                speaker = Speaker.HOST if i % 2 == 0 else Speaker.CO_HOST
                segments.append(Segment(speaker=speaker, text=line))
            return segments
        
        for speaker_str, text in matches:
            speaker = Speaker.HOST if speaker_str == "HOST" else Speaker.CO_HOST
            clean_text = text.strip()
            # Remove markdown formatting artifacts
            clean_text = re.sub(r'\*\*\[.*?\]\*\*', '', clean_text).strip()
            clean_text = re.sub(r'\*\*', '', clean_text).strip()  # Remove leftover **
            clean_text = re.sub(r'^\*+\s*', '', clean_text).strip()  # Remove leading asterisks
            clean_text = re.sub(r'\s*\*+$', '', clean_text).strip()  # Remove trailing asterisks
            # Remove incomplete sentences like "Gościem specjalnym jest" at the end
            clean_text = re.sub(r'\s+(?:jest|to|są)\s*$', '.', clean_text)
            
            if clean_text and len(clean_text) > 10:  # Skip very short segments
                segments.append(Segment(speaker=speaker, text=clean_text))
        
        logger.debug(f"Parsed {len(segments)} segments from script")
        return segments
    
    def _generate_title(self, articles: list[Article]) -> str:
        """Generate a title for the podcast episode."""
        if articles:
            date_str = articles[0].published.strftime("%Y-%m-%d")
            return f"Tech Feed - {date_str}"
        return f"Tech Feed - {datetime.now().strftime('%Y-%m-%d')}"
