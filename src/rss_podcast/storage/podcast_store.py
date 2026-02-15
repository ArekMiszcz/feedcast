"""Podcast storage - save and load podcasts."""

import json
import logging
from pathlib import Path
from datetime import datetime

from ..podcast.models import PodcastScript

logger = logging.getLogger(__name__)


class PodcastStore:
    """Handles podcast persistence."""
    
    def __init__(self, base_path: Path | str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_script(self, script: PodcastScript) -> Path:
        """
        Save podcast script to files (JSON + TXT).
        
        Args:
            script: PodcastScript to save.
        
        Returns:
            Path to saved JSON file.
        """
        timestamp = script.generated_at.strftime("%Y-%m-%d_%H%M%S")
        
        # Save JSON (full data)
        json_path = self.base_path / f"script_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(script.to_dict(), f, ensure_ascii=False, indent=2)
        
        # Save TXT (readable script)
        txt_path = self.base_path / f"script_{timestamp}.txt"
        txt_path.write_text(script.raw_script, encoding="utf-8")
        
        logger.info(f"Saved script to {json_path}")
        return json_path
    
    def load_script(self, path: Path | str) -> PodcastScript:
        """
        Load podcast script from JSON file.
        
        Args:
            path: Path to JSON file.
        
        Returns:
            PodcastScript object.
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Script file not found: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        script = PodcastScript.from_dict(data)
        logger.info(f"Loaded script from {path}")
        
        return script
    
    def get_latest_script(self) -> Path | None:
        """
        Get path to most recent script file.
        
        Returns:
            Path to latest script or None.
        """
        files = list(self.base_path.glob("script_*.json"))
        
        if not files:
            return None
        
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return files[0]
    
    def list_podcasts(self) -> list[dict]:
        """
        List all generated podcasts.
        
        Returns:
            List of podcast metadata dicts.
        """
        podcasts = []
        
        for json_file in self.base_path.glob("script_*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                
                # Find matching audio file
                audio_file = json_file.with_suffix(".wav")
                if not audio_file.exists():
                    audio_file = None
                
                podcasts.append({
                    "title": data.get("title", "Unknown"),
                    "generated_at": data.get("generated_at"),
                    "segment_count": len(data.get("segments", [])),
                    "script_path": str(json_file),
                    "audio_path": str(audio_file) if audio_file else None,
                })
            except Exception as e:
                logger.warning(f"Error reading {json_file}: {e}")
        
        # Sort by date, newest first
        podcasts.sort(key=lambda p: p.get("generated_at", ""), reverse=True)
        return podcasts
