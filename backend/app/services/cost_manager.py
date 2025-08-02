"""
Cost management service for AI analysis operations.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Optional, List, Any
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.models.logs import APIUsageLog

logger = logging.getLogger(__name__)


class CostManager:
    """Manages AI analysis costs and budget tracking."""
    
    def __init__(self, db: Optional[Session] = None):
        """Initialize cost manager."""
        self.db = db
        self.daily_budget = settings.DAILY_AI_BUDGET_USD
        self.monthly_budget = settings.MONTHLY_AI_BUDGET_USD
        self.emergency_buffer = 50.0  # Emergency buffer in USD
        
        # Cache thresholds
        self.cache_thresholds = {
            "market_hours": 300,      # 5 minutes during market hours
            "after_hours": 1800,      # 30 minutes after hours
            "weekend": 3600,          # 1 hour on weekends
            "high_cost": 900          # 15 minutes for expensive analyses
        }
    
    async def can_afford(self, estimated_cost: float) -> bool:
        """Check if we can afford the estimated cost."""
        try:
            # Get current usage
            daily_usage = await self._get_daily_usage()
            monthly_usage = await self._get_monthly_usage()
            
            # Check daily budget
            if daily_usage + estimated_cost > self.daily_budget:
                logger.warning(
                    f"Daily budget exceeded. Usage: ${daily_usage:.4f}, "
                    f"Estimated: ${estimated_cost:.4f}, Budget: ${self.daily_budget}"
                )
                return False
            
            # Check monthly budget
            if monthly_usage + estimated_cost > self.monthly_budget:
                logger.warning(
                    f"Monthly budget exceeded. Usage: ${monthly_usage:.4f}, "
                    f"Estimated: ${estimated_cost:.4f}, Budget: ${self.monthly_budget}"
                )
                return False
            
            # Check emergency buffer
            remaining_daily = self.daily_budget - daily_usage
            if remaining_daily < self.emergency_buffer and estimated_cost > remaining_daily * 0.5:
                logger.warning(
                    f"Emergency buffer protection. Remaining: ${remaining_daily:.4f}, "
                    f"Estimated: ${estimated_cost:.4f}"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking budget: {str(e)}")
            # Fail safe - allow if we can't check
            return True
    
    async def record_usage(
        self, 
        ticker: str, 
        cost: float,
        api_provider: str = "google_gemini",
        endpoint: str = "generate_content",
        response_time_ms: Optional[int] = None
    ):
        """Record API usage for cost tracking."""
        if not self.db:
            logger.warning("No database session available for cost tracking")
            return
        
        try:
            usage_log = APIUsageLog(
                api_provider=api_provider,
                endpoint=endpoint,
                request_type=f"analysis_{ticker}",
                cost_usd=Decimal(str(cost)),
                response_time_ms=response_time_ms,
                status_code=200,
                request_timestamp=datetime.now()
            )
            
            self.db.add(usage_log)
            self.db.commit()
            
            logger.info(f"Recorded usage: {ticker} - ${cost:.4f}")
            
        except Exception as e:
            logger.error(f"Error recording usage: {str(e)}")
            self.db.rollback()
    
    async def should_use_cache(
        self, 
        ticker: str, 
        last_generated: datetime,
        analysis_cost: Optional[float] = None
    ) -> bool:
        """Determine if cached analysis should be used based on cost and time."""
        try:
            now = datetime.now()
            time_diff = (now - last_generated).total_seconds()
            
            # Determine cache threshold based on market conditions
            threshold = self._get_cache_threshold(now, analysis_cost)
            
            # Use cache if within threshold
            if time_diff < threshold:
                logger.info(
                    f"Using cache for {ticker}. Age: {time_diff:.0f}s, "
                    f"Threshold: {threshold:.0f}s"
                )
                return True
            
            # Check if we're approaching budget limits
            daily_usage = await self._get_daily_usage()
            daily_remaining = self.daily_budget - daily_usage
            
            # If low on budget, extend cache usage
            if daily_remaining < self.emergency_buffer:
                extended_threshold = threshold * 2
                if time_diff < extended_threshold:
                    logger.info(
                        f"Extended cache usage for {ticker} due to budget constraints. "
                        f"Age: {time_diff:.0f}s, Extended threshold: {extended_threshold:.0f}s"
                    )
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking cache policy: {str(e)}")
            # Default to not using cache if error
            return False
    
    def _get_cache_threshold(self, current_time: datetime, analysis_cost: Optional[float] = None) -> int:
        """Get cache threshold based on market conditions and cost."""
        # Check if it's weekend
        if current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return self.cache_thresholds["weekend"]
        
        # Check if it's market hours (9:00-15:00 JST)
        # Note: This is simplified - real implementation should handle timezone properly
        hour = current_time.hour
        if 9 <= hour <= 15:
            threshold = self.cache_thresholds["market_hours"]
        else:
            threshold = self.cache_thresholds["after_hours"]
        
        # Adjust for high-cost analyses
        if analysis_cost and analysis_cost > 0.01:  # High cost threshold
            threshold = min(threshold, self.cache_thresholds["high_cost"])
        
        return threshold
    
    async def _get_daily_usage(self) -> float:
        """Get today's API usage cost."""
        if not self.db:
            return 0.0
        
        try:
            today = date.today()
            result = self.db.query(
                func.sum(APIUsageLog.cost_usd)
            ).filter(
                func.date(APIUsageLog.request_timestamp) == today,
                APIUsageLog.api_provider == "google_gemini"
            ).scalar()
            
            return float(result or 0)
            
        except Exception as e:
            logger.error(f"Error getting daily usage: {str(e)}")
            return 0.0
    
    async def _get_monthly_usage(self) -> float:
        """Get this month's API usage cost."""
        if not self.db:
            return 0.0
        
        try:
            today = date.today()
            month_start = today.replace(day=1)
            
            result = self.db.query(
                func.sum(APIUsageLog.cost_usd)
            ).filter(
                APIUsageLog.request_timestamp >= month_start,
                APIUsageLog.api_provider == "google_gemini"
            ).scalar()
            
            return float(result or 0)
            
        except Exception as e:
            logger.error(f"Error getting monthly usage: {str(e)}")
            return 0.0
    
    async def get_usage_stats(self) -> Dict[str, float]:
        """Get usage statistics."""
        try:
            daily_usage = await self._get_daily_usage()
            monthly_usage = await self._get_monthly_usage()
            
            return {
                "daily_usage": daily_usage,
                "daily_budget": self.daily_budget,
                "daily_remaining": max(0, self.daily_budget - daily_usage),
                "daily_usage_percent": (daily_usage / self.daily_budget) * 100,
                "monthly_usage": monthly_usage,
                "monthly_budget": self.monthly_budget,
                "monthly_remaining": max(0, self.monthly_budget - monthly_usage),
                "monthly_usage_percent": (monthly_usage / self.monthly_budget) * 100
            }
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {str(e)}")
            return {
                "daily_usage": 0.0,
                "daily_budget": self.daily_budget,
                "daily_remaining": self.daily_budget,
                "daily_usage_percent": 0.0,
                "monthly_usage": 0.0,
                "monthly_budget": self.monthly_budget,
                "monthly_remaining": self.monthly_budget,
                "monthly_usage_percent": 0.0
            }
    
    def estimate_analysis_cost(
        self, 
        analysis_type: str,
        data_complexity: str = "medium"
    ) -> float:
        """Estimate cost for different analysis types."""
        # Base costs by analysis type (in USD)
        base_costs = {
            "short_term": 0.005,
            "mid_term": 0.008,
            "long_term": 0.012,
            "comprehensive": 0.020
        }
        
        # Complexity multipliers
        complexity_multipliers = {
            "low": 0.7,
            "medium": 1.0,
            "high": 1.5,
            "very_high": 2.0
        }
        
        base_cost = base_costs.get(analysis_type, 0.010)
        multiplier = complexity_multipliers.get(data_complexity, 1.0)
        
        return base_cost * multiplier
    
    async def get_budget_alerts(self) -> List[Dict[str, Any]]:
        """Get budget alerts if approaching limits."""
        alerts = []
        
        try:
            stats = await self.get_usage_stats()
            
            # Daily budget alerts
            if stats["daily_usage_percent"] >= 90:
                alerts.append({
                    "type": "critical",
                    "message": f"Daily budget 90% used: ${stats['daily_usage']:.2f}/${stats['daily_budget']:.2f}",
                    "remaining": stats["daily_remaining"]
                })
            elif stats["daily_usage_percent"] >= 75:
                alerts.append({
                    "type": "warning", 
                    "message": f"Daily budget 75% used: ${stats['daily_usage']:.2f}/${stats['daily_budget']:.2f}",
                    "remaining": stats["daily_remaining"]
                })
            
            # Monthly budget alerts
            if stats["monthly_usage_percent"] >= 90:
                alerts.append({
                    "type": "critical",
                    "message": f"Monthly budget 90% used: ${stats['monthly_usage']:.2f}/${stats['monthly_budget']:.2f}",
                    "remaining": stats["monthly_remaining"]
                })
            elif stats["monthly_usage_percent"] >= 75:
                alerts.append({
                    "type": "warning",
                    "message": f"Monthly budget 75% used: ${stats['monthly_usage']:.2f}/${stats['monthly_budget']:.2f}",
                    "remaining": stats["monthly_remaining"]
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting budget alerts: {str(e)}")
            return []


class IntelligentCacheManager:
    """Manages intelligent caching for AI analysis."""
    
    def __init__(self):
        """Initialize cache manager."""
        self.cache_policies = {
            "stock_prices": {"ttl": 300, "priority": "high"},      # 5 minutes
            "financial_data": {"ttl": 86400, "priority": "high"},  # 24 hours
            "news_data": {"ttl": 3600, "priority": "medium"},      # 1 hour
            "analysis_data": {"ttl": 1800, "priority": "high"},    # 30 minutes
            "macro_data": {"ttl": 21600, "priority": "low"}        # 6 hours
        }
    
    def get_cache_ttl(self, data_type: str, market_conditions: Dict[str, Any] = None) -> int:
        """Get cache TTL based on data type and market conditions."""
        base_ttl = self.cache_policies.get(data_type, {}).get("ttl", 3600)
        
        if not market_conditions:
            return base_ttl
        
        # Adjust TTL based on market volatility
        volatility = market_conditions.get("volatility", "normal")
        if volatility == "high":
            return int(base_ttl * 0.5)  # Shorter cache during high volatility
        elif volatility == "low":
            return int(base_ttl * 1.5)  # Longer cache during low volatility
        
        return base_ttl
    
    def should_invalidate_cache(
        self, 
        data_type: str, 
        last_update: datetime,
        trigger_events: List[str] = None
    ) -> bool:
        """Determine if cache should be invalidated based on events."""
        # Market-moving events that should invalidate cache
        invalidation_triggers = {
            "earnings_announcement",
            "dividend_announcement", 
            "major_news_event",
            "market_crash",
            "regulatory_change"
        }
        
        if trigger_events:
            for event in trigger_events:
                if event in invalidation_triggers:
                    logger.info(f"Cache invalidated due to event: {event}")
                    return True
        
        return False