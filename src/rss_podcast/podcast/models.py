"""Data models for podcast generation."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Speaker(Enum):
    """Podcast speakers."""
    
    HOST = "host"
    CO_HOST = "co_host"


@dataclass
class Segment:
    """Single podcast dialogue segment."""
    
    speaker: Speaker
    text: str
    audio_path: str | None = None
    duration_seconds: float | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "speaker": self.speaker.value,
            "text": self.text,
            "audio_path": self.audio_path,
            "duration_seconds": self.duration_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Segment":
        """Create Segment from dictionary."""
        return cls(
            speaker=Speaker(data["speaker"]),
            text=data["text"],
            audio_path=data.get("audio_path"),
            duration_seconds=data.get("duration_seconds"),
        )


@dataclass
class PodcastScript:
    """Complete podcast script with metadata."""
    
    title: str
    segments: list[Segment] = field(default_factory=list)
    source_article_ids: list[str] = field(default_factory=list)
    language: str = "pl"
    generated_at: datetime = field(default_factory=datetime.now)
    audio_path: str | None = None
    total_duration_seconds: float | None = None
    
    @property
    def segment_count(self) -> int:
        """Number of dialogue segments."""
        return len(self.segments)
    
    @property
    def raw_script(self) -> str:
        """Get script as plain text with speaker markers."""
        lines = []
        for segment in self.segments:
            speaker_tag = "[HOST]" if segment.speaker == Speaker.HOST else "[CO-HOST]"
            lines.append(f"{speaker_tag} {segment.text}")
        return "\n\n".join(lines)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "segments": [s.to_dict() for s in self.segments],
            "source_article_ids": self.source_article_ids,
            "language": self.language,
            "generated_at": self.generated_at.isoformat(),
            "audio_path": self.audio_path,
            "total_duration_seconds": self.total_duration_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PodcastScript":
        """Create PodcastScript from dictionary."""
        return cls(
            title=data["title"],
            segments=[Segment.from_dict(s) for s in data.get("segments", [])],
            source_article_ids=data.get("source_article_ids", []),
            language=data.get("language", "pl"),
            generated_at=datetime.fromisoformat(data["generated_at"]) if data.get("generated_at") else datetime.now(),
            audio_path=data.get("audio_path"),
            total_duration_seconds=data.get("total_duration_seconds"),
        )
