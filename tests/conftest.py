"""Pytest fixtures for rss_podcast tests."""

import pytest
from datetime import datetime
from pathlib import Path

from rss_podcast.scraper.models import Article, Feed
from rss_podcast.podcast.models import Speaker, Segment, PodcastScript
from rss_podcast.config import Config, ScraperConfig, LLMConfig, TTSConfig, PodcastConfig


@pytest.fixture
def sample_feed():
    """Sample RSS feed."""
    return Feed(
        url="https://example.com/feed.xml",
        name="Example Feed",
        category="tech",
    )


@pytest.fixture
def sample_article():
    """Sample article."""
    return Article(
        title="Test Article",
        url="https://example.com/article-1",
        source="Example Feed",
        published=datetime(2026, 1, 20, 12, 0, 0),
        summary="This is a test article summary.",
        content="This is the full content of the test article.",
    )


@pytest.fixture
def sample_articles():
    """List of sample articles."""
    return [
        Article(
            title="Article 1",
            url="https://example.com/article-1",
            source="Feed A",
            published=datetime(2026, 1, 25, 10, 0, 0),
            summary="Summary 1",
            content="Content 1",
        ),
        Article(
            title="Article 2",
            url="https://example.com/article-2",
            source="Feed B",
            published=datetime(2026, 1, 24, 15, 0, 0),
            summary="Summary 2",
        ),
        Article(
            title="Article 3",
            url="https://example.com/article-3",
            source="Feed A",
            published=datetime(2026, 1, 23, 8, 0, 0),
            summary="Summary 3",
            content="Content 3",
        ),
    ]


@pytest.fixture
def sample_segment():
    """Sample podcast segment."""
    return Segment(
        speaker=Speaker.HOST,
        text="Welcome to the podcast!",
    )


@pytest.fixture
def sample_script(sample_articles):
    """Sample podcast script."""
    return PodcastScript(
        title="Test Podcast",
        segments=[
            Segment(speaker=Speaker.HOST, text="Welcome to the show!"),
            Segment(speaker=Speaker.CO_HOST, text="Great to be here."),
            Segment(speaker=Speaker.HOST, text="Let's discuss today's news."),
        ],
        source_article_ids=[a.id for a in sample_articles],
        language="en",
    )


@pytest.fixture
def test_config(tmp_path):
    """Test configuration with temp paths."""
    return Config(
        scraper=ScraperConfig(
            feeds_file=tmp_path / "feeds.yaml",
            max_workers=2,
            days_back=7,
        ),
        llm=LLMConfig(
            base_url="http://localhost:11434",
            model="test-model",
        ),
    )


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
