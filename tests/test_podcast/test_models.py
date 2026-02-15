"""Tests for podcast models."""

from datetime import datetime

from rss_podcast.podcast.models import Speaker, Segment, PodcastScript


class TestSegment:
    """Tests for Segment model."""
    
    def test_segment_creation(self, sample_segment):
        assert sample_segment.speaker == Speaker.HOST
        assert sample_segment.text == "Welcome to the podcast!"
        assert sample_segment.audio_path is None
    
    def test_segment_to_dict(self, sample_segment):
        data = sample_segment.to_dict()
        
        assert data["speaker"] == "host"
        assert data["text"] == "Welcome to the podcast!"
    
    def test_segment_from_dict(self):
        data = {
            "speaker": "co_host",
            "text": "Hello everyone!",
            "audio_path": "/path/to/audio.wav",
        }
        segment = Segment.from_dict(data)
        
        assert segment.speaker == Speaker.CO_HOST
        assert segment.text == "Hello everyone!"
        assert segment.audio_path == "/path/to/audio.wav"


class TestPodcastScript:
    """Tests for PodcastScript model."""
    
    def test_script_creation(self, sample_script):
        assert sample_script.title == "Test Podcast"
        assert sample_script.segment_count == 3
        assert sample_script.language == "en"
    
    def test_raw_script(self, sample_script):
        raw = sample_script.raw_script
        
        assert "[HOST] Welcome to the show!" in raw
        assert "[CO-HOST] Great to be here." in raw
        assert "[HOST] Let's discuss today's news." in raw
    
    def test_script_to_dict_and_from_dict(self, sample_script):
        """Test serialization roundtrip."""
        data = sample_script.to_dict()
        
        assert data["title"] == "Test Podcast"
        assert len(data["segments"]) == 3
        
        restored = PodcastScript.from_dict(data)
        
        assert restored.title == sample_script.title
        assert restored.segment_count == sample_script.segment_count
        assert restored.language == sample_script.language
        
        # Check segments
        assert restored.segments[0].speaker == Speaker.HOST
        assert restored.segments[1].speaker == Speaker.CO_HOST
    
    def test_empty_script(self):
        script = PodcastScript(title="Empty")
        
        assert script.segment_count == 0
        assert script.raw_script == ""
