"""Configuration management for RSS Podcast."""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class ScraperConfig:
    """Configuration for RSS scraping."""
    
    feeds_file: Path = field(default_factory=lambda: Path("config/feeds.yaml"))
    max_workers: int = 5
    days_back: int = 7
    scrape_full_articles: bool = True
    max_content_length: int | None = None
    request_timeout: int = 10
    user_agent: str = "Mozilla/5.0 (RSS Podcast Bot)"


@dataclass
class LLMConfig:
    """Configuration for LLM (Ollama)."""
    
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:14b-instruct"
    temperature: float = 0.8
    max_tokens: int = 4096
    timeout: int = 300  # 5 minutes


@dataclass
class TTSConfig:
    """Configuration for Text-to-Speech."""
    
    model: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    device: str = "cuda"
    audio_format: str = "wav"
    
    # XTTS generation parameters (critical for Polish!)
    temperature: float = 0.15  # Low = stable, no spelling out words
    repetition_penalty: float = 10.0  # High = no stuttering loops
    top_k: int = 50
    top_p: float = 0.85
    length_penalty: float = 1.0
    speed: float = 1.0


@dataclass
class VoiceConfig:
    """Voice configuration for podcast."""
    
    host_speaker: str = "Damien Black"
    co_host_speaker: str = "Claribel Dervla"
    host_voice_sample: Path | None = None
    co_host_voice_sample: Path | None = None


@dataclass
class PodcastConfig:
    """Configuration for podcast generation."""
    
    language: str = "pl"
    voices: VoiceConfig = field(default_factory=VoiceConfig)
    output_dir: Path = field(default_factory=lambda: Path("output/podcasts"))


@dataclass
class StorageConfig:
    """Configuration for data storage."""
    
    articles_dir: Path = field(default_factory=lambda: Path("output/articles"))
    podcasts_dir: Path = field(default_factory=lambda: Path("output/podcasts"))


@dataclass
class Config:
    """Main configuration container."""
    
    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    podcast: PodcastConfig = field(default_factory=PodcastConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    
    @classmethod
    def load(cls, config_dir: Path | str = "config") -> "Config":
        """Load configuration from YAML files."""
        config_dir = Path(config_dir)
        config = cls()
        
        # Load feeds config
        feeds_file = config_dir / "feeds.yaml"
        if feeds_file.exists():
            config.scraper.feeds_file = feeds_file
        
        # Load podcast config
        podcast_file = config_dir / "podcast.yaml"
        if podcast_file.exists():
            data = yaml.safe_load(podcast_file.read_text())
            config = cls._apply_podcast_config(config, data)
        
        # Load LLM config
        llm_file = config_dir / "llm.yaml"
        if llm_file.exists():
            data = yaml.safe_load(llm_file.read_text())
            config = cls._apply_llm_config(config, data)
        
        return config
    
    @classmethod
    def _apply_podcast_config(cls, config: "Config", data: dict[str, Any]) -> "Config":
        """Apply podcast configuration from dict."""
        if not data:
            return config
        
        if "language" in data:
            config.podcast.language = data["language"]
        
        if "voices" in data:
            voices = data["voices"]
            if "host_speaker" in voices:
                config.podcast.voices.host_speaker = voices["host_speaker"]
            if "co_host_speaker" in voices:
                config.podcast.voices.co_host_speaker = voices["co_host_speaker"]
            if "host_voice_sample" in voices:
                config.podcast.voices.host_voice_sample = Path(voices["host_voice_sample"])
            if "co_host_voice_sample" in voices:
                config.podcast.voices.co_host_voice_sample = Path(voices["co_host_voice_sample"])
        
        if "output_dir" in data:
            config.podcast.output_dir = Path(data["output_dir"])
        
        return config
    
    @classmethod
    def _apply_llm_config(cls, config: "Config", data: dict[str, Any]) -> "Config":
        """Apply LLM configuration from dict."""
        if not data:
            return config
        
        if "base_url" in data:
            config.llm.base_url = data["base_url"]
        if "model" in data:
            config.llm.model = data["model"]
        if "temperature" in data:
            config.llm.temperature = data["temperature"]
        if "max_tokens" in data:
            config.llm.max_tokens = data["max_tokens"]
        
        if "tts" in data:
            tts = data["tts"]
            if "model" in tts:
                config.tts.model = tts["model"]
            if "device" in tts:
                config.tts.device = tts["device"]
        
        return config


# Global config instance (lazy loaded)
_config: Config | None = None


def get_config(config_dir: Path | str = "config") -> Config:
    """Get or create global configuration."""
    global _config
    if _config is None:
        _config = Config.load(config_dir)
    return _config


def reset_config() -> None:
    """Reset global configuration (for testing)."""
    global _config
    _config = None
