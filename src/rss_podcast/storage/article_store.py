"""Article storage - save and load articles."""

import json
import logging
from pathlib import Path
from datetime import datetime

from ..scraper.models import Article

logger = logging.getLogger(__name__)


class ArticleStore:
    """Handles article persistence."""
    
    def __init__(self, base_path: Path | str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save(
        self, 
        articles: list[Article], 
        date_range: tuple[datetime, datetime]
    ) -> Path:
        """
        Save articles to JSON file.
        
        Args:
            articles: List of articles to save.
            date_range: (start_date, end_date) tuple.
        
        Returns:
            Path to saved file.
        """
        start_date, end_date = date_range
        filename = f"articles_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.json"
        filepath = self.base_path / filename
        
        data = {
            "meta": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_articles": len(articles),
                "generated_at": datetime.now().isoformat(),
            },
            "articles": [a.to_dict() for a in articles],
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(articles)} articles to {filepath}")
        return filepath
    
    def load(self, path: Path | str) -> list[Article]:
        """
        Load articles from JSON file.
        
        Args:
            path: Path to JSON file.
        
        Returns:
            List of Article objects.
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Articles file not found: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        articles = [Article.from_dict(a) for a in data.get("articles", [])]
        logger.info(f"Loaded {len(articles)} articles from {path}")
        
        return articles
    
    def get_latest(self) -> Path | None:
        """
        Get path to most recent articles file.
        
        Returns:
            Path to latest file or None if no files exist.
        """
        files = list(self.base_path.glob("articles_*.json"))
        
        if not files:
            return None
        
        # Sort by modification time, newest first
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return files[0]
    
    def export_txt(self, articles: list[Article], path: Path | str) -> Path:
        """
        Export articles to plain text (for LLM consumption).
        
        Args:
            articles: List of articles.
            path: Output path.
        
        Returns:
            Path to exported file.
        """
        path = Path(path)
        
        lines = [
            "# RSS ARTICLES EXPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d')}",
            f"Total Articles: {len(articles)}",
            "=" * 50,
            "",
        ]
        
        for article in articles:
            content = article.get_text() or "(No content available)"
            
            lines.extend([
                f"SOURCE: {article.source}",
                f"DATE: {article.published.strftime('%Y-%m-%d')}",
                f"TITLE: {article.title}",
                f"URL: {article.url}",
                f"CONTENT:",
                content,
                "-" * 30,
                "",
            ])
        
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        
        logger.info(f"Exported {len(articles)} articles to {path}")
        return path
