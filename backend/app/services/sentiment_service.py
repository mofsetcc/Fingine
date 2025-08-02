"""
Japanese sentiment analysis service using nlp-waseda/roberta-base-japanese-sentiment model.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
import hashlib

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload

from ..models.news import NewsArticle, StockNewsLink
from ..core.database import get_db
from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """Sentiment analysis result."""
    label: str  # 'positive', 'negative', 'neutral'
    score: float  # confidence score 0.0 to 1.0
    raw_score: float  # raw model output -1.0 to 1.0


@dataclass
class SentimentTimelinePoint:
    """Point in sentiment timeline."""
    date: datetime
    positive_count: int
    negative_count: int
    neutral_count: int
    avg_sentiment_score: float
    total_articles: int


class JapaneseSentimentAnalyzer:
    """
    Japanese sentiment analyzer using nlp-waseda/roberta-base-japanese-sentiment model.
    Provides batch processing capabilities for performance optimization.
    """
    
    def __init__(self):
        self.model_name = "nlp-waseda/roberta-base-japanese-sentiment"
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        self._is_initialized = False
        self._initialization_lock = asyncio.Lock()
        
        # Batch processing settings
        self.batch_size = 16
        self.max_sequence_length = 512
        
        # Cache for recent sentiment results
        self._sentiment_cache = {}
        self._cache_ttl = 3600  # 1 hour
        
        # Label mapping from model output to our standard format
        self.label_mapping = {
            "POSITIVE": "positive",
            "NEGATIVE": "negative", 
            "NEUTRAL": "neutral"
        }
    
    async def initialize(self) -> None:
        """Initialize the sentiment analysis model."""
        if self._is_initialized:
            return
        
        async with self._initialization_lock:
            if self._is_initialized:
                return
            
            try:
                logger.info("Initializing Japanese sentiment analysis model...")
                
                # Load tokenizer and model
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
                
                # Create pipeline for easier inference
                self.pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=0 if torch.cuda.is_available() else -1,
                    batch_size=self.batch_size,
                    max_length=self.max_sequence_length,
                    truncation=True
                )
                
                self._is_initialized = True
                logger.info("Japanese sentiment analysis model initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize sentiment analysis model: {e}")
                raise
    
    async def analyze_text(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: Japanese text to analyze
            
        Returns:
            SentimentResult with label, score, and raw_score
        """
        if not text or not text.strip():
            return SentimentResult(label="neutral", score=0.5, raw_score=0.0)
        
        # Check cache first
        cache_key = self._get_cache_key(text)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        await self.initialize()
        
        try:
            # Run inference
            result = self.pipeline(text)[0]
            
            # Convert to our format
            sentiment_result = self._convert_pipeline_result(result)
            
            # Cache the result
            self._cache_result(cache_key, sentiment_result)
            
            return sentiment_result
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment for text: {e}")
            return SentimentResult(label="neutral", score=0.5, raw_score=0.0)
    
    async def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """
        Analyze sentiment of multiple texts in batch for better performance.
        
        Args:
            texts: List of Japanese texts to analyze
            
        Returns:
            List of SentimentResult objects
        """
        if not texts:
            return []
        
        await self.initialize()
        
        results = []
        
        try:
            # Filter out empty texts and create mapping
            valid_texts = []
            text_indices = []
            
            for i, text in enumerate(texts):
                if text and text.strip():
                    valid_texts.append(text.strip())
                    text_indices.append(i)
                else:
                    # Add neutral result for empty texts
                    results.append(SentimentResult(label="neutral", score=0.5, raw_score=0.0))
            
            if not valid_texts:
                return results
            
            # Check cache for valid texts
            cached_results = {}
            uncached_texts = []
            uncached_indices = []
            
            for i, text in enumerate(valid_texts):
                cache_key = self._get_cache_key(text)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    cached_results[i] = cached_result
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            
            # Process uncached texts in batches
            uncached_results = {}
            if uncached_texts:
                for batch_start in range(0, len(uncached_texts), self.batch_size):
                    batch_end = min(batch_start + self.batch_size, len(uncached_texts))
                    batch_texts = uncached_texts[batch_start:batch_end]
                    batch_indices = uncached_indices[batch_start:batch_end]
                    
                    # Run batch inference
                    batch_results = self.pipeline(batch_texts)
                    
                    # Process batch results
                    for i, (text, result) in enumerate(zip(batch_texts, batch_results)):
                        sentiment_result = self._convert_pipeline_result(result)
                        original_index = batch_indices[i]
                        uncached_results[original_index] = sentiment_result
                        
                        # Cache the result
                        cache_key = self._get_cache_key(text)
                        self._cache_result(cache_key, sentiment_result)
            
            # Combine cached and uncached results
            final_results = []
            for i in range(len(valid_texts)):
                if i in cached_results:
                    final_results.append(cached_results[i])
                else:
                    final_results.append(uncached_results[i])
            
            # Insert results back into original positions
            result_iter = iter(final_results)
            final_output = []
            
            for i in range(len(texts)):
                if i in [text_indices[j] for j in range(len(text_indices))]:
                    final_output.append(next(result_iter))
                else:
                    final_output.append(SentimentResult(label="neutral", score=0.5, raw_score=0.0))
            
            return final_output
            
        except Exception as e:
            logger.error(f"Error in batch sentiment analysis: {e}")
            # Return neutral results for all texts
            return [SentimentResult(label="neutral", score=0.5, raw_score=0.0) for _ in texts]
    
    def _convert_pipeline_result(self, pipeline_result: Dict[str, Any]) -> SentimentResult:
        """Convert pipeline result to our SentimentResult format."""
        label = pipeline_result.get("label", "NEUTRAL")
        confidence = pipeline_result.get("score", 0.5)
        
        # Map label to our format
        mapped_label = self.label_mapping.get(label, "neutral")
        
        # Convert confidence to raw score (-1.0 to 1.0)
        if mapped_label == "positive":
            raw_score = confidence
        elif mapped_label == "negative":
            raw_score = -confidence
        else:
            raw_score = 0.0
        
        return SentimentResult(
            label=mapped_label,
            score=confidence,
            raw_score=raw_score
        )
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[SentimentResult]:
        """Get cached sentiment result if still valid."""
        if cache_key in self._sentiment_cache:
            cached_data = self._sentiment_cache[cache_key]
            if datetime.utcnow().timestamp() - cached_data["timestamp"] < self._cache_ttl:
                return cached_data["result"]
            else:
                # Remove expired cache entry
                del self._sentiment_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: SentimentResult) -> None:
        """Cache sentiment result."""
        self._sentiment_cache[cache_key] = {
            "result": result,
            "timestamp": datetime.utcnow().timestamp()
        }
        
        # Simple cache cleanup - remove oldest entries if cache gets too large
        if len(self._sentiment_cache) > 1000:
            # Remove oldest 100 entries
            sorted_items = sorted(
                self._sentiment_cache.items(),
                key=lambda x: x[1]["timestamp"]
            )
            for key, _ in sorted_items[:100]:
                del self._sentiment_cache[key]


