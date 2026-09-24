import logging
from datetime import datetime
from time import mktime
from typing import Any, Dict, List, Optional
import feedparser
import httpx
from database.client import db

logger = logging.getLogger(__name__)

# Default crypto news RSS feeds
DEFAULT_RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
]


class SentimentAnalyzer:
    """Basic rule-based sentiment analyzer for news headlines and summaries."""

    BULLISH_KEYWORDS = {
        "bullish", "rally", "surge", "breakout", "gain", "soar", "adoption",
        "approval", "etf", "all-time high", "ath", "buy", "record", "growth"
    }

    BEARISH_KEYWORDS = {
        "bearish", "crash", "plunge", "dump", "drop", "hack", "exploit",
        "lawsuit", "ban", "sec", "collapse", "liquidation", "sell", "down"
    }

    @classmethod
    def analyze_text(cls, text: str) -> Dict[str, Any]:
        """Analyze text sentiment and return label and score between -1.0 and +1.0."""
        text_lower = text.lower()
        
        bull_count = sum(1 for kw in cls.BULLISH_KEYWORDS if kw in text_lower)
        bear_count = sum(1 for kw in cls.BEARISH_KEYWORDS if kw in text_lower)

        total_matches = bull_count + bear_count
        if total_matches == 0:
            return {"sentiment_label": "NEUTRAL", "sentiment_score": 0.0}

        score = round((bull_count - bear_count) / total_matches, 2)

        if score > 0.2:
            label = "BULLISH"
        elif score < -0.2:
            label = "BEARISH"
        else:
            label = "NEUTRAL"

        return {"sentiment_label": label, "sentiment_score": score}


class NewsCollector:
    """Collector responsible for fetching crypto news via RSS feeds and storing sentiment data."""

    def __init__(self, rss_urls: Optional[List[str]] = None) -> None:
        self.rss_urls = rss_urls or DEFAULT_RSS_FEEDS

    async def _fetch_feed_xml(self, client: httpx.AsyncClient, url: str) -> Optional[str]:
        """Asynchronously fetch RSS feed content as string."""
        try:
            response = await client.get(url, timeout=10.0, follow_redirects=True)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch RSS feed from {url}: {e}")
            return None

    def _parse_entry(self, entry: Any, source_url: str) -> Dict[str, Any]:
        """Parse a single feedparser entry into a structured dictionary."""
        title = entry.get("title", "")
        summary = entry.get("summary", "") or entry.get("description", "")
        link = entry.get("link", "")
        
        # Extract published timestamp
        published_parsed = entry.get("published_parsed")
        if published_parsed:
            published_at = datetime.fromtimestamp(mktime(published_parsed)).isoformat()
        else:
            published_at = datetime.utcnow().isoformat()

        # Compute sentiment
        text_to_analyze = f"{title} {summary}"
        sentiment_result = SentimentAnalyzer.analyze_text(text_to_analyze)

        return {
            "title": title,
            "summary": summary[:500] if summary else "",  # Truncate summary if long
            "url": link,
            "source": source_url,
            "sentiment_label": sentiment_result["sentiment_label"],
            "sentiment_score": sentiment_result["sentiment_score"],
            "published_at": published_at,
        }

    async def fetch_and_store_news(self) -> int:
        """Fetch news entries from all configured RSS feeds and insert into Supabase."""
        parsed_entries: List[Dict[str, Any]] = []

        async with httpx.AsyncClient() as http_client:
            for url in self.rss_urls:
                xml_content = await self._fetch_feed_xml(http_client, url)
                if not xml_content:
                    continue

                feed = feedparser.parse(xml_content)
                for entry in feed.entries[:10]:  # Limit to 10 latest articles per feed
                    parsed_item = self._parse_entry(entry, source_url=url)
                    parsed_entries.append(parsed_item)

        if not parsed_entries:
            logger.warning("No news articles collected.")
            return 0

        # Upsert into 'news' table in Supabase
        client = await db.connect()
        try:
            # Requires unique constraint or primary key on 'url' in Supabase news table
            await client.table("news").upsert(parsed_entries, on_conflict="url").execute()
            logger.info(f"Successfully synced {len(parsed_entries)} news articles to Supabase.")
            return len(parsed_entries)
        except Exception as e:
            logger.error(f"Failed to store news in Supabase: {e}")
            raise e


async def run_news_sync() -> int:
    """Convenience runner function for news collection."""
    collector = NewsCollector()
    return await collector.fetch_and_store_news()