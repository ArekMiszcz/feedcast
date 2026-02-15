"""Article Scraper - extracts full content from article URLs."""

import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

import trafilatura

from .models import Article

logger = logging.getLogger(__name__)


class ArticleScraper:
    """Scrapes full article content from URLs."""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
    
    def scrape(self, article: Article) -> Article:
        """
        Scrape full content for a single article.
        
        Args:
            article: Article with URL to scrape.
        
        Returns:
            Article with content field populated (if successful).
        """
        if not article.url:
            return article
        
        try:
            downloaded = trafilatura.fetch_url(article.url)
            if not downloaded:
                logger.debug(f"Failed to download: {article.url}")
                return article
            
            content = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=False,
                favor_recall=True,
            )
            
            if content:
                article.content = content
                article.scraped_at = datetime.now()
                logger.debug(f"Scraped {len(content)} chars from {article.url}")
            
        except Exception as e:
            logger.warning(f"Error scraping {article.url}: {e}")
        
        return article
    
    def scrape_batch(
        self, 
        articles: list[Article], 
        progress_callback: Callable | None = None
    ) -> list[Article]:
        """
        Scrape content for multiple articles in parallel.
        
        Args:
            articles: List of articles to scrape.
            progress_callback: Optional callback(current, total, article) for progress.
        
        Returns:
            List of articles with content populated where successful.
        """
        total = len(articles)
        success_count = 0
        failed_count = 0
        
        logger.info(f"Scraping {total} articles with {self.max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_article = {
                executor.submit(self.scrape, article): article
                for article in articles
            }
            
            for i, future in enumerate(as_completed(future_to_article), 1):
                article = future.result()
                
                if article.has_content():
                    success_count += 1
                else:
                    failed_count += 1
                
                if progress_callback:
                    progress_callback(i, total, article)
        
        logger.info(f"Scraping complete: {success_count} succeeded, {failed_count} failed")
        return articles
