"""LLM-enhanced text normalizer for TTS.

Combines static dictionary for known terms with LLM for unknown English words.
"""

import re
import logging
from functools import lru_cache
from typing import Optional

import requests

from .text_normalizer import POLISH_PRONUNCIATIONS, normalize_text_for_tts

logger = logging.getLogger(__name__)

# Regex to detect English words (ASCII letters, common patterns)
ENGLISH_WORD_PATTERN = re.compile(
    r'\b[A-Za-z]+(?:\.[A-Za-z]+)*\b'  # Words with optional dots (Node.js)
)

# Words that are the same in Polish or don't need conversion
SKIP_WORDS = {
    # Polish words that look English
    "to", "i", "w", "z", "a", "o", "na", "do", "jest", "co", "jak", "tak",
    "nie", "ale", "czy", "po", "za", "od", "przy", "dla", "bez", "przez",
    "mamy", "mam", "ma", "są", "jest", "być", "był", "była", "było",
    "problem", "problemy", "problemem", "problemu",  # Polish word!
    "potrzebujemy", "potrzebuje", "czekam", "czeka", "czekamy",
    "zrobiłem", "zrobił", "zrobiła", "zrobili",
    "używa", "używamy", "używają",
    # Common words that TTS handles well
    "ok", "super", "fajne", "mega", "ekstra",
    # Articles, prepositions (often in mixed text)
    "the", "a", "an", "of", "for", "in", "on", "at", "to", "is", "it",
    "and", "or", "but", "if", "then", "else", "with", "from", "by",
    # Common tech words that sound OK in Polish TTS
    "code", "test", "data", "info", "demo", "beta", "alfa", "delta",
    "open", "close", "start", "stop", "run", "get", "set", "put", "post",
}

# Cache for LLM responses to avoid repeated calls
_pronunciation_cache: dict[str, str] = {}


