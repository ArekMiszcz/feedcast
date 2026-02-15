"""Data models for RSS scraping."""

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import md5


@dataclass
class Feed:
    """RSS feed configuration."""
    
    url: str
    name: str | None = None
    category: str | None = None
    enabled: bool = True
    
    def __post_init__(self):
        if self.name is None:
            self.name = self.url


@dataclass
class Article:
    """Scraped article data."""
    
    title: str
    url: str
    source: str
    published: datetime
    summary: str = ""
    content: str | None = None
    scraped_at: datetime | None = None
    id: str = field(default="", init=False)
    
    def __post_init__(self):
        # Generate ID from URL hash
        self.id = md5(self.url.encode()).hexdigest()[:12]
    
    def has_content(self) -> bool:
        """Check if article has scraped content."""
        return self.content is not None and len(self.content) > 0
    
    def get_text(self) -> str:
        """Get best available text (content or summary)."""
        if self.content:
            return self.content
        return self.summary
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published": self.published.isoformat(),
            "summary": self.summary,
            "content": self.content,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Create Article from dictionary."""
        article = cls(
            title=data["title"],
            url=data["url"],
            source=data["source"],
            published=datetime.fromisoformat(data["published"]),
            summary=data.get("summary", ""),
            content=data.get("content"),
            scraped_at=datetime.fromisoformat(data["scraped_at"]) if data.get("scraped_at") else None,
        )
        return article
