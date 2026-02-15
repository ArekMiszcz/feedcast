"""Tests for scraper models."""

from datetime import datetime

from rss_podcast.scraper.models import Article, Feed


class TestFeed:
    """Tests for Feed model."""
    
    def test_feed_creation(self):
        feed = Feed(url="https://example.com/feed.xml")
        assert feed.url == "https://example.com/feed.xml"
        assert feed.name == "https://example.com/feed.xml"  # defaults to URL
        assert feed.enabled is True
    
    def test_feed_with_name(self):
        feed = Feed(
            url="https://example.com/feed.xml",
            name="Example Feed",
            category="tech",
        )
        assert feed.name == "Example Feed"
        assert feed.category == "tech"


class TestArticle:
    """Tests for Article model."""
    
    def test_article_creation(self, sample_article):
        assert sample_article.title == "Test Article"
        assert sample_article.url == "https://example.com/article-1"
        assert sample_article.id is not None
        assert len(sample_article.id) == 12  # MD5 hash prefix
    
    def test_article_id_from_url(self):
        """Same URL should produce same ID."""
        a1 = Article(
            title="Article 1",
            url="https://example.com/same-url",
            source="Feed",
            published=datetime.now(),
        )
        a2 = Article(
            title="Article 2",  # Different title
            url="https://example.com/same-url",  # Same URL
            source="Feed",
            published=datetime.now(),
        )
        assert a1.id == a2.id
    
    def test_has_content(self, sample_article):
        assert sample_article.has_content() is True
        
        article_no_content = Article(
            title="No Content",
            url="https://example.com/no-content",
            source="Feed",
            published=datetime.now(),
        )
        assert article_no_content.has_content() is False
    
    def test_get_text_with_content(self, sample_article):
        text = sample_article.get_text()
        assert text == "This is the full content of the test article."
    
    def test_get_text_without_content(self):
        article = Article(
            title="Summary Only",
            url="https://example.com/summary",
            source="Feed",
            published=datetime.now(),
            summary="This is just the summary.",
        )
        assert article.get_text() == "This is just the summary."
    
    def test_to_dict_and_from_dict(self, sample_article):
        """Test serialization roundtrip."""
        data = sample_article.to_dict()
        
        assert data["title"] == "Test Article"
        assert data["url"] == "https://example.com/article-1"
        assert data["id"] == sample_article.id
        
        restored = Article.from_dict(data)
        
        assert restored.title == sample_article.title
        assert restored.url == sample_article.url
        assert restored.id == sample_article.id
        assert restored.content == sample_article.content
