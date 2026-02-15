"""RSS Feed Fetcher - fetches articles from RSS feeds."""

import time
import logging
from datetime import datetime
from pathlib import Path

import feedparser
import requests
import yaml

from .models import Article, Feed
from ..config import ScraperConfig

logger = logging.getLogger(__name__)


class RSSFetcher:
    """Fetches and parses RSS feeds."""
    
    def __init__(self, config: ScraperConfig | None = None):
        self.config = config or ScraperConfig()
        self._feeds: list[Feed] | None = None
    
    @property
    def feeds(self) -> list[Feed]:
        """Lazy-load feeds from config file."""
        if self._feeds is None:
            self._feeds = self._load_feeds()
        return self._feeds
    
    def _load_feeds(self) -> list[Feed]:
        """Load feeds from YAML configuration."""
        feeds_file = self.config.feeds_file
        
        if not feeds_file.exists():
            logger.warning(f"Feeds file not found: {feeds_file}")
            return []
        
        data = yaml.safe_load(feeds_file.read_text())
        feeds_data = data.get("feeds", [])
        
        feeds = []
        for item in feeds_data:
            feed = Feed(
                url=item["url"],
                name=item.get("name"),
                category=item.get("category"),
                enabled=item.get("enabled", True),
            )
            if feed.enabled:
                feeds.append(feed)
        
        logger.info(f"Loaded {len(feeds)} feeds from {feeds_file}")
        return feeds
    
    def fetch_all(self, since: datetime | None = None) -> list[Article]:
        """
        Fetch articles from all configured feeds.
        
        Args:
            since: Only return articles published after this date.
                   Defaults to config.days_back days ago.
        
        Returns:
            List of Article objects.
        """
        if since is None:
            from datetime import timedelta
            since = datetime.now() - timedelta(days=self.config.days_back)
        
        all_articles = []
        
        for feed in self.feeds:
            try:
                articles = self.fetch_feed(feed, since)
                all_articles.extend(articles)
                logger.info(f"Fetched {len(articles)} articles from {feed.name}")
            except Exception as e:
                logger.error(f"Error fetching {feed.url}: {e}")
        
        # Sort by date, newest first
        all_articles.sort(key=lambda a: a.published, reverse=True)
        
        logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles
    
    def fetch_feed(self, feed: Feed, since: datetime) -> list[Article]:
        """
        Fetch articles from a single feed.
        
        Args:
            feed: Feed configuration.
            since: Only return articles published after this date.
        
        Returns:
            List of Article objects from this feed.
        """
        # Fetch RSS with requests first (better error handling)
        try:
            response = requests.get(
                feed.url,
                headers={"User-Agent": self.config.user_agent},
                timeout=self.config.request_timeout,
            )
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
        except requests.RequestException as e:
            logger.error(f"HTTP error fetching {feed.url}: {e}")
            return []
        
        if parsed.bozo and parsed.bozo_exception:
            logger.warning(f"Feed parsing warning for {feed.url}: {parsed.bozo_exception}")
        
        # Get feed name from feed itself if not configured
        feed_name = feed.name or parsed.feed.get("title", feed.url)
        
        articles = []
        for entry in parsed.entries:
            pub_date = self._parse_date(entry)
            
            if pub_date is None:
                continue
            
            if pub_date < since:
                continue
            
            article = Article(
                title=entry.get("title", "(No title)"),
                url=entry.get("link", ""),
                source=feed_name,
                published=pub_date,
                summary=entry.get("summary", entry.get("description", "")),
            )
            articles.append(article)
        
        return articles
    
    def _parse_date(self, entry) -> datetime | None:
        """Extract publication date from feed entry."""
        # Try published_parsed first
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime.fromtimestamp(time.mktime(entry.published_parsed))
        
        # Fall back to updated_parsed
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return datetime.fromtimestamp(time.mktime(entry.updated_parsed))
        
        return None
