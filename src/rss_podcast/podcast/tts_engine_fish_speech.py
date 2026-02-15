"""TTS Engine - Text-to-Speech using Fish Speech."""

import logging
import os
import subprocess
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Callable
import ormsgpack

from .models import Speaker, Segment, PodcastScript
from .text_normalizer import normalize_text_for_tts
from ..config import TTSConfig, VoiceConfig

logger = logging.getLogger(__name__)

# Global API server process
_api_server_process = None


def _start_api_server(config: TTSConfig) -> subprocess.Popen:
    """Start Fish Speech API server in background."""
    global _api_server_process
    
    if _api_server_process is not None and _api_server_process.poll() is None:
        logger.info("Fish Speech API server already running")
        return _api_server_process
    
    repo_path = Path(config.fish_speech_repo).resolve()
    checkpoint_path = Path(config.checkpoint_path).resolve()
    
    if not repo_path.exists():
        raise RuntimeError(f"Fish Speech repo not found: {repo_path}")
    
    if not checkpoint_path.exists():
        raise RuntimeError(f"Fish Speech checkpoint not found: {checkpoint_path}")
    
    # Detect codec path based on model version
    if (checkpoint_path / "codec.pth").exists():
        decoder_path = checkpoint_path / "codec.pth"
    elif (checkpoint_path / "firefly-gan-vq-fsq-8x1024-21hz-generator.pth").exists():
        decoder_path = checkpoint_path / "firefly-gan-vq-fsq-8x1024-21hz-generator.pth"
    else:
        raise RuntimeError(f"No codec/decoder found in {checkpoint_path}")
    
    logger.info(f"Starting Fish Speech API server...")
    logger.info(f"  Checkpoint: {checkpoint_path}")
    logger.info(f"  Decoder: {decoder_path}")
    logger.info(f"  Device: {config.device}")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_path)
    
    cmd = [
        "python", "-m", "tools.api_server",
        "--listen", f"{config.api_host}:{config.api_port}",
        "--llama-checkpoint-path", str(checkpoint_path),
        "--decoder-checkpoint-path", str(decoder_path),
        "--device", config.device,
        "--half",  # Use FP16 for faster inference
    ]
    
    _api_server_process = subprocess.Popen(
        cmd,
        cwd=str(repo_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    
    # Wait for server to start
    api_url = f"http://{config.api_host}:{config.api_port}/v1/health"
    max_wait = 120  # 2 minutes max
    wait_interval = 2
    waited = 0
    
    logger.info(f"Waiting for API server at {api_url}...")
    while waited < max_wait:
        try:
            response = requests.post(api_url, timeout=5)
            if response.status_code == 200:
                logger.info("Fish Speech API server ready!")
                return _api_server_process
        except requests.exceptions.ConnectionError:
            pass
        
        time.sleep(wait_interval)
        waited += wait_interval
        
        # Check if process died
        if _api_server_process.poll() is not None:
            # Read output to see what went wrong
            output = _api_server_process.stdout.read().decode() if _api_server_process.stdout else ""
            logger.error(f"API server died. Output:\n{output}")
            raise RuntimeError("Fish Speech API server failed to start")
        
        logger.debug(f"Still waiting for API server... ({waited}s)")
    
    raise RuntimeError(f"API server did not start within {max_wait} seconds")


def _stop_api_server():
    """Stop Fish Speech API server."""
    global _api_server_process
    
    if _api_server_process is not None:
        logger.info("Stopping Fish Speech API server...")
        _api_server_process.terminate()
        try:
            _api_server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _api_server_process.kill()
        _api_server_process = None


class TTSEngine:
    """Text-to-Speech engine using Fish Speech API."""
    
    def __init__(
        self,
        tts_config: TTSConfig | None = None,
        voice_config: VoiceConfig | None = None,
        language: str = "pl",
    ):
        self.tts_config = tts_config or TTSConfig()
        self.voice_config = voice_config or VoiceConfig()
        self.language = language
        self._server_started = False
        
        # API endpoint
        self.api_url = f"http://{self.tts_config.api_host}:{self.tts_config.api_port}/v1/tts"
    
    def _ensure_server(self):
        """Ensure API server is running."""
        if not self._server_started:
            _start_api_server(self.tts_config)
            self._server_started = True
    
    def _load_reference_audio(self, voice_sample: Path | str | None) -> bytes | None:
        """Load reference audio for voice cloning."""
        if voice_sample is None:
            return None
        
        path = Path(voice_sample)
        if not path.exists():
            logger.warning(f"Voice sample not found: {path}")
            return None
        
        with open(path, "rb") as f:
            return f.read()
    
    def synthesize_segment(self, segment: Segment, output_path: Path) -> Path:
        """
        Generate audio for a single segment.
        
        Args:
            segment: Segment with text to synthesize.
            output_path: Path to save audio file.
        
        Returns:
            Path to generated audio file.
        """
        self._ensure_server()
        
        # Normalize text for TTS
        normalized_text = normalize_text_for_tts(segment.text, self.language)
        
        # Determine voice sample based on speaker
        if segment.speaker == Speaker.HOST:
            voice_sample = self.voice_config.host_voice_sample
        else:
            voice_sample = self.voice_config.co_host_voice_sample
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build request
        references = []
        if voice_sample:
            audio_bytes = self._load_reference_audio(voice_sample)
            if audio_bytes:
                references.append({
                    "audio": audio_bytes,
                    "text": "",  # Empty text for reference
                })
        
        request_data = {
            "text": normalized_text,
            "references": references,
            "format": self.tts_config.audio_format,
            "chunk_length": self.tts_config.chunk_length,
            "top_p": self.tts_config.top_p,
            "temperature": self.tts_config.temperature,
            "repetition_penalty": self.tts_config.repetition_penalty,
            "max_new_tokens": self.tts_config.max_new_tokens,
            "streaming": False,
            "normalize": True,
        }
        
        # Send request
        try:
            response = requests.post(
                self.api_url,
                params={"format": "msgpack"},
                data=ormsgpack.packb(request_data),
                headers={"content-type": "application/msgpack"},
                timeout=300,  # 5 min timeout for long segments
            )
            
            if response.status_code != 200:
                logger.error(f"TTS API error: {response.status_code} - {response.text}")
                raise RuntimeError(f"TTS API error: {response.status_code}")
            
            # Save audio
            with open(output_path, "wb") as f:
                f.write(response.content)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TTS request failed: {e}")
            raise RuntimeError(f"TTS request failed: {e}")
        
        segment.audio_path = str(output_path)
        return output_path
    
    def synthesize_script(
        self,
        script: PodcastScript,
        output_dir: Path,
        progress_callback: Callable | None = None,
    ) -> Path:
        """
        Generate full podcast audio from script.
        
        Args:
            script: PodcastScript with segments.
            output_dir: Directory for output files.
            progress_callback: Optional callback(current, total, segment).
        
        Returns:
            Path to final combined audio file.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        audio_format = self.tts_config.audio_format
        segment_files = []
        
        logger.info(f"Synthesizing {len(script.segments)} segments with Fish Speech...")
        
        for i, segment in enumerate(script.segments):
            segment_path = output_dir / f"segment_{i:03d}.{audio_format}"
            
            logger.debug(f"[{i+1}/{len(script.segments)}] {segment.speaker.value}: {segment.text[:50]}...")
            
            self.synthesize_segment(segment, segment_path)
            segment_files.append(segment_path)
            
            if progress_callback:
                progress_callback(i + 1, len(script.segments), segment)
        
        # Combine segments
        timestamp = datetime.now().strftime("%Y-%m-%d")
        final_path = output_dir / f"podcast_{timestamp}.{audio_format}"
        
        self._combine_audio(segment_files, final_path)
        
        script.audio_path = str(final_path)
        
        # Cleanup segment files
        for f in segment_files:
            f.unlink(missing_ok=True)
        
        return final_path
    
    def _combine_audio(self, audio_files: list[Path], output_path: Path) -> None:
        """Combine multiple audio files using ffmpeg."""
        if not audio_files:
            return
        
        # Create file list for ffmpeg
        list_file = output_path.parent / "filelist.txt"
        with open(list_file, "w") as f:
            for audio_file in audio_files:
                f.write(f"file '{audio_file.name}'\n")
        
        logger.info("Combining audio segments...")
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path),
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Podcast saved: {output_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg error: {e.stderr.decode()}")
            raise RuntimeError(f"Failed to combine audio: {e}")
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. Install with: sudo apt install ffmpeg"
            )
        finally:
            list_file.unlink(missing_ok=True)
    
    def __del__(self):
        """Cleanup on destruction."""
        # Note: We don't stop the server here to allow reuse
        pass


# Cleanup on module unload
import atexit
atexit.register(_stop_api_server)
