# Feedcast — RSS-to-Podcast Generator

Turn your RSS feeds into a two-host tech podcast, fully offline, using a local LLM for scriptwriting and open-source TTS for audio synthesis.

```
RSS feeds ──► article scraper ──► LLM script writer ──► TTS engine ──► 🎧 podcast
```

## How it works

1. **Fetch** — pulls articles from your configured RSS feeds and scrapes full content with [trafilatura](https://trafilatura.readthedocs.io/).
2. **Script** — sends articles to a local [Ollama](https://ollama.com/) model which generates a natural two-host dialogue covering the week's news.
3. **Audio** *(work-in-progress)* — synthesizes each dialogue segment with text-to-speech (Coqui XTTS or Fish Speech) and concatenates them into a single audio file.

> **⚠️ Note:** The primary focus of this project is feed aggregation and web scraping to gather rich article content. Script generation and podcast audio are a natural follow-up but are still **work-in-progress**. Current open-source TTS models (XTTS v2, Fish Speech) produce serviceable but noticeably synthetic output — especially for non-English languages. Both the script-generation pipeline and TTS integration will improve as open models mature.

> **💡 Tip:** In the meantime, you can upload the scraped article summaries (from `output/articles/`) into [Google NotebookLM](https://notebooklm.google.com/) and let it generate a podcast for you — it produces surprisingly natural audio and is a great way to consume your aggregated content right now.

## Features

- Aggregate articles from any number of RSS/Atom feeds
- Scrape full article content (not just summaries)
- Generate podcast scripts with a local LLM via Ollama — no API keys needed
- Multi-language support (English, Polish, and more)
- Pluggable TTS backends (Coqui XTTS v2, Fish Speech)
- Voice cloning from custom `.wav` samples
- Clean CLI with progress indicators ([Rich](https://github.com/Textualize/rich))

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/) running locally with a model pulled (e.g. `gemma2:27b`, `qwen2.5:14b-instruct`)
- *(optional, for audio)* NVIDIA GPU with ≥ 12 GB VRAM, `ffmpeg`

## Installation

```bash
git clone https://github.com/yourusername/feedcast.git
cd feedcast

# Core install (fetch + script generation)
pip install -e .

# With TTS support (requires CUDA)
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -e ".[tts]"

# Dev dependencies (pytest, ruff)
pip install -e ".[dev]"
```

## Quick start

```bash
# Full pipeline: fetch articles → generate script
rss-podcast pipeline --script-only

# Or step-by-step:
rss-podcast fetch --days 7
rss-podcast generate --script-only   # script only
rss-podcast generate                  # script + audio
```

## Configuration

All configuration lives in YAML files inside `config/`.

### RSS Feeds — `config/feeds.yaml`

```yaml
feeds:
  - url: "https://example.com/feed.xml"
    name: "Example Feed"
    category: "tech"

  - url: "https://hnrss.org/newest?q=python"
    name: "Hacker News - Python"
    category: "programming"

scraper:
  days_back: 7
  max_workers: 5
  scrape_full_articles: true
```

### LLM — `config/llm.yaml`

```yaml
base_url: "http://localhost:11434"
model: "gemma2:27b-instruct-q4_K_M"
temperature: 0.9
max_tokens: 16384
```

### Podcast — `config/podcast.yaml`

```yaml
language: "en"   # "en", "pl", …

voices:
  host_speaker: "Damien Black"
  co_host_speaker: "Claribel Dervla"
  # Uncomment for voice cloning:
  # host_voice_sample: "voices/host.wav"
  # co_host_voice_sample: "voices/cohost.wav"

output_dir: "output/podcasts"
```

## CLI reference

| Command | Description |
|---|---|
| `rss-podcast fetch` | Fetch & scrape articles from RSS feeds |
| `rss-podcast generate` | Generate podcast script (and optionally audio) |
| `rss-podcast pipeline` | Run fetch → generate in one step |
| `rss-podcast list-feeds` | Show configured feeds |

### Common options

```bash
rss-podcast fetch --days 14             # look back 14 days
rss-podcast generate --language en      # generate in English
rss-podcast generate --script-only      # skip audio synthesis
rss-podcast pipeline --script-only      # full pipeline, no audio
```

## Project structure

```
feedcast/
├── src/rss_podcast/
│   ├── cli.py                  # CLI entry points (Click)
│   ├── config.py               # YAML config loader
│   ├── scraper/                # RSS fetching & article scraping
│   ├── podcast/                # Script generation & TTS
│   │   ├── script_generator.py # LLM-powered dialogue writer
│   │   ├── prompts.py          # Prompt templates (PL/EN)
│   │   ├── tts_engine.py       # Coqui XTTS backend
│   │   └── tts_engine_fish_speech.py  # Fish Speech backend
│   └── storage/                # JSON persistence
├── config/                     # YAML configuration files  
├── output/                     # Generated articles & podcasts
├── voices/                     # Custom voice samples (.wav)
├── checkpoints/                # TTS model weights (not tracked)
├── tests/                      # Test suite
├── Makefile                    # Convenience targets
└── pyproject.toml              # Package metadata & deps
```

## Development

```bash
make test        # run tests
make lint        # ruff check
make format      # ruff format + fix
make clean       # remove generated output
```

## Roadmap

- [ ] Improve TTS quality with newer open models
- [ ] Add support for more TTS backends
- [ ] RSS feed auto-discovery
- [ ] Web UI for managing feeds & listening to episodes
- [ ] Scheduled generation (cron / systemd timer)

## License

MIT