class SentimentService:
    """
    Service for managing sentiment analysis of news articles and generating sentiment timelines.
    """
    
    def __init__(self):
        self.analyzer = JapaneseSentimentAnalyzer()
    
    async def analyze_article_sentiment(self, article_id: str) -> Optional[SentimentResult]:
        """
        Analyze sentiment for a single news article.
        
        Args:
            article_id: UUID of the news article
            
        Returns:
            SentimentResult or None if article not found
        """
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(NewsArticle).where(NewsArticle.id == article_id)
                )
                article = result.scalar_one_or_none()
                
                if not article:
                    logger.warning(f"Article {article_id} not found")
                    return None
                
                # Combine headline and content for analysis
                text_to_analyze = f"{article.headline}"
                if article.content_summary:
                    text_to_analyze += f" {article.content_summary}"
                
                # Analyze sentiment
                sentiment_result = await self.analyzer.analyze_text(text_to_analyze)
                
                # Update article with sentiment data
                article.sentiment_label = sentiment_result.label
                article.sentiment_score = sentiment_result.raw_score
                
                await db.commit()
                
                logger.info(f"Updated sentiment for article {article_id}: {sentiment_result.label} ({sentiment_result.score:.3f})")
                
                return sentiment_result
                
        except Exception as e:
            logger.error(f"Error analyzing sentiment for article {article_id}: {e}")
            return None
    
    async def analyze_articles_batch(self, article_ids: List[str]) -> Dict[str, SentimentResult]:
        """
        Analyze sentiment for multiple articles in batch.
        
        Args:
            article_ids: List of article UUIDs
            
        Returns:
            Dictionary mapping article_id to SentimentResult
        """
        if not article_ids:
            return {}
        
        try:
            async with get_db() as db:
                # Fetch articles
                result = await db.execute(
                    select(NewsArticle).where(NewsArticle.id.in_(article_ids))
                )
                articles = result.scalars().all()
                
                if not articles:
                    return {}
                
                # Prepare texts for batch analysis
                texts = []
                article_map = {}
                
                for article in articles:
                    text_to_analyze = f"{article.headline}"
                    if article.content_summary:
                        text_to_analyze += f" {article.content_summary}"
                    
                    texts.append(text_to_analyze)
                    article_map[len(texts) - 1] = article
                
                # Perform batch sentiment analysis
                sentiment_results = await self.analyzer.analyze_batch(texts)
                
                # Update articles and prepare return data
                results = {}
                
                for i, sentiment_result in enumerate(sentiment_results):
                    article = article_map[i]
                    
                    # Update article
                    article.sentiment_label = sentiment_result.label
                    article.sentiment_score = sentiment_result.raw_score
                    
                    results[str(article.id)] = sentiment_result
                
                await db.commit()
                
                logger.info(f"Updated sentiment for {len(results)} articles")
                
                return results
                
        except Exception as e:
            logger.error(f"Error in batch sentiment analysis: {e}")
            return {}
    
    async def analyze_unprocessed_articles(self, limit: int = 100) -> int:
        """
        Analyze sentiment for articles that haven't been processed yet.
        
        Args:
            limit: Maximum number of articles to process
            
        Returns:
            Number of articles processed
        """
        try:
            async with get_db() as db:
                # Find articles without sentiment analysis
                result = await db.execute(
                    select(NewsArticle)
                    .where(NewsArticle.sentiment_label.is_(None))
                    .limit(limit)
                )
                articles = result.scalars().all()
                
                if not articles:
                    return 0
                
                article_ids = [str(article.id) for article in articles]
                
                # Process in batch
                await self.analyze_articles_batch(article_ids)
                
                return len(articles)
                
        except Exception as e:
            logger.error(f"Error analyzing unprocessed articles: {e}")
            return 0
    
    async def generate_sentiment_timeline(
        self,
        ticker: Optional[str] = None,
        days_back: int = 30,
        granularity: str = "daily"
    ) -> List[SentimentTimelinePoint]:
        """
        Generate sentiment timeline for a stock or general market.
        
        Args:
            ticker: Stock ticker (None for general market sentiment)
            days_back: Number of days to look back
            granularity: 'daily' or 'hourly'
            
        Returns:
            List of SentimentTimelinePoint objects
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days_back)
            
            async with get_db() as db:
                # Build base query
                if ticker:
                    # Stock-specific sentiment
                    query = (
                        select(NewsArticle)
                        .join(StockNewsLink)
                        .where(
                            and_(
                                StockNewsLink.ticker == ticker,
                                NewsArticle.published_at >= start_date.isoformat(),
                                NewsArticle.sentiment_label.isnot(None)
                            )
                        )
                    )
                else:
                    # General market sentiment
                    query = (
                        select(NewsArticle)
                        .where(
                            and_(
                                NewsArticle.published_at >= start_date.isoformat(),
                                NewsArticle.sentiment_label.isnot(None)
                            )
                        )
                    )
                
                result = await db.execute(query)
                articles = result.scalars().all()
                
                if not articles:
                    return []
                
                # Group articles by time period
                timeline_data = {}
                
                for article in articles:
                    try:
                        # Parse published date
                        pub_date = datetime.fromisoformat(article.published_at.replace("Z", "+00:00"))
                        pub_date = pub_date.replace(tzinfo=None)  # Remove timezone for consistency
                        
                        # Determine time bucket based on granularity
                        if granularity == "hourly":
                            time_bucket = pub_date.replace(minute=0, second=0, microsecond=0)
                        else:  # daily
                            time_bucket = pub_date.replace(hour=0, minute=0, second=0, microsecond=0)
                        
                        if time_bucket not in timeline_data:
                            timeline_data[time_bucket] = {
                                "positive": 0,
                                "negative": 0,
                                "neutral": 0,
                                "sentiment_scores": []
                            }
                        
                        # Count sentiment labels
                        timeline_data[time_bucket][article.sentiment_label] += 1
                        
                        # Collect sentiment scores for average calculation
                        if article.sentiment_score is not None:
                            timeline_data[time_bucket]["sentiment_scores"].append(float(article.sentiment_score))
                    
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing date for article {article.id}: {e}")
                        continue
                
                # Convert to timeline points
                timeline_points = []
                
                for date, data in sorted(timeline_data.items()):
                    avg_sentiment = 0.0
                    if data["sentiment_scores"]:
                        avg_sentiment = sum(data["sentiment_scores"]) / len(data["sentiment_scores"])
                    
                    total_articles = data["positive"] + data["negative"] + data["neutral"]
                    
                    timeline_point = SentimentTimelinePoint(
                        date=date,
                        positive_count=data["positive"],
                        negative_count=data["negative"],
                        neutral_count=data["neutral"],
                        avg_sentiment_score=avg_sentiment,
                        total_articles=total_articles
                    )
                    
                    timeline_points.append(timeline_point)
                
                return timeline_points
                
        except Exception as e:
            logger.error(f"Error generating sentiment timeline: {e}")
            return []
    
    async def get_sentiment_summary(
        self,
        ticker: Optional[str] = None,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """
        Get sentiment summary for recent articles.
        
        Args:
            ticker: Stock ticker (None for general market)
            hours_back: Number of hours to look back
            
        Returns:
            Dictionary with sentiment summary statistics
        """
        try:
            start_date = datetime.utcnow() - timedelta(hours=hours_back)
            
            async with get_db() as db:
                # Build query
                if ticker:
                    query = (
                        select(NewsArticle)
                        .join(StockNewsLink)
                        .where(
                            and_(
                                StockNewsLink.ticker == ticker,
                                NewsArticle.published_at >= start_date.isoformat(),
                                NewsArticle.sentiment_label.isnot(None)
                            )
                        )
                    )
                else:
                    query = (
                        select(NewsArticle)
                        .where(
                            and_(
                                NewsArticle.published_at >= start_date.isoformat(),
                                NewsArticle.sentiment_label.isnot(None)
                            )
                        )
                    )
                
                result = await db.execute(query)
                articles = result.scalars().all()
                
                if not articles:
                    return {
                        "total_articles": 0,
                        "positive_count": 0,
                        "negative_count": 0,
                        "neutral_count": 0,
                        "positive_percentage": 0.0,
                        "negative_percentage": 0.0,
                        "neutral_percentage": 0.0,
                        "avg_sentiment_score": 0.0,
                        "sentiment_trend": "neutral"
                    }
                
                # Calculate statistics
                positive_count = sum(1 for a in articles if a.sentiment_label == "positive")
                negative_count = sum(1 for a in articles if a.sentiment_label == "negative")
                neutral_count = sum(1 for a in articles if a.sentiment_label == "neutral")
                total_articles = len(articles)
                
                # Calculate percentages
                positive_pct = (positive_count / total_articles) * 100
                negative_pct = (negative_count / total_articles) * 100
                neutral_pct = (neutral_count / total_articles) * 100
                
                # Calculate average sentiment score
                sentiment_scores = [float(a.sentiment_score) for a in articles if a.sentiment_score is not None]
                avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
                
                # Determine overall trend
                if positive_count > negative_count and positive_pct > 40:
                    trend = "positive"
                elif negative_count > positive_count and negative_pct > 40:
                    trend = "negative"
                else:
                    trend = "neutral"
                
                return {
                    "total_articles": total_articles,
                    "positive_count": positive_count,
                    "negative_count": negative_count,
                    "neutral_count": neutral_count,
                    "positive_percentage": round(positive_pct, 1),
                    "negative_percentage": round(negative_pct, 1),
                    "neutral_percentage": round(neutral_pct, 1),
                    "avg_sentiment_score": round(avg_sentiment, 3),
                    "sentiment_trend": trend,
                    "hours_analyzed": hours_back,
                    "ticker": ticker
                }
                
        except Exception as e:
            logger.error(f"Error getting sentiment summary: {e}")
            return {}


# Global service instance
sentiment_service = SentimentService()