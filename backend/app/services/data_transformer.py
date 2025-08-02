"""
Data transformation service for converting raw data into LLM-friendly format.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import json

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.models.stock import Stock, StockPriceHistory, StockDailyMetrics
from app.models.financial import FinancialReport, FinancialReportLineItem
from app.models.news import NewsArticle, StockNewsLink
from app.services.stock_service import StockService
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)


class TechnicalIndicatorCalculator:
    """Calculates technical indicators for stock analysis."""
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return []
        
        sma = []
        for i in range(period - 1, len(prices)):
            avg = sum(prices[i - period + 1:i + 1]) / period
            sma.append(round(avg, 2))
        
        return sma
    
    @staticmethod
    def calculate_price_momentum(prices: List[float], period: int = 10) -> List[float]:
        """Calculate price momentum (rate of change)."""
        if len(prices) < period + 1:
            return []
        
        momentum = []
        for i in range(period, len(prices)):
            current_price = prices[i]
            past_price = prices[i - period]
            if past_price != 0:
                momentum_value = ((current_price - past_price) / past_price) * 100
                momentum.append(round(momentum_value, 2))
            else:
                momentum.append(0.0)
        
        return momentum
    
    @staticmethod
    def calculate_volatility(prices: List[float], period: int = 20) -> List[float]:
        """Calculate rolling volatility (standard deviation)."""
        if len(prices) < period:
            return []
        
        volatility = []
        for i in range(period - 1, len(prices)):
            price_slice = prices[i - period + 1:i + 1]
            std_dev = np.std(price_slice)
            volatility.append(round(std_dev, 2))
        
        return volatility
    
    @staticmethod
    def calculate_support_resistance(prices: List[float], window: int = 20) -> Dict[str, float]:
        """Calculate support and resistance levels."""
        if len(prices) < window:
            return {"support": 0.0, "resistance": 0.0}
        
        recent_prices = prices[-window:]
        support = min(recent_prices)
        resistance = max(recent_prices)
        
        return {
            "support": round(support, 2),
            "resistance": round(resistance, 2)
        }
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return []
        
        multiplier = 2 / (period + 1)
        ema = [prices[0]]  # Start with first price
        
        for i in range(1, len(prices)):
            ema_value = (prices[i] * multiplier) + (ema[-1] * (1 - multiplier))
            ema.append(round(ema_value, 2))
        
        return ema
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return []
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        # Calculate initial average gain and loss
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        rsi = []
        for i in range(period, len(gains)):
            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi_value = 100 - (100 / (1 + rs))
                rsi.append(round(rsi_value, 2))
            
            # Update averages
            avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
        
        return rsi
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float], 
        period: int = 20, 
        std_dev: float = 2
    ) -> Dict[str, List[float]]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return {"upper": [], "middle": [], "lower": []}
        
        sma = TechnicalIndicatorCalculator.calculate_sma(prices, period)
        
        upper_band = []
        lower_band = []
        
        for i in range(period - 1, len(prices)):
            price_slice = prices[i - period + 1:i + 1]
            std = np.std(price_slice)
            
            upper_band.append(round(sma[i - period + 1] + (std_dev * std), 2))
            lower_band.append(round(sma[i - period + 1] - (std_dev * std), 2))
        
        return {
            "upper": upper_band,
            "middle": sma,
            "lower": lower_band
        }
    
    @staticmethod
    def calculate_macd(
        prices: List[float], 
        fast_period: int = 12, 
        slow_period: int = 26, 
        signal_period: int = 9
    ) -> Dict[str, List[float]]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        if len(prices) < slow_period:
            return {"macd": [], "signal": [], "histogram": []}
        
        ema_fast = TechnicalIndicatorCalculator.calculate_ema(prices, fast_period)
        ema_slow = TechnicalIndicatorCalculator.calculate_ema(prices, slow_period)
        
        # Align EMAs (slow EMA starts later)
        start_idx = slow_period - fast_period
        ema_fast_aligned = ema_fast[start_idx:]
        
        # Calculate MACD line
        macd = [fast - slow for fast, slow in zip(ema_fast_aligned, ema_slow)]
        
        # Calculate signal line (EMA of MACD)
        signal = TechnicalIndicatorCalculator.calculate_ema(macd, signal_period)
        
        # Calculate histogram (MACD - Signal)
        histogram_start = len(macd) - len(signal)
        macd_aligned = macd[histogram_start:]
        histogram = [m - s for m, s in zip(macd_aligned, signal)]
        
        return {
            "macd": [round(x, 4) for x in macd],
            "signal": [round(x, 4) for x in signal],
            "histogram": [round(x, 4) for x in histogram]
        }


class DataTransformer:
    """Transforms raw data into LLM-friendly format for analysis."""
    
    def __init__(self, db: Optional[Session] = None):
        """Initialize data transformer."""
        self.db = db
        self.stock_service = StockService(db) if db else None
        self.news_service = NewsService(db) if db else None
        self.indicator_calc = TechnicalIndicatorCalculator()
    
    async def prepare_analysis_context(
        self, 
        ticker: str, 
        analysis_type: str
    ) -> Dict[str, Any]:
        """Prepare comprehensive analysis context for LLM."""
        try:
            context = {
                "ticker": ticker,
                "analysis_type": analysis_type,
                "company_name": await self._get_company_name(ticker),
                "analysis_timestamp": datetime.now().isoformat(),
                "data_sources": []
            }
            
            # Add data based on analysis type with enhanced context
            if analysis_type in ["short_term", "comprehensive"]:
                technical_context = await self._prepare_technical_context(ticker)
                context.update(technical_context)
                context["data_sources"].append("technical_indicators")
                
                # Add momentum analysis for short-term
                momentum_context = await self._prepare_momentum_context(ticker)
                context.update(momentum_context)
                context["data_sources"].append("momentum_analysis")
            
            if analysis_type in ["mid_term", "long_term", "comprehensive"]:
                fundamental_context = await self._prepare_fundamental_context(ticker)
                context.update(fundamental_context)
                context["data_sources"].append("fundamental_data")
                
                # Add growth analysis for mid/long-term
                growth_context = await self._prepare_growth_context(ticker)
                context.update(growth_context)
                context["data_sources"].append("growth_analysis")
            
            if analysis_type in ["short_term", "mid_term", "comprehensive"]:
                news_context = await self._prepare_news_sentiment_context(ticker)
                context.update(news_context)
                context["data_sources"].append("news_sentiment")
            
            if analysis_type in ["long_term", "comprehensive"]:
                macro_context = await self._prepare_macro_context()
                context.update(macro_context)
                context["data_sources"].append("macro_environment")
                
                # Add valuation context for long-term
                valuation_context = await self._prepare_valuation_context(ticker)
                context.update(valuation_context)
                context["data_sources"].append("valuation_metrics")
            
            # Add market context for all analysis types
            market_context = await self._prepare_market_context(ticker)
            context.update(market_context)
            context["data_sources"].append("market_context")
            
            # Generate analysis summary
            context["analysis_summary"] = self._generate_analysis_summary(context, analysis_type)
            
            return context
            
        except Exception as e:
            logger.error(f"Error preparing analysis context for {ticker}: {str(e)}")
            raise DataTransformationException(f"Failed to prepare context: {str(e)}")
    
    async def _get_company_name(self, ticker: str) -> str:
        """Get company name for ticker."""
        if not self.stock_service:
            return ticker
        
        try:
            stock = await self.stock_service.get_stock_by_ticker(ticker)
            return stock.company_name_jp if stock else ticker
        except Exception:
            return ticker
    
    async def _prepare_technical_context(self, ticker: str) -> Dict[str, Any]:
        """Prepare technical analysis context."""
        try:
            # Get price history (last 100 days)
            end_date = date.today()
            start_date = end_date - timedelta(days=100)
            
            price_data = await self._get_price_history(ticker, start_date, end_date)
            
            if not price_data:
                return {"price_data": "No price data available"}
            
            # Extract price lists
            closes = [float(p["close"]) for p in price_data]
            highs = [float(p["high"]) for p in price_data]
            lows = [float(p["low"]) for p in price_data]
            volumes = [int(p["volume"]) for p in price_data]
            dates = [p["date"] for p in price_data]
            
            # Calculate comprehensive technical indicators
            sma_5 = self.indicator_calc.calculate_sma(closes, 5)
            sma_20 = self.indicator_calc.calculate_sma(closes, 20)
            sma_50 = self.indicator_calc.calculate_sma(closes, 50)
            ema_12 = self.indicator_calc.calculate_ema(closes, 12)
            ema_26 = self.indicator_calc.calculate_ema(closes, 26)
            rsi = self.indicator_calc.calculate_rsi(closes)
            bollinger = self.indicator_calc.calculate_bollinger_bands(closes)
            macd = self.indicator_calc.calculate_macd(closes)
            momentum = self.indicator_calc.calculate_price_momentum(closes)
            volatility = self.indicator_calc.calculate_volatility(closes)
            support_resistance = self.indicator_calc.calculate_support_resistance(closes)
            
            # Recent price action (last 10 days)
            recent_prices = price_data[-10:] if len(price_data) >= 10 else price_data
            
            # Volume analysis
            avg_volume_20 = sum(volumes[-20:]) / min(20, len(volumes)) if volumes else 0
            avg_volume_5 = sum(volumes[-5:]) / min(5, len(volumes)) if volumes else 0
            recent_volume = volumes[-1] if volumes else 0
            volume_ratio = recent_volume / avg_volume_20 if avg_volume_20 > 0 else 1
            
            # Price trend analysis
            current_price = closes[-1] if closes else 0
            price_change_1d = ((closes[-1] - closes[-2]) / closes[-2] * 100) if len(closes) >= 2 else 0
            price_change_5d = ((closes[-1] - closes[-6]) / closes[-6] * 100) if len(closes) >= 6 else 0
            price_change_20d = ((closes[-1] - closes[-21]) / closes[-21] * 100) if len(closes) >= 21 else 0
            
            # Technical signals
            technical_signals = self._analyze_technical_signals(
                closes, sma_20, sma_50, rsi, macd, bollinger
            )
            
            return {
                "price_data": self._format_price_data(recent_prices),
                "current_price": current_price,
                "price_changes": {
                    "1_day": round(price_change_1d, 2),
                    "5_day": round(price_change_5d, 2),
                    "20_day": round(price_change_20d, 2)
                },
                "technical_indicators": {
                    "sma_5": sma_5[-5:] if sma_5 else [],
                    "sma_20": sma_20[-5:] if sma_20 else [],
                    "sma_50": sma_50[-5:] if sma_50 else [],
                    "ema_12": ema_12[-5:] if ema_12 else [],
                    "ema_26": ema_26[-5:] if ema_26 else [],
                    "rsi": rsi[-5:] if rsi else [],
                    "momentum": momentum[-5:] if momentum else [],
                    "volatility": volatility[-5:] if volatility else [],
                    "bollinger_bands": {
                        "upper": bollinger["upper"][-5:] if bollinger["upper"] else [],
                        "middle": bollinger["middle"][-5:] if bollinger["middle"] else [],
                        "lower": bollinger["lower"][-5:] if bollinger["lower"] else []
                    },
                    "macd": {
                        "macd": macd["macd"][-5:] if macd["macd"] else [],
                        "signal": macd["signal"][-5:] if macd["signal"] else [],
                        "histogram": macd["histogram"][-5:] if macd["histogram"] else []
                    }
                },
                "support_resistance": support_resistance,
                "volume_analysis": {
                    "recent_volume": recent_volume,
                    "average_volume_20d": round(avg_volume_20),
                    "average_volume_5d": round(avg_volume_5),
                    "volume_ratio": round(volume_ratio, 2),
                    "volume_trend": "高い" if volume_ratio > 1.5 else "普通" if volume_ratio > 0.5 else "低い"
                },
                "technical_signals": technical_signals,
                "technical_summary": self._generate_technical_summary(
                    current_price, price_change_1d, rsi, technical_signals
                )
            }
            
        except Exception as e:
            logger.error(f"Error preparing technical context: {str(e)}")
            return {"price_data": f"Error loading price data: {str(e)}"}
    
    async def _prepare_fundamental_context(self, ticker: str) -> Dict[str, Any]:
        """Prepare fundamental analysis context."""
        try:
            # Get financial data
            financial_data = await self._get_financial_data(ticker)
            
            if not financial_data:
                return {"financial_data": "No financial data available"}
            
            # Get daily metrics (P/E, P/B, etc.)
            daily_metrics = await self._get_daily_metrics(ticker)
            
            # Calculate financial ratios and trends
            financial_summary = self._analyze_financial_trends(financial_data)
            
            return {
                "financial_data": financial_summary,
                "valuation_metrics": daily_metrics,
                "quarterly_trends": self._analyze_quarterly_trends(financial_data),
                "peer_comparison": await self._get_peer_comparison(ticker),
                "industry_trends": await self._get_industry_trends(ticker)
            }
            
        except Exception as e:
            logger.error(f"Error preparing fundamental context: {str(e)}")
            return {"financial_data": f"Error loading financial data: {str(e)}"}
    
    async def _prepare_news_sentiment_context(self, ticker: str) -> Dict[str, Any]:
        """Prepare news and sentiment context."""
        try:
            # Get recent news (last 30 days)
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            news_data = await self._get_news_data(ticker, start_date, end_date)
            
            if not news_data:
                return {"news_sentiment": "No recent news available"}
            
            # Analyze sentiment trends
            sentiment_analysis = self._analyze_sentiment_trends(news_data)
            
            return {
                "news_sentiment": sentiment_analysis,
                "recent_news": self._format_recent_news(news_data[:5])  # Top 5 news
            }
            
        except Exception as e:
            logger.error(f"Error preparing news sentiment context: {str(e)}")
            return {"news_sentiment": f"Error loading news data: {str(e)}"}
    
    async def _prepare_macro_context(self) -> Dict[str, Any]:
        """Prepare macroeconomic context."""
        try:
            # This would typically fetch from external APIs
            # For now, return placeholder data
            return {
                "macro_environment": {
                    "market_sentiment": "中立",
                    "interest_rates": "低金利環境継続",
                    "inflation": "インフレ圧力は限定的",
                    "currency": "円安傾向",
                    "global_markets": "米国市場は堅調"
                }
            }
            
        except Exception as e:
            logger.error(f"Error preparing macro context: {str(e)}")
            return {"macro_environment": "Macro data unavailable"}
    
    async def _get_price_history(
        self, 
        ticker: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get price history from database."""
        if not self.db:
            return []
        
        try:
            price_records = self.db.query(StockPriceHistory).filter(
                StockPriceHistory.ticker == ticker,
                StockPriceHistory.date >= start_date,
                StockPriceHistory.date <= end_date
            ).order_by(StockPriceHistory.date).all()
            
            return [
                {
                    "date": record.date.isoformat(),
                    "open": float(record.open),
                    "high": float(record.high),
                    "low": float(record.low),
                    "close": float(record.close),
                    "volume": record.volume
                }
                for record in price_records
            ]
            
        except Exception as e:
            logger.error(f"Error getting price history: {str(e)}")
            return []
    
    async def _get_financial_data(self, ticker: str) -> List[Dict[str, Any]]:
        """Get financial data from database."""
        if not self.db:
            return []
        
        try:
            # Get recent financial reports
            reports = self.db.query(FinancialReport).filter(
                FinancialReport.ticker == ticker
            ).order_by(
                FinancialReport.fiscal_year.desc(),
                FinancialReport.fiscal_period.desc()
            ).limit(8).all()  # Last 8 quarters
            
            financial_data = []
            for report in reports:
                # Get line items for this report
                line_items = self.db.query(FinancialReportLineItem).filter(
                    FinancialReportLineItem.report_id == report.id
                ).all()
                
                metrics = {item.metric_name: float(item.metric_value) for item in line_items}
                
                financial_data.append({
                    "fiscal_year": report.fiscal_year,
                    "fiscal_period": report.fiscal_period,
                    "report_type": report.report_type,
                    "announced_at": report.announced_at.isoformat(),
                    "metrics": metrics
                })
            
            return financial_data
            
        except Exception as e:
            logger.error(f"Error getting financial data: {str(e)}")
            return []
    
    async def _get_daily_metrics(self, ticker: str) -> Dict[str, Any]:
        """Get latest daily metrics."""
        if not self.db:
            return {}
        
        try:
            latest_metrics = self.db.query(StockDailyMetrics).filter(
                StockDailyMetrics.ticker == ticker
            ).order_by(StockDailyMetrics.date.desc()).first()
            
            if not latest_metrics:
                return {}
            
            return {
                "date": latest_metrics.date.isoformat(),
                "market_cap": int(latest_metrics.market_cap) if latest_metrics.market_cap else None,
                "pe_ratio": float(latest_metrics.pe_ratio) if latest_metrics.pe_ratio else None,
                "pb_ratio": float(latest_metrics.pb_ratio) if latest_metrics.pb_ratio else None,
                "dividend_yield": float(latest_metrics.dividend_yield) if latest_metrics.dividend_yield else None,
                "shares_outstanding": int(latest_metrics.shares_outstanding) if latest_metrics.shares_outstanding else None
            }
            
        except Exception as e:
            logger.error(f"Error getting daily metrics: {str(e)}")
            return {}
    
    async def _get_news_data(
        self, 
        ticker: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get news data from database."""
        if not self.db:
            return []
        
        try:
            # Get news articles linked to this stock
            news_query = self.db.query(NewsArticle).join(
                StockNewsLink, NewsArticle.id == StockNewsLink.article_id
            ).filter(
                StockNewsLink.ticker == ticker,
                NewsArticle.published_at >= start_date,
                NewsArticle.published_at <= end_date
            ).order_by(NewsArticle.published_at.desc())
            
            news_records = news_query.all()
            
            return [
                {
                    "headline": record.headline,
                    "content_summary": record.content_summary,
                    "source": record.source,
                    "published_at": record.published_at.isoformat(),
                    "sentiment_label": record.sentiment_label,
                    "sentiment_score": float(record.sentiment_score) if record.sentiment_score else 0.0
                }
                for record in news_records
            ]
            
        except Exception as e:
            logger.error(f"Error getting news data: {str(e)}")
            return []
    
    def _format_price_data(self, price_data: List[Dict[str, Any]]) -> str:
        """Format price data for LLM consumption."""
        if not price_data:
            return "価格データなし"
        
        formatted = "最近の株価データ:\n"
        for data in price_data[-5:]:  # Last 5 days
            formatted += f"日付: {data['date']}, 終値: ¥{data['close']}, 出来高: {data['volume']:,}\n"
        
        # Add price change
        if len(price_data) >= 2:
            latest = price_data[-1]
            previous = price_data[-2]
            change = latest['close'] - previous['close']
            change_pct = (change / previous['close']) * 100
            formatted += f"前日比: {change:+.2f} ({change_pct:+.2f}%)\n"
        
        return formatted
    
    def _analyze_financial_trends(self, financial_data: List[Dict[str, Any]]) -> str:
        """Analyze financial trends."""
        if not financial_data:
            return "財務データなし"
        
        # Extract key metrics trends
        revenues = []
        profits = []
        
        for data in financial_data:
            metrics = data.get("metrics", {})
            if "revenue" in metrics:
                revenues.append(metrics["revenue"])
            if "net_income" in metrics:
                profits.append(metrics["net_income"])
        
        analysis = "財務トレンド分析:\n"
        
        if revenues:
            if len(revenues) >= 2:
                revenue_trend = "増収" if revenues[0] > revenues[1] else "減収"
                analysis += f"売上高: {revenue_trend}傾向\n"
        
        if profits:
            if len(profits) >= 2:
                profit_trend = "増益" if profits[0] > profits[1] else "減益"
                analysis += f"純利益: {profit_trend}傾向\n"
        
        return analysis
    
    def _analyze_quarterly_trends(self, financial_data: List[Dict[str, Any]]) -> str:
        """Analyze quarterly trends."""
        if not financial_data:
            return "四半期データなし"
        
        quarterly_data = [d for d in financial_data if d.get("report_type") == "quarterly"]
        
        if len(quarterly_data) < 2:
            return "四半期比較データ不足"
        
        return f"直近四半期: {quarterly_data[0]['fiscal_year']}年{quarterly_data[0]['fiscal_period']}"
    
    def _analyze_sentiment_trends(self, news_data: List[Dict[str, Any]]) -> str:
        """Analyze sentiment trends from news."""
        if not news_data:
            return "ニュースデータなし"
        
        # Calculate sentiment distribution
        sentiments = [news.get("sentiment_label", "neutral") for news in news_data]
        positive_count = sentiments.count("positive")
        negative_count = sentiments.count("negative")
        neutral_count = sentiments.count("neutral")
        
        total = len(sentiments)
        if total == 0:
            return "センチメントデータなし"
        
        positive_pct = (positive_count / total) * 100
        negative_pct = (negative_count / total) * 100
        
        overall_sentiment = "ポジティブ" if positive_pct > negative_pct else "ネガティブ" if negative_pct > positive_pct else "中立"
        
        return f"ニュースセンチメント: {overall_sentiment} (ポジティブ: {positive_pct:.1f}%, ネガティブ: {negative_pct:.1f}%)"
    
    def _format_recent_news(self, news_data: List[Dict[str, Any]]) -> str:
        """Format recent news for LLM."""
        if not news_data:
            return "最近のニュースなし"
        
        formatted = "最近の関連ニュース:\n"
        for news in news_data:
            sentiment_emoji = "📈" if news.get("sentiment_label") == "positive" else "📉" if news.get("sentiment_label") == "negative" else "📊"
            formatted += f"{sentiment_emoji} {news['headline']} ({news['source']}, {news['published_at'][:10]})\n"
        
        return formatted
    
    async def _get_peer_comparison(self, ticker: str) -> str:
        """Get peer comparison data."""
        # Placeholder - would implement peer analysis
        return "同業他社比較データは準備中"
    
    async def _get_industry_trends(self, ticker: str) -> str:
        """Get industry trends."""
        # Placeholder - would implement industry analysis
        return "業界トレンドデータは準備中"
    
    async def _prepare_momentum_context(self, ticker: str) -> Dict[str, Any]:
        """Prepare momentum analysis context for short-term analysis."""
        try:
            # Get recent price data (last 30 days)
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            price_data = await self._get_price_history(ticker, start_date, end_date)
            
            if not price_data:
                return {"momentum_analysis": "No price data for momentum analysis"}
            
            closes = [float(p["close"]) for p in price_data]
            volumes = [int(p["volume"]) for p in price_data]
            
            # Calculate momentum indicators
            momentum_10 = self.indicator_calc.calculate_price_momentum(closes, 10)
            momentum_5 = self.indicator_calc.calculate_price_momentum(closes, 5)
            
            # Volume momentum
            volume_momentum = []
            if len(volumes) >= 10:
                for i in range(10, len(volumes)):
                    recent_avg = sum(volumes[i-5:i]) / 5
                    past_avg = sum(volumes[i-10:i-5]) / 5
                    if past_avg > 0:
                        vol_momentum = ((recent_avg - past_avg) / past_avg) * 100
                        volume_momentum.append(round(vol_momentum, 2))
            
            return {
                "momentum_analysis": {
                    "price_momentum_5d": momentum_5[-5:] if momentum_5 else [],
                    "price_momentum_10d": momentum_10[-5:] if momentum_10 else [],
                    "volume_momentum": volume_momentum[-5:] if volume_momentum else [],
                    "momentum_summary": self._analyze_momentum_trend(momentum_5, momentum_10)
                }
            }
            
        except Exception as e:
            logger.error(f"Error preparing momentum context: {str(e)}")
            return {"momentum_analysis": f"Error in momentum analysis: {str(e)}"}
    
    async def _prepare_growth_context(self, ticker: str) -> Dict[str, Any]:
        """Prepare growth analysis context for mid/long-term analysis."""
        try:
            financial_data = await self._get_financial_data(ticker)
            
            if not financial_data:
                return {"growth_analysis": "No financial data for growth analysis"}
            
            # Calculate growth rates
            growth_metrics = self._calculate_growth_rates(financial_data)
            
            return {
                "growth_analysis": {
                    "revenue_growth": growth_metrics.get("revenue_growth", {}),
                    "profit_growth": growth_metrics.get("profit_growth", {}),
                    "growth_consistency": growth_metrics.get("growth_consistency", "不明"),
                    "growth_summary": self._generate_growth_summary(growth_metrics)
                }
            }
            
        except Exception as e:
            logger.error(f"Error preparing growth context: {str(e)}")
            return {"growth_analysis": f"Error in growth analysis: {str(e)}"}
    
    async def _prepare_valuation_context(self, ticker: str) -> Dict[str, Any]:
        """Prepare valuation context for long-term analysis."""
        try:
            daily_metrics = await self._get_daily_metrics(ticker)
            financial_data = await self._get_financial_data(ticker)
            
            if not daily_metrics and not financial_data:
                return {"valuation_analysis": "No valuation data available"}
            
            # Calculate valuation metrics
            valuation_metrics = self._calculate_valuation_metrics(daily_metrics, financial_data)
            
            return {
                "valuation_analysis": {
                    "current_valuation": valuation_metrics.get("current", {}),
                    "historical_valuation": valuation_metrics.get("historical", {}),
                    "peer_comparison": valuation_metrics.get("peer_comparison", "準備中"),
                    "valuation_summary": self._generate_valuation_summary(valuation_metrics)
                }
            }
            
        except Exception as e:
            logger.error(f"Error preparing valuation context: {str(e)}")
            return {"valuation_analysis": f"Error in valuation analysis: {str(e)}"}
    
    async def _prepare_market_context(self, ticker: str) -> Dict[str, Any]:
        """Prepare market context for all analysis types."""
        try:
            # This would typically fetch market indices data
            # For now, return placeholder data
            return {
                "market_context": {
                    "market_trend": "横ばい",
                    "sector_performance": "セクター平均並み",
                    "market_volatility": "中程度",
                    "trading_session": "通常取引時間" if self._is_market_hours() else "時間外"
                }
            }
            
        except Exception as e:
            logger.error(f"Error preparing market context: {str(e)}")
            return {"market_context": "Market context unavailable"}
    
    def _analyze_technical_signals(
        self, 
        closes: List[float], 
        sma_20: List[float], 
        sma_50: List[float], 
        rsi: List[float], 
        macd: Dict[str, List[float]], 
        bollinger: Dict[str, List[float]]
    ) -> Dict[str, str]:
        """Analyze technical signals."""
        signals = {}
        
        try:
            # Moving average signals
            if closes and sma_20 and sma_50:
                current_price = closes[-1]
                current_sma20 = sma_20[-1]
                current_sma50 = sma_50[-1]
                
                if current_price > current_sma20 > current_sma50:
                    signals["trend"] = "強い上昇トレンド"
                elif current_price > current_sma20:
                    signals["trend"] = "上昇トレンド"
                elif current_price < current_sma20 < current_sma50:
                    signals["trend"] = "強い下降トレンド"
                else:
                    signals["trend"] = "横ばいトレンド"
            
            # RSI signals
            if rsi:
                current_rsi = rsi[-1]
                if current_rsi > 70:
                    signals["rsi"] = "買われすぎ"
                elif current_rsi < 30:
                    signals["rsi"] = "売られすぎ"
                else:
                    signals["rsi"] = "中立"
            
            # MACD signals
            if macd.get("macd") and macd.get("signal"):
                macd_line = macd["macd"][-1]
                signal_line = macd["signal"][-1]
                
                if macd_line > signal_line:
                    signals["macd"] = "買いシグナル"
                else:
                    signals["macd"] = "売りシグナル"
            
            # Bollinger Bands signals
            if bollinger.get("upper") and bollinger.get("lower") and closes:
                current_price = closes[-1]
                upper_band = bollinger["upper"][-1]
                lower_band = bollinger["lower"][-1]
                
                if current_price > upper_band:
                    signals["bollinger"] = "上限突破（買われすぎ）"
                elif current_price < lower_band:
                    signals["bollinger"] = "下限突破（売られすぎ）"
                else:
                    signals["bollinger"] = "バンド内推移"
            
        except Exception as e:
            logger.error(f"Error analyzing technical signals: {str(e)}")
            signals["error"] = "シグナル分析エラー"
        
        return signals
    
    def _generate_technical_summary(
        self, 
        current_price: float, 
        price_change_1d: float, 
        rsi: List[float], 
        signals: Dict[str, str]
    ) -> str:
        """Generate technical analysis summary."""
        try:
            summary = f"現在価格: ¥{current_price:.2f} "
            
            if price_change_1d > 0:
                summary += f"(+{price_change_1d:.2f}%)\n"
            else:
                summary += f"({price_change_1d:.2f}%)\n"
            
            summary += f"トレンド: {signals.get('trend', '不明')}\n"
            summary += f"RSI状況: {signals.get('rsi', '不明')}\n"
            summary += f"MACD: {signals.get('macd', '不明')}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating technical summary: {str(e)}")
            return "テクニカル分析サマリー生成エラー"
    
    def _analyze_momentum_trend(
        self, 
        momentum_5: List[float], 
        momentum_10: List[float]
    ) -> str:
        """Analyze momentum trend."""
        try:
            if not momentum_5 or not momentum_10:
                return "モメンタムデータ不足"
            
            recent_momentum_5 = momentum_5[-1] if momentum_5 else 0
            recent_momentum_10 = momentum_10[-1] if momentum_10 else 0
            
            if recent_momentum_5 > 5 and recent_momentum_10 > 3:
                return "強い上昇モメンタム"
            elif recent_momentum_5 > 0 and recent_momentum_10 > 0:
                return "上昇モメンタム"
            elif recent_momentum_5 < -5 and recent_momentum_10 < -3:
                return "強い下降モメンタム"
            elif recent_momentum_5 < 0 and recent_momentum_10 < 0:
                return "下降モメンタム"
            else:
                return "モメンタム中立"
                
        except Exception as e:
            logger.error(f"Error analyzing momentum trend: {str(e)}")
            return "モメンタム分析エラー"
    
    def _calculate_growth_rates(self, financial_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate growth rates from financial data."""
        try:
            if len(financial_data) < 2:
                return {"error": "Insufficient data for growth calculation"}
            
            # Sort by fiscal year and period
            sorted_data = sorted(
                financial_data, 
                key=lambda x: (x["fiscal_year"], x["fiscal_period"]), 
                reverse=True
            )
            
            growth_metrics = {}
            
            # Calculate revenue growth
            revenues = []
            for data in sorted_data:
                revenue = data.get("metrics", {}).get("revenue")
                if revenue:
                    revenues.append(revenue)
            
            if len(revenues) >= 2:
                yoy_growth = ((revenues[0] - revenues[1]) / revenues[1]) * 100
                growth_metrics["revenue_growth"] = {
                    "yoy": round(yoy_growth, 2),
                    "trend": "成長" if yoy_growth > 0 else "減少"
                }
            
            # Calculate profit growth
            profits = []
            for data in sorted_data:
                profit = data.get("metrics", {}).get("net_income")
                if profit:
                    profits.append(profit)
            
            if len(profits) >= 2:
                profit_growth = ((profits[0] - profits[1]) / profits[1]) * 100
                growth_metrics["profit_growth"] = {
                    "yoy": round(profit_growth, 2),
                    "trend": "成長" if profit_growth > 0 else "減少"
                }
            
            # Assess growth consistency
            if len(revenues) >= 4:
                growth_rates = []
                for i in range(len(revenues) - 1):
                    if revenues[i + 1] != 0:
                        growth_rate = ((revenues[i] - revenues[i + 1]) / revenues[i + 1]) * 100
                        growth_rates.append(growth_rate)
                
                if growth_rates:
                    positive_growth = sum(1 for rate in growth_rates if rate > 0)
                    consistency = positive_growth / len(growth_rates)
                    
                    if consistency >= 0.75:
                        growth_metrics["growth_consistency"] = "安定成長"
                    elif consistency >= 0.5:
                        growth_metrics["growth_consistency"] = "成長鈍化"
                    else:
                        growth_metrics["growth_consistency"] = "不安定"
            
            return growth_metrics
            
        except Exception as e:
            logger.error(f"Error calculating growth rates: {str(e)}")
            return {"error": "Growth calculation error"}
    
    def _generate_growth_summary(self, growth_metrics: Dict[str, Any]) -> str:
        """Generate growth analysis summary."""
        try:
            if "error" in growth_metrics:
                return "成長分析データ不足"
            
            summary = "成長分析:\n"
            
            revenue_growth = growth_metrics.get("revenue_growth", {})
            if revenue_growth:
                summary += f"売上成長率: {revenue_growth.get('yoy', 0):.1f}% ({revenue_growth.get('trend', '不明')})\n"
            
            profit_growth = growth_metrics.get("profit_growth", {})
            if profit_growth:
                summary += f"利益成長率: {profit_growth.get('yoy', 0):.1f}% ({profit_growth.get('trend', '不明')})\n"
            
            consistency = growth_metrics.get("growth_consistency", "不明")
            summary += f"成長の安定性: {consistency}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating growth summary: {str(e)}")
            return "成長分析サマリー生成エラー"
    
    def _calculate_valuation_metrics(
        self, 
        daily_metrics: Dict[str, Any], 
        financial_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate valuation metrics."""
        try:
            valuation = {"current": {}, "historical": {}}
            
            # Current valuation from daily metrics
            if daily_metrics:
                valuation["current"] = {
                    "pe_ratio": daily_metrics.get("pe_ratio"),
                    "pb_ratio": daily_metrics.get("pb_ratio"),
                    "market_cap": daily_metrics.get("market_cap"),
                    "dividend_yield": daily_metrics.get("dividend_yield")
                }
            
            # Historical valuation trends
            if financial_data and len(financial_data) >= 2:
                # Calculate historical P/E trend (simplified)
                recent_data = financial_data[0]
                past_data = financial_data[1]
                
                recent_eps = recent_data.get("metrics", {}).get("net_income", 0)
                past_eps = past_data.get("metrics", {}).get("net_income", 0)
                
                if past_eps != 0:
                    eps_growth = ((recent_eps - past_eps) / past_eps) * 100
                    valuation["historical"]["eps_growth"] = round(eps_growth, 2)
            
            return valuation
            
        except Exception as e:
            logger.error(f"Error calculating valuation metrics: {str(e)}")
            return {"error": "Valuation calculation error"}
    
    def _generate_valuation_summary(self, valuation_metrics: Dict[str, Any]) -> str:
        """Generate valuation analysis summary."""
        try:
            if "error" in valuation_metrics:
                return "バリュエーション分析データ不足"
            
            summary = "バリュエーション分析:\n"
            
            current = valuation_metrics.get("current", {})
            if current.get("pe_ratio"):
                summary += f"PER: {current['pe_ratio']:.1f}倍\n"
            if current.get("pb_ratio"):
                summary += f"PBR: {current['pb_ratio']:.1f}倍\n"
            if current.get("dividend_yield"):
                summary += f"配当利回り: {current['dividend_yield']:.2f}%\n"
            
            historical = valuation_metrics.get("historical", {})
            if historical.get("eps_growth"):
                summary += f"EPS成長率: {historical['eps_growth']:.1f}%\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating valuation summary: {str(e)}")
            return "バリュエーション分析サマリー生成エラー"
    
    def _generate_analysis_summary(self, context: Dict[str, Any], analysis_type: str) -> str:
        """Generate overall analysis summary."""
        try:
            summary = f"{context.get('company_name', context.get('ticker'))}の{analysis_type}分析サマリー:\n\n"
            
            # Add technical summary if available
            if "technical_summary" in context:
                summary += "【テクニカル分析】\n"
                summary += context["technical_summary"] + "\n"
            
            # Add momentum summary if available
            if "momentum_analysis" in context:
                momentum = context["momentum_analysis"]
                if isinstance(momentum, dict) and "momentum_summary" in momentum:
                    summary += "【モメンタム分析】\n"
                    summary += momentum["momentum_summary"] + "\n"
            
            # Add growth summary if available
            if "growth_analysis" in context:
                growth = context["growth_analysis"]
                if isinstance(growth, dict) and "growth_summary" in growth:
                    summary += "【成長分析】\n"
                    summary += growth["growth_summary"] + "\n"
            
            # Add valuation summary if available
            if "valuation_analysis" in context:
                valuation = context["valuation_analysis"]
                if isinstance(valuation, dict) and "valuation_summary" in valuation:
                    summary += "【バリュエーション分析】\n"
                    summary += valuation["valuation_summary"] + "\n"
            
            # Add news sentiment if available
            if "news_sentiment" in context and isinstance(context["news_sentiment"], str):
                summary += "【ニュース・センチメント】\n"
                summary += context["news_sentiment"] + "\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating analysis summary: {str(e)}")
            return "分析サマリー生成エラー"
    
    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours (JST)."""
        try:
            from datetime import datetime
            import pytz
            
            jst = pytz.timezone('Asia/Tokyo')
            now = datetime.now(jst)
            
            # Tokyo Stock Exchange hours: 9:00-11:30, 12:30-15:00 JST
            if now.weekday() >= 5:  # Weekend
                return False
            
            morning_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
            morning_end = now.replace(hour=11, minute=30, second=0, microsecond=0)
            afternoon_start = now.replace(hour=12, minute=30, second=0, microsecond=0)
            afternoon_end = now.replace(hour=15, minute=0, second=0, microsecond=0)
            
            return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)
            
        except Exception:
            return False  # Default to closed if unable to determine


class DataTransformationException(Exception):
    """Raised when data transformation fails."""
    pass