"""TTS Engine - Text-to-Speech using Coqui XTTS."""

import logging
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Callable

from .models import Speaker, Segment, PodcastScript
from .text_normalizer import normalize_text_for_tts, sanitize_segment_text, detect_repetition_artifacts
from ..config import TTSConfig, VoiceConfig

logger = logging.getLogger(__name__)

# XTTS character limits by language
XTTS_CHAR_LIMITS = {
    "pl": 224,
    "en": 250,
    "de": 250,
    "es": 250,
    "fr": 250,
    "it": 250,
    "pt": 250,
    "default": 200,
}


def _split_long_text(text: str, max_chars: int = 200) -> list[str]:
    """
    Split long text into smaller chunks that fit within TTS character limit.
    
    Tries to split at natural boundaries:
    1. Sentence endings (. ! ?)
    2. Commas and semicolons
    3. Word boundaries
    
    Args:
        text: Text to split
        max_chars: Maximum characters per chunk
        
    Returns:
        List of text chunks, each within the limit
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    remaining = text.strip()
    
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        
        # Find best split point within limit
        chunk = remaining[:max_chars]
        
        # Try to split at sentence boundary
        sentence_breaks = list(re.finditer(r'[.!?]\s+', chunk))
        if sentence_breaks:
            # Use the last sentence break
            split_pos = sentence_breaks[-1].end()
            chunks.append(remaining[:split_pos].strip())
            remaining = remaining[split_pos:].strip()
            continue
        
        # Try to split at comma/semicolon
        clause_breaks = list(re.finditer(r'[,;]\s+', chunk))
        if clause_breaks:
            split_pos = clause_breaks[-1].end()
            chunks.append(remaining[:split_pos].strip())
            remaining = remaining[split_pos:].strip()
            continue
        
        # Fall back to word boundary
        last_space = chunk.rfind(' ')
        if last_space > max_chars // 2:  # Only if we're not cutting too early
            chunks.append(remaining[:last_space].strip())
            remaining = remaining[last_space:].strip()
        else:
            # No good break point, just cut at limit
            chunks.append(chunk.strip())
            remaining = remaining[max_chars:].strip()
    
    return chunks

# Auto-accept Coqui TOS (CPML non-commercial license)
os.environ["COQUI_TOS_AGREED"] = "1"

# Lazy-loaded TTS model
_tts_model = None

# Lazy-loaded LLM normalizer
_llm_normalizer = None


def _get_tts_model(config: TTSConfig):
    """Lazy-load TTS model (heavy import)."""
    global _tts_model
    if _tts_model is None:
        try:
            from TTS.api import TTS
            logger.info(f"Loading TTS model: {config.model}")
            logger.info(f"Device: {config.device}")
            _tts_model = TTS(config.model, progress_bar=True).to(config.device)
            logger.info("TTS model loaded")
        except ImportError:
            raise RuntimeError(
                "TTS not installed. Install with: pip install TTS torch"
            )
    return _tts_model


def _get_llm_normalizer(use_llm: bool = True):
    """Lazy-load LLM normalizer."""
    global _llm_normalizer
    if _llm_normalizer is None and use_llm:
        try:
            from .llm_text_normalizer import LLMTextNormalizer
            _llm_normalizer = LLMTextNormalizer(
                model="qwen2.5:14b-instruct",  # Good balance of quality/speed
                use_llm=True
            )
            logger.info("LLM text normalizer initialized")
        except Exception as e:
            logger.warning(f"Could not initialize LLM normalizer: {e}")
            _llm_normalizer = False  # Mark as unavailable
    return _llm_normalizer if _llm_normalizer else None


class TTSEngine:
    """Text-to-Speech engine using Coqui XTTS."""
    
    def __init__(
        self,
        tts_config: TTSConfig | None = None,
        voice_config: VoiceConfig | None = None,
        language: str = "pl",
        use_llm_normalizer: bool = True,
    ):
        self.tts_config = tts_config or TTSConfig()
        self.voice_config = voice_config or VoiceConfig()
        self.language = language
        self.use_llm_normalizer = use_llm_normalizer
        self._model = None
    
    @property
    def model(self):
        """Lazy-load TTS model."""
        if self._model is None:
            self._model = _get_tts_model(self.tts_config)
        return self._model
    
    def synthesize_segment(self, segment: Segment, output_path: Path) -> Path:
        """
        Generate audio for a single segment.
        
        Args:
            segment: Segment with text to synthesize.
            output_path: Path to save audio file.
        
        Returns:
            Path to generated audio file, or None if segment was skipped.
        """
        # Full sanitization: clean metadata, check for artifacts, normalize
        sanitized_text = sanitize_segment_text(segment.text)
        
        if not sanitized_text:
            logger.warning(f"Skipping invalid segment (metadata/artifact): '{segment.text[:50]}...'")
            return None
        
        # Normalize tech terms for pronunciation
        # Try LLM-enhanced normalization first, fall back to static dictionary
        llm_norm = _get_llm_normalizer(self.use_llm_normalizer)
        if llm_norm:
            normalized_text = llm_norm.normalize(sanitized_text, self.language)
        else:
            normalized_text = normalize_text_for_tts(sanitized_text, self.language)
        
        # Get character limit for language
        max_chars = XTTS_CHAR_LIMITS.get(self.language, XTTS_CHAR_LIMITS["default"])
        
        # Check if text exceeds limit - if so, log warning
        # (splitting is handled in synthesize_script)
        if len(normalized_text) > max_chars:
            logger.warning(f"Text exceeds {max_chars} chars ({len(normalized_text)}): {normalized_text[:50]}...")
        
        # Determine voice settings based on speaker
        if segment.speaker == Speaker.HOST:
            voice_sample = self.voice_config.host_voice_sample
            default_speaker = self.voice_config.host_speaker
        else:
            voice_sample = self.voice_config.co_host_voice_sample
            default_speaker = self.voice_config.co_host_speaker
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # XTTS generation kwargs for stability (low temp = no spelling out)
        xtts_kwargs = {
            "temperature": self.tts_config.temperature,
            "repetition_penalty": self.tts_config.repetition_penalty,
            "top_k": self.tts_config.top_k,
            "top_p": self.tts_config.top_p,
            "length_penalty": self.tts_config.length_penalty,
            "speed": self.tts_config.speed,
        }
        
        if voice_sample and Path(voice_sample).exists():
            # Voice cloning from sample
            self.model.tts_to_file(
                text=normalized_text,
                file_path=str(output_path),
                speaker_wav=str(voice_sample),
                language=self.language,
                **xtts_kwargs,
            )
        else:
            # Built-in speaker
            self.model.tts_to_file(
                text=normalized_text,
                file_path=str(output_path),
                speaker=default_speaker,
                language=self.language,
                **xtts_kwargs,
            )
        
        segment.audio_path = str(output_path)
        return output_path
    
    def _split_segment_if_needed(self, segment: Segment) -> list[Segment]:
        """
        Split a segment into multiple segments if text exceeds character limit.
        
        Args:
            segment: Original segment
            
        Returns:
            List of segments (original or split)
        """
        # First sanitize and normalize to check actual length
        sanitized = sanitize_segment_text(segment.text)
        if not sanitized:
            return [segment]  # Will be skipped later
            
        llm_norm = _get_llm_normalizer(self.use_llm_normalizer)
        if llm_norm:
            normalized = llm_norm.normalize(sanitized, self.language)
        else:
            normalized = normalize_text_for_tts(sanitized, self.language)
        
        max_chars = XTTS_CHAR_LIMITS.get(self.language, XTTS_CHAR_LIMITS["default"])
        
        if len(normalized) <= max_chars:
            return [segment]
        
        # Need to split - use original sanitized text to keep context
        # Use a smaller limit for safety (normalization may expand text)
        safe_limit = int(max_chars * 0.7)  # 70% of limit for safety
        text_chunks = _split_long_text(sanitized, safe_limit)
        
        logger.info(f"Split long segment into {len(text_chunks)} parts")
        
        # Create new segments for each chunk
        return [
            Segment(speaker=segment.speaker, text=chunk)
            for chunk in text_chunks
        ]
    
    def synthesize_script(
        self,
        script: PodcastScript,
        output_dir: Path,
        progress_callback: Callable | None = None,
    ) -> Path:
        """
        Generate full podcast audio from script.
        
        Args:
            script: PodcastScript with segments.
            output_dir: Directory for output files.
            progress_callback: Optional callback(current, total, segment).
        
        Returns:
            Path to final combined audio file.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        audio_format = self.tts_config.audio_format
        segment_files = []
        
        # Pre-process: split any segments that exceed character limit
        processed_segments = []
        for segment in script.segments:
            split_segments = self._split_segment_if_needed(segment)
            processed_segments.extend(split_segments)
        
        if len(processed_segments) != len(script.segments):
            logger.info(f"Expanded {len(script.segments)} segments to {len(processed_segments)} (split long texts)")
        
        logger.info(f"Synthesizing {len(processed_segments)} segments...")
        
        for i, segment in enumerate(processed_segments):
            segment_path = output_dir / f"segment_{i:03d}.{audio_format}"
            
            logger.debug(f"[{i+1}/{len(processed_segments)}] {segment.speaker.value}: {segment.text[:50]}...")
            
            result_path = self.synthesize_segment(segment, segment_path)
            if result_path:  # Only add if segment was successfully generated
                segment_files.append(segment_path)
            
            if progress_callback:
                progress_callback(i + 1, len(processed_segments), segment)
        
        # Combine segments
        timestamp = datetime.now().strftime("%Y-%m-%d")
        final_path = output_dir / f"podcast_{timestamp}.{audio_format}"
        
        self._combine_audio(segment_files, final_path)
        
        script.audio_path = str(final_path)
        
        # Cleanup segment files
        for f in segment_files:
            f.unlink(missing_ok=True)
        
        return final_path
    
    def _combine_audio(self, audio_files: list[Path], output_path: Path) -> None:
        """Combine multiple audio files using ffmpeg."""
        if not audio_files:
            return
        
        # Create file list for ffmpeg
        list_file = output_path.parent / "filelist.txt"
        with open(list_file, "w") as f:
            for audio_file in audio_files:
                f.write(f"file '{audio_file.name}'\n")
        
        logger.info("Combining audio segments...")
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path),
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Podcast saved: {output_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg error: {e.stderr.decode()}")
            raise RuntimeError(f"Failed to combine audio: {e}")
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. Install with: sudo apt install ffmpeg"
            )
        finally:
            list_file.unlink(missing_ok=True)