class LLMTextNormalizer:
    """Text normalizer that uses LLM for unknown English terms."""
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5:14b-instruct",  # Good balance of quality/speed
        use_llm: bool = True,
        timeout: int = 10,
    ):
        """
        Initialize LLM text normalizer.
        
        Args:
            ollama_url: Ollama API URL.
            model: Small LLM model for pronunciation conversion.
            use_llm: Whether to use LLM for unknown words (can disable for speed).
            timeout: Request timeout in seconds.
        """
        self.ollama_url = ollama_url
        self.model = model
        self.use_llm = use_llm
        self.timeout = timeout
        self._llm_available: Optional[bool] = None
    
    def _check_llm_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        if self._llm_available is not None:
            return self._llm_available
        
        try:
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=5
            )
            if response.ok:
                models = [m["name"] for m in response.json().get("models", [])]
                # Check if model or base model name is available
                base_model = self.model.split(":")[0]
                self._llm_available = any(
                    self.model in m or base_model in m for m in models
                )
                if not self._llm_available:
                    logger.warning(f"Model {self.model} not found in Ollama. Available: {models[:5]}")
            else:
                self._llm_available = False
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            self._llm_available = False
        
        return self._llm_available
    
    def _get_pronunciation_from_llm(self, word: str) -> Optional[str]:
        """Get Polish phonetic pronunciation from LLM."""
        if word.lower() in _pronunciation_cache:
            return _pronunciation_cache[word.lower()]
        
        if not self._check_llm_available():
            return None
        
        prompt = f"""Zamień angielskie słowo/wyrażenie na polską wymowę fonetyczną.

ZASADY:
- Pisz JAK POLAK BY PRZECZYTAŁ to słowo
- Używaj TYLKO polskich liter (ą,ę,ć,ł,ń,ó,ś,ź,ż,sz,cz,dż,dź)
- Rozdzielaj sylaby spacjami
- Odpowiedz TYLKO wymową, bez wyjaśnień

PRZYKŁADY:
JavaScript → dżawa skrypt
Python → paj ton  
GitHub → git hab
Docker → do ker
Kubernetes → ku ber ne tis
repository → re po zy to ri
deployment → di ploj ment
pull request → pul ri kłest
feature → fi czer
branch → brancz
staging → stej dżing
backend → bek end
middleware → mid l łer
authentication → o ten ty fi kej szyn
refactoring → ri fak to ring
legacy → le ga si
cache → kesz
debug → di bag

Słowo: {word}
Wymowa:"""

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low for consistency
                        "num_predict": 50,   # Short response
                    }
                },
                timeout=self.timeout
            )
            
            if response.ok:
                result = response.json().get("response", "").strip()
                # Clean up response - take first line, remove quotes
                result = result.split("\n")[0].strip().strip('"\'')
                
                # Validate - should be mostly Polish characters
                if result and len(result) < 50 and not result.startswith("Słowo"):
                    _pronunciation_cache[word.lower()] = result
                    logger.debug(f"LLM pronunciation: {word} → {result}")
                    return result
            
        except Exception as e:
            logger.warning(f"LLM pronunciation failed for '{word}': {e}")
        
        return None
    
    def _find_unknown_english_words(self, text: str) -> list[str]:
        """Find English words not in our dictionary."""
        words = ENGLISH_WORD_PATTERN.findall(text)
        unknown = []
        
        for word in words:
            word_lower = word.lower()
            # Strip Polish suffixes for dictionary lookup
            base_word = self._strip_polish_suffix(word_lower)
            
            # Skip if in dictionary (any case variant or base form)
            if word in POLISH_PRONUNCIATIONS or word_lower in POLISH_PRONUNCIATIONS:
                continue
            if word.upper() in POLISH_PRONUNCIATIONS:
                continue
            if base_word in POLISH_PRONUNCIATIONS:
                continue
            # Skip common words
            if word_lower in SKIP_WORDS:
                continue
            # Skip very short words (likely Polish)
            if len(word) <= 2:
                continue
            # Skip words that look Polish (have Polish-specific letters)
            if any(c in word for c in "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"):
                continue
            # Skip numbers
            if word.isdigit():
                continue
            # Skip words that are likely Polish based on common patterns
            if self._looks_polish(word_lower):
                continue
            
            unknown.append(word)
        
        return list(set(unknown))  # Unique
    
    def _looks_polish(self, word: str) -> bool:
        """Heuristic to detect if word is likely Polish."""
        # Common Polish word endings
        polish_endings = (
            'ać', 'ić', 'yć', 'eć', 'ować', 'ywać', 'iwać',  # verbs
            'ość', 'ność', 'stwo', 'ctwo',  # nouns
            'owy', 'owa', 'owe', 'owi', 'owych',  # adjectives
            'ący', 'ąca', 'ące', 'ącego', 'ącej',  # participles
            'dź', 'dzi', 'dzu', 'dza', 'dzą', 'dzę',  # dź cluster
            'rz', 'rzy', 'rzu', 'rza', 'rzą', 'rzę',  # rz cluster
            'sz', 'szy', 'szu', 'sza', 'szą', 'szę',  # sz cluster
            'cz', 'czy', 'czu', 'cza', 'czą', 'czę',  # cz cluster
            'ie', 'ia', 'iu', 'io',  # common Polish vowel clusters
            'ej', 'aj', 'uj', 'ij',  # j clusters
        )
        if word.endswith(polish_endings):
            return True
        
        # Common Polish verbs and words (expanded)
        polish_words = {
            'zobacz', 'sprawdź', 'zrób', 'idź', 'weź', 'daj', 'mów', 'pisz',
            'dzieje', 'dzieję', 'działać', 'działa',
            'logi', 'logo', 'logów',
            'który', 'która', 'które', 'którzy', 'których',
            'bardzo', 'tylko', 'także', 'również', 'jednak', 'jeszcze',
            'teraz', 'potem', 'wcześniej', 'później', 'zaraz',
            'tutaj', 'gdzie', 'kiedy', 'dlaczego', 'dlatego',
        }
        if word in polish_words:
            return True
        
        return False
    
    def _strip_polish_suffix(self, word: str) -> str:
        """Strip common Polish grammatical suffixes from English words."""
        # Polish case endings often added to English words
        suffixes = [
            'ów', 'om', 'ami', 'ach', 'em', 'ie', 'owi', 'a', 'u', 'y', 'ę', 'ą',
            'iem', 'em', 'ów', 'ami', 'ach', 'om'
        ]
        for suffix in sorted(suffixes, key=len, reverse=True):
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[:-len(suffix)]
        return word
    
    def normalize(self, text: str, language: str = "pl") -> str:
        """
        Normalize text for TTS with LLM enhancement.
        
        Args:
            text: Input text with English terms.
            language: Target language (only 'pl' uses LLM).
        
        Returns:
            Text with English words converted to Polish phonetic form.
        """
        result = text
        
        # First pass: use LLM for unknown English words (before dictionary mangles them)
        if language == "pl" and self.use_llm:
            unknown_words = self._find_unknown_english_words(result)
            
            if unknown_words:
                logger.debug(f"Unknown English words for LLM: {unknown_words[:10]}")
                
                for word in unknown_words:
                    pronunciation = self._get_pronunciation_from_llm(word)
                    if pronunciation:
                        # Replace word with pronunciation (case-insensitive)
                        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                        result = pattern.sub(pronunciation, result)
        
        # Second pass: use static dictionary (fast, deterministic)
        result = normalize_text_for_tts(result, language)
        
        return result
    
    def add_to_dictionary(self, word: str, pronunciation: str):
        """Add a new word to the static dictionary."""
        POLISH_PRONUNCIATIONS[word] = pronunciation
        logger.info(f"Added to dictionary: {word} → {pronunciation}")
    
    def get_cached_pronunciations(self) -> dict[str, str]:
        """Return all LLM-generated pronunciations (for potential dictionary update)."""
        return _pronunciation_cache.copy()
    
    def export_new_pronunciations(self) -> str:
        """Export new LLM pronunciations as Python dict entries."""
        if not _pronunciation_cache:
            return "# No new pronunciations"
        
        lines = ["# New pronunciations from LLM (add to POLISH_PRONUNCIATIONS):"]
        for word, pron in sorted(_pronunciation_cache.items()):
            lines.append(f'    "{word}": "{pron}",')
        
        return "\n".join(lines)


# Singleton instance for easy import
_normalizer: Optional[LLMTextNormalizer] = None


def get_llm_normalizer(
    use_llm: bool = True,
    model: str = "qwen2.5:1.5b"
) -> LLMTextNormalizer:
    """Get or create singleton LLM normalizer instance."""
    global _normalizer
    if _normalizer is None:
        _normalizer = LLMTextNormalizer(use_llm=use_llm, model=model)
    return _normalizer


def normalize_with_llm(text: str, language: str = "pl") -> str:
    """Convenience function for LLM-enhanced normalization."""
    return get_llm_normalizer().normalize(text, language)
