"""Tests for storage modules."""

import json
from datetime import datetime

from rss_podcast.storage import ArticleStore, PodcastStore
from rss_podcast.scraper.models import Article
from rss_podcast.podcast.models import Speaker, Segment, PodcastScript


class TestArticleStore:
    """Tests for ArticleStore."""
    
    def test_save_and_load(self, sample_articles, temp_output_dir):
        store = ArticleStore(temp_output_dir)
        
        # Save
        start = datetime(2026, 1, 20)
        end = datetime(2026, 1, 27)
        filepath = store.save(sample_articles, (start, end))
        
        assert filepath.exists()
        assert "articles_2026-01-20_2026-01-27.json" in str(filepath)
        
        # Load
        loaded = store.load(filepath)
        
        assert len(loaded) == len(sample_articles)
        assert loaded[0].title == sample_articles[0].title
        assert loaded[0].id == sample_articles[0].id
    
    def test_get_latest(self, sample_articles, temp_output_dir):
        store = ArticleStore(temp_output_dir)
        
        # Initially no files
        assert store.get_latest() is None
        
        # Save one file
        store.save(sample_articles, (datetime(2026, 1, 1), datetime(2026, 1, 7)))
        
        latest = store.get_latest()
        assert latest is not None
        assert "articles_" in str(latest)
    
    def test_export_txt(self, sample_articles, temp_output_dir):
        store = ArticleStore(temp_output_dir)
        
        txt_path = temp_output_dir / "export.txt"
        store.export_txt(sample_articles, txt_path)
        
        assert txt_path.exists()
        
        content = txt_path.read_text()
        assert "RSS ARTICLES EXPORT" in content
        assert "Article 1" in content
        assert "Feed A" in content


class TestPodcastStore:
    """Tests for PodcastStore."""
    
    def test_save_and_load_script(self, sample_script, temp_output_dir):
        store = PodcastStore(temp_output_dir)
        
        # Save
        json_path = store.save_script(sample_script)
        
        assert json_path.exists()
        assert "script_" in str(json_path)
        
        # TXT should also exist
        txt_path = json_path.with_suffix(".txt")
        assert txt_path.exists()
        
        # Load
        loaded = store.load_script(json_path)
        
        assert loaded.title == sample_script.title
        assert loaded.segment_count == sample_script.segment_count
    
    def test_list_podcasts(self, sample_script, temp_output_dir):
        store = PodcastStore(temp_output_dir)
        
        # Initially empty
        assert store.list_podcasts() == []
        
        # Save script
        store.save_script(sample_script)
        
        podcasts = store.list_podcasts()
        assert len(podcasts) == 1
        assert podcasts[0]["title"] == "Test Podcast"
