"""CLI entry points for RSS Podcast."""

import logging
from pathlib import Path
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler

from .config import Config, get_config
from .scraper import RSSFetcher, ArticleScraper, Article
from .podcast import ScriptGenerator, TTSEngine

console = Console()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
logger = logging.getLogger("rss_podcast")


@click.group()
@click.option("--config-dir", "-c", default="config", help="Configuration directory")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, config_dir: str, verbose: bool):
    """RSS Podcast Generator - fetch articles and generate podcasts."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = get_config(config_dir)
    
    if verbose:
        logging.getLogger("rss_podcast").setLevel(logging.DEBUG)


@cli.command()
@click.option("--days", "-d", default=7, help="Days back to fetch")
@click.option("--output", "-o", default="output/articles", help="Output directory")
@click.option("--no-scrape", is_flag=True, help="Skip full article scraping")
@click.pass_context
def fetch(ctx, days: int, output: str, no_scrape: bool):
    """Fetch articles from RSS feeds."""
    config = ctx.obj["config"]
    config.scraper.days_back = days
    
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Fetch RSS
    console.print(f"\n[bold blue]📡 Fetching RSS feeds[/bold blue] (last {days} days)")
    
    fetcher = RSSFetcher(config.scraper)
    since = datetime.now() - timedelta(days=days)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching feeds...", total=None)
        articles = fetcher.fetch_all(since)
        progress.update(task, completed=True)
    
    console.print(f"   Found [green]{len(articles)}[/green] articles")
    
    # Scrape full content
    if not no_scrape and articles:
        console.print(f"\n[bold blue]🔍 Scraping full articles[/bold blue]")
        
        scraper = ArticleScraper(max_workers=config.scraper.max_workers)
        
        with Progress(console=console) as progress:
            task = progress.add_task("Scraping...", total=len(articles))
            
            def on_progress(current, total, article):
                status = "✓" if article.has_content() else "✗"
                progress.update(task, advance=1, description=f"{status} {article.title[:40]}...")
            
            articles = scraper.scrape_batch(articles, on_progress)
        
        scraped = sum(1 for a in articles if a.has_content())
        console.print(f"   Scraped [green]{scraped}[/green] / {len(articles)} articles")
    
    # Save articles
    from .storage import ArticleStore
    store = ArticleStore(output_dir)
    
    end_date = datetime.now()
    start_date = since
    filepath = store.save(articles, (start_date, end_date))
    
    console.print(f"\n[bold green]✅ Saved to:[/bold green] {filepath}")


@cli.command()
@click.option("--input", "-i", "input_path", help="Articles file (JSON or TXT)")
@click.option("--output", "-o", default="output/podcasts", help="Output directory")
@click.option("--script-only", is_flag=True, help="Generate script only (no audio)")
@click.option("--language", "-l", default="pl", type=click.Choice(["pl", "en"]))
@click.pass_context
def generate(ctx, input_path: str | None, output: str, script_only: bool, language: str):
    """Generate podcast from articles."""
    config = ctx.obj["config"]
    config.podcast.language = language
    
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find input file
    if not input_path:
        from .storage import ArticleStore
        store = ArticleStore(Path("output/articles"))
        input_path = store.get_latest()
        
        if not input_path:
            console.print("[red]❌ No articles file found. Run 'rss-podcast fetch' first.[/red]")
            raise SystemExit(1)
        
        console.print(f"[dim]Using latest file: {input_path}[/dim]")
    
    # Load articles
    console.print(f"\n[bold blue]📖 Loading articles[/bold blue]")
    
    from .storage import ArticleStore
    store = ArticleStore(Path(input_path).parent)
    articles = store.load(Path(input_path))
    
    console.print(f"   Loaded [green]{len(articles)}[/green] articles")
    
    # Generate script
    console.print(f"\n[bold blue]🤖 Generating script[/bold blue] ({config.llm.model})")
    
    generator = ScriptGenerator(config.llm, config.podcast)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating script...", total=None)
        script = generator.generate(articles)
        progress.update(task, completed=True)
    
    console.print(f"   Generated [green]{script.segment_count}[/green] dialogue segments")
    
    # Save script
    from .storage import PodcastStore
    podcast_store = PodcastStore(output_dir)
    script_path = podcast_store.save_script(script)
    
    console.print(f"   Script saved: {script_path}")
    
    if script_only:
        console.print(f"\n[bold green]✅ Script generated![/bold green]")
        return
    
    # Generate audio
    console.print(f"\n[bold blue]🎙️ Generating audio[/bold blue]")
    
    tts = TTSEngine(config.tts, config.podcast.voices, language)
    
    with Progress(console=console) as progress:
        task = progress.add_task("Synthesizing...", total=script.segment_count)
        
        def on_progress(current, total, segment):
            progress.update(task, advance=1, description=f"{segment.speaker.value}: {segment.text[:30]}...")
        
        audio_path = tts.synthesize_script(script, output_dir, on_progress)
    
    console.print(f"\n[bold green]✅ Podcast ready![/bold green]")
    console.print(f"   Script: {script_path}")
    console.print(f"   Audio:  {audio_path}")


@cli.command()
@click.option("--days", "-d", default=7, help="Days back to fetch")
@click.option("--language", "-l", default="pl", type=click.Choice(["pl", "en"]))
@click.option("--script-only", is_flag=True, help="Generate script only (no audio)")
@click.pass_context
def pipeline(ctx, days: int, language: str, script_only: bool):
    """Run full pipeline: fetch -> generate podcast."""
    console.print("[bold]🎧 RSS Podcast Generator[/bold]\n")
    
    # Run fetch
    ctx.invoke(fetch, days=days)
    
    # Run generate
    ctx.invoke(generate, language=language, script_only=script_only)


@cli.command()
@click.pass_context
def list_feeds(ctx):
    """List configured RSS feeds."""
    config = ctx.obj["config"]
    fetcher = RSSFetcher(config.scraper)
    
    console.print("\n[bold]Configured RSS Feeds:[/bold]\n")
    
    for feed in fetcher.feeds:
        category = f"[{feed.category}]" if feed.category else ""
        console.print(f"  • {feed.name} {category}")
        console.print(f"    [dim]{feed.url}[/dim]")


if __name__ == "__main__":
    cli()
