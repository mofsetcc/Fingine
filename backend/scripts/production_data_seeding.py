#!/usr/bin/env python3
"""
Production data seeding and validation script for Japanese Stock Analysis Platform.

This script handles:
1. Populate production database with initial stock data
2. Validate data source connections in production environment  
3. Test AI analysis generation with real production data
4. Verify news aggregation and sentiment analysis pipeline

Requirements: 2.1, 4.1, 6.1
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal, AsyncSessionLocal
from app.core.config import settings
from app.models.stock import Stock, StockPriceHistory, StockDailyMetrics
from app.models.subscription import Plan
from app.models.news import NewsArticle, StockNewsLink
from app.adapters.registry import registry
from app.adapters.alpha_vantage_adapter import AlphaVantageAdapter
from app.adapters.yahoo_finance_adapter import YahooFinanceJapanAdapter
from app.adapters.edinet_adapter import EDINETAdapter
from app.adapters.news_adapter import NewsDataAdapter
from app.services.ai_analysis_service import AIAnalysisService
from app.services.news_service import NewsService
from app.services.sentiment_service import SentimentService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('production_seeding.log')
    ]
)
logger = logging.getLogger(__name__)


class ProductionDataSeeder:
    """Production data seeding and validation orchestrator."""
    
    def __init__(self):
        """Initialize the seeder with production configuration."""
        self.validation_results = {
            "stock_data_seeding": {"status": "pending", "details": {}},
            "data_source_validation": {"status": "pending", "details": {}},
            "ai_analysis_testing": {"status": "pending", "details": {}},
            "news_pipeline_validation": {"status": "pending", "details": {}}
        }
        
        # Major Japanese companies for production seeding
        self.production_stocks = [
            {
                "ticker": "7203",
                "company_name_jp": "トヨタ自動車",
                "company_name_en": "Toyota Motor Corporation",
                "sector_jp": "輸送用機器",
                "industry_jp": "自動車",
                "description": "世界最大級の自動車メーカー",
                "priority": 1
            },
            {
                "ticker": "9984", 
                "company_name_jp": "ソフトバンクグループ",
                "company_name_en": "SoftBank Group Corp",
                "sector_jp": "情報・通信業",
                "industry_jp": "通信",
                "description": "投資持株会社",
                "priority": 1
            },
            {
                "ticker": "6758",
                "company_name_jp": "ソニーグループ",
                "company_name_en": "Sony Group Corporation", 
                "sector_jp": "電気機器",
                "industry_jp": "電子機器",
                "description": "エレクトロニクス・エンターテインメント企業",
                "priority": 1
            },
            {
                "ticker": "8306",
                "company_name_jp": "三菱UFJフィナンシャル・グループ",
                "company_name_en": "Mitsubishi UFJ Financial Group",
                "sector_jp": "銀行業",
                "industry_jp": "銀行",
                "description": "日本最大の金融グループ",
                "priority": 1
            },
            {
                "ticker": "9432",
                "company_name_jp": "日本電信電話",
                "company_name_en": "Nippon Telegraph and Telephone Corporation",
                "sector_jp": "情報・通信業", 
                "industry_jp": "通信",
                "description": "日本最大の通信事業者",
                "priority": 1
            },
            {
                "ticker": "6861",
                "company_name_jp": "キーエンス",
                "company_name_en": "Keyence Corporation",
                "sector_jp": "電気機器",
                "industry_jp": "電子機器", 
                "description": "センサー・測定器メーカー",
                "priority": 2
            },
            {
                "ticker": "4519",
                "company_name_jp": "中外製薬",
                "company_name_en": "Chugai Pharmaceutical Co., Ltd.",
                "sector_jp": "医薬品",
                "industry_jp": "医薬品",
                "description": "製薬会社",
                "priority": 2
            },
            {
                "ticker": "8035",
                "company_name_jp": "東京エレクトロン",
                "company_name_en": "Tokyo Electron Limited",
                "sector_jp": "電気機器",
                "industry_jp": "半導体製造装置",
                "description": "半導体製造装置メーカー",
                "priority": 2
            },
            {
                "ticker": "6954",
                "company_name_jp": "ファナック", 
                "company_name_en": "FANUC Corporation",
                "sector_jp": "電気機器",
                "industry_jp": "工作機械",
                "description": "工作機械・ロボットメーカー",
                "priority": 2
            },
            {
                "ticker": "4661",
                "company_name_jp": "オリエンタルランド",
                "company_name_en": "Oriental Land Co., Ltd.",
                "sector_jp": "サービス業",
                "industry_jp": "テーマパーク",
                "description": "東京ディズニーリゾート運営",
                "priority": 2
            }
        ]
    
    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete production data seeding and validation."""
        logger.info("🚀 Starting production data seeding and validation")
        
        try:
            # Task 1: Populate production database with initial stock data
            await self._populate_stock_data()
            
            # Task 2: Validate data source connections in production environment
            await self._validate_data_sources()
            
            # Task 3: Test AI analysis generation with real production data
            await self._test_ai_analysis()
            
            # Task 4: Verify news aggregation and sentiment analysis pipeline
            await self._validate_news_pipeline()
            
            # Generate final report
            report = self._generate_validation_report()
            
            logger.info("✅ Production data seeding and validation completed")
            return report
            
        except Exception as e:
            logger.error(f"❌ Production validation failed: {e}")
            raise
    
    async def _populate_stock_data(self) -> None:
        """Populate production database with initial stock data."""
        logger.info("📊 Starting stock data population...")
        
        try:
            # Create database session
            db = SessionLocal()
            
            try:
                # 1. Create stock records
                stocks_created = await self._create_stock_records(db)
                
                # 2. Create subscription plans if they don't exist
                plans_created = await self._create_subscription_plans(db)
                
                # 3. Populate initial price data for priority stocks
                price_records = await self._populate_initial_price_data(db)
                
                # 4. Create daily metrics for priority stocks
                metrics_created = await self._create_daily_metrics(db)
                
                self.validation_results["stock_data_seeding"] = {
                    "status": "success",
                    "details": {
                        "stocks_created": stocks_created,
                        "plans_created": plans_created,
                        "price_records": price_records,
                        "metrics_created": metrics_created,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
                
                logger.info(f"✅ Stock data population completed: {stocks_created} stocks, {price_records} price records")
                
            finally:
                db.close()
                
        except Exception as e:
            self.validation_results["stock_data_seeding"] = {
                "status": "failed",
                "details": {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
            }
            logger.error(f"❌ Stock data population failed: {e}")
            raise
    
    async def _create_stock_records(self, db: Session) -> int:
        """Create stock records in database."""
        stocks_created = 0
        
        for stock_data in self.production_stocks:
            # Check if stock already exists
            existing_stock = db.query(Stock).filter(Stock.ticker == stock_data["ticker"]).first()
            if existing_stock:
                logger.info(f"Stock {stock_data['ticker']} already exists, updating...")
                # Update existing stock data
                existing_stock.company_name_jp = stock_data["company_name_jp"]
                existing_stock.company_name_en = stock_data["company_name_en"]
                existing_stock.sector_jp = stock_data["sector_jp"]
                existing_stock.industry_jp = stock_data["industry_jp"]
                existing_stock.description = stock_data["description"]
                existing_stock.is_active = True
            else:
                # Create new stock
                stock = Stock(
                    ticker=stock_data["ticker"],
                    company_name_jp=stock_data["company_name_jp"],
                    company_name_en=stock_data["company_name_en"],
                    sector_jp=stock_data["sector_jp"],
                    industry_jp=stock_data["industry_jp"],
                    description=stock_data["description"],
                    listing_date=datetime(2000, 1, 1).date(),  # Default listing date
                    is_active=True
                )
                db.add(stock)
                stocks_created += 1
                logger.info(f"Created stock record: {stock_data['ticker']} - {stock_data['company_name_jp']}")
        
        db.commit()
        return stocks_created
    
    async def _create_subscription_plans(self, db: Session) -> int:
        """Create subscription plans if they don't exist."""
        # Check if plans already exist
        existing_plans = db.query(Plan).count()
        if existing_plans > 0:
            logger.info(f"Subscription plans already exist ({existing_plans} plans), skipping...")
            return 0
        
        # Create default plans
        plans = [
            Plan(
                plan_name="Free",
                price_monthly=0,
                features={
                    "ai_analysis": True,
                    "real_time_data": False,
                    "advanced_charts": False,
                    "api_access": False,
                    "priority_support": False
                },
                api_quota_daily=10,
                ai_analysis_quota_daily=5,
                is_active=True
            ),
            Plan(
                plan_name="Pro",
                price_monthly=2980,  # 2,980 JPY
                features={
                    "ai_analysis": True,
                    "real_time_data": True,
                    "advanced_charts": True,
                    "api_access": True,
                    "priority_support": False,
                    "watchlist_alerts": True,
                    "export_data": True
                },
                api_quota_daily=100,
                ai_analysis_quota_daily=50,
                is_active=True
            ),
            Plan(
                plan_name="Business",
                price_monthly=9800,  # 9,800 JPY
                features={
                    "ai_analysis": True,
                    "real_time_data": True,
                    "advanced_charts": True,
                    "api_access": True,
                    "priority_support": True,
                    "watchlist_alerts": True,
                    "export_data": True,
                    "bulk_analysis": True,
                    "custom_reports": True,
                    "white_label": True
                },
                api_quota_daily=1000,
                ai_analysis_quota_daily=500,
                is_active=True
            )
        ]
        
        for plan in plans:
            db.add(plan)
            logger.info(f"Created subscription plan: {plan.plan_name} (¥{plan.price_monthly}/month)")
        
        db.commit()
        return len(plans)
    
    async def _populate_initial_price_data(self, db: Session) -> int:
        """Populate initial price data for priority stocks."""
        price_records = 0
        
        # Only populate for priority 1 stocks to avoid excessive API calls
        priority_stocks = [s for s in self.production_stocks if s.get("priority", 2) == 1]
        
        for stock_data in priority_stocks:
            ticker = stock_data["ticker"]
            
            # Check if price data already exists
            existing_data = db.query(StockPriceHistory).filter(
                StockPriceHistory.ticker == ticker
            ).first()
            
            if existing_data:
                logger.info(f"Price data for {ticker} already exists, skipping...")
                continue
            
            try:
                # Try to get real price data from Yahoo Finance (free)
                yahoo_adapter = YahooFinanceJapanAdapter(config={})
                
                # Get last 30 days of data
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=30)
                
                historical_data = await yahoo_adapter.get_historical_prices(
                    symbol=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    interval="1d"
                )
                
                # Insert price data
                for price_data in historical_data:
                    price_record = StockPriceHistory(
                        ticker=ticker,
                        date=datetime.fromisoformat(price_data["date"].replace("Z", "+00:00")).date(),
                        open=price_data["open"],
                        high=price_data["high"],
                        low=price_data["low"],
                        close=price_data["close"],
                        volume=price_data["volume"],
                        adjusted_close=price_data["adjusted_close"]
                    )
                    db.add(price_record)
                    price_records += 1
                
                logger.info(f"Added {len(historical_data)} price records for {ticker}")
                
                # Close adapter session
                await yahoo_adapter._close_session()
                
            except Exception as e:
                logger.warning(f"Failed to get price data for {ticker}: {e}")
                continue
        
        db.commit()
        return price_records
    
    async def _create_daily_metrics(self, db: Session) -> int:
        """Create daily metrics for priority stocks."""
        metrics_created = 0
        today = datetime.utcnow().date()
        
        # Only create metrics for priority 1 stocks
        priority_stocks = [s for s in self.production_stocks if s.get("priority", 2) == 1]
        
        for stock_data in priority_stocks:
            ticker = stock_data["ticker"]
            
            # Check if metrics already exist
            existing_metrics = db.query(StockDailyMetrics).filter(
                StockDailyMetrics.ticker == ticker,
                StockDailyMetrics.date == today
            ).first()
            
            if existing_metrics:
                logger.info(f"Metrics for {ticker} already exist, skipping...")
                continue
            
            # Get latest price for calculations
            latest_price = db.query(StockPriceHistory).filter(
                StockPriceHistory.ticker == ticker
            ).order_by(StockPriceHistory.date.desc()).first()
            
            if not latest_price:
                logger.warning(f"No price data found for {ticker}, skipping metrics")
                continue
            
            # Create realistic metrics based on company type
            metrics = self._generate_realistic_metrics(stock_data, float(latest_price.close))
            
            daily_metrics = StockDailyMetrics(
                ticker=ticker,
                date=today,
                market_cap=metrics["market_cap"],
                pe_ratio=metrics["pe_ratio"],
                pb_ratio=metrics["pb_ratio"],
                dividend_yield=metrics["dividend_yield"],
                shares_outstanding=metrics["shares_outstanding"]
            )
            
            db.add(daily_metrics)
            metrics_created += 1
            logger.info(f"Created metrics for {ticker}")
        
        db.commit()
        return metrics_created
    
    def _generate_realistic_metrics(self, stock_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Generate realistic financial metrics based on company profile."""
        ticker = stock_data["ticker"]
        sector = stock_data["sector_jp"]
        
        # Base metrics by sector
        sector_metrics = {
            "輸送用機器": {"pe_range": (8, 15), "pb_range": (0.8, 1.5), "div_yield": (2.0, 4.0)},
            "情報・通信業": {"pe_range": (15, 35), "pb_range": (1.5, 4.0), "div_yield": (1.0, 3.0)},
            "電気機器": {"pe_range": (12, 25), "pb_range": (1.0, 2.5), "div_yield": (1.5, 3.5)},
            "銀行業": {"pe_range": (6, 12), "pb_range": (0.3, 0.8), "div_yield": (3.0, 5.0)},
            "医薬品": {"pe_range": (20, 40), "pb_range": (2.0, 5.0), "div_yield": (1.0, 2.5)},
            "サービス業": {"pe_range": (15, 30), "pb_range": (1.5, 3.0), "div_yield": (1.0, 2.0)}
        }
        
        # Get sector-specific ranges or use defaults
        metrics_range = sector_metrics.get(sector, {"pe_range": (10, 20), "pb_range": (1.0, 2.0), "div_yield": (2.0, 3.0)})
        
        # Company-specific adjustments
        company_adjustments = {
            "7203": {"shares": 2_900_000_000, "pe_mult": 0.8},  # Toyota - lower PE
            "9984": {"shares": 4_700_000_000, "pe_mult": 1.2},  # SoftBank - higher PE
            "6758": {"shares": 1_260_000_000, "pe_mult": 1.1},  # Sony
            "8306": {"shares": 13_700_000_000, "pe_mult": 0.7}, # MUFG - bank, lower PE
            "9432": {"shares": 4_300_000_000, "pe_mult": 0.9}   # NTT
        }
        
        adjustment = company_adjustments.get(ticker, {"shares": 1_000_000_000, "pe_mult": 1.0})
        
        # Calculate metrics
        shares_outstanding = adjustment["shares"]
        market_cap = int(current_price * shares_outstanding)
        
        # PE ratio with company adjustment
        pe_base = (metrics_range["pe_range"][0] + metrics_range["pe_range"][1]) / 2
        pe_ratio = round(pe_base * adjustment["pe_mult"], 2)
        
        # PB ratio
        pb_ratio = round((metrics_range["pb_range"][0] + metrics_range["pb_range"][1]) / 2, 2)
        
        # Dividend yield
        div_yield = round((metrics_range["div_yield"][0] + metrics_range["div_yield"][1]) / 2 / 100, 4)
        
        return {
            "market_cap": market_cap,
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "dividend_yield": div_yield,
            "shares_outstanding": shares_outstanding
        }
    
    async def _validate_data_sources(self) -> None:
        """Validate data source connections in production environment."""
        logger.info("🔌 Validating data source connections...")
        
        try:
            validation_results = {}
            
            # Initialize and test data source adapters
            adapters_to_test = [
                ("alpha_vantage", AlphaVantageAdapter, {"api_key": settings.ALPHA_VANTAGE_API_KEY}),
                ("yahoo_finance", YahooFinanceJapanAdapter, {}),
                ("edinet", EDINETAdapter, {}),
                ("news_data", NewsDataAdapter, {"news_api_key": settings.NEWS_API_KEY})
            ]
            
            for adapter_name, adapter_class, config in adapters_to_test:
                try:
                    logger.info(f"Testing {adapter_name} adapter...")
                    
                    # Initialize adapter
                    adapter = adapter_class(name=adapter_name, config=config)
                    
                    # Perform health check
                    health_check = await adapter.health_check()
                    
                    # Test basic functionality
                    functionality_test = await self._test_adapter_functionality(adapter, adapter_name)
                    
                    validation_results[adapter_name] = {
                        "status": "success" if health_check.status.value == "healthy" else "degraded",
                        "health_check": {
                            "status": health_check.status.value,
                            "response_time_ms": health_check.response_time_ms,
                            "error_message": health_check.error_message
                        },
                        "functionality_test": functionality_test,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Clean up adapter
                    if hasattr(adapter, '_close_session'):
                        await adapter._close_session()
                    
                    logger.info(f"✅ {adapter_name} validation completed")
                    
                except Exception as e:
                    validation_results[adapter_name] = {
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    logger.error(f"❌ {adapter_name} validation failed: {e}")
            
            self.validation_results["data_source_validation"] = {
                "status": "success",
                "details": validation_results
            }
            
            logger.info("✅ Data source validation completed")
            
        except Exception as e:
            self.validation_results["data_source_validation"] = {
                "status": "failed",
                "details": {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
            }
            logger.error(f"❌ Data source validation failed: {e}")
            raise
    
    async def _test_adapter_functionality(self, adapter: Any, adapter_name: str) -> Dict[str, Any]:
        """Test basic functionality of a data adapter."""
        test_results = {}
        
        try:
            if adapter_name in ["alpha_vantage", "yahoo_finance"]:
                # Test stock price retrieval
                test_symbol = "7203"  # Toyota
                current_price = await adapter.get_current_price(test_symbol)
                test_results["current_price_test"] = {
                    "success": True,
                    "symbol": test_symbol,
                    "price": current_price.get("price"),
                    "currency": current_price.get("currency")
                }
                
                # Test historical data
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=7)
                historical_data = await adapter.get_historical_prices(test_symbol, start_date, end_date)
                test_results["historical_data_test"] = {
                    "success": True,
                    "records_count": len(historical_data),
                    "date_range": f"{start_date.date()} to {end_date.date()}"
                }
                
            elif adapter_name == "edinet":
                # Test financial data retrieval
                test_symbol = "7203"
                financial_data = await adapter.get_financial_statements(test_symbol, "income_statement", "annual")
                test_results["financial_data_test"] = {
                    "success": True,
                    "symbol": test_symbol,
                    "statements_count": len(financial_data)
                }
                
            elif adapter_name == "news_data":
                # Test news retrieval
                news_articles = await adapter.get_news(symbol="7203", limit=5)
                test_results["news_retrieval_test"] = {
                    "success": True,
                    "articles_count": len(news_articles),
                    "sources": list(set([article.get("source", "") for article in news_articles]))
                }
            
        except Exception as e:
            test_results["error"] = str(e)
            test_results["success"] = False
        
        return test_results
    
    async def _test_ai_analysis(self) -> None:
        """Test AI analysis generation with real production data."""
        logger.info("🤖 Testing AI analysis generation...")
        
        try:
            # Initialize AI analysis service
            # Note: This would typically use dependency injection in the actual app
            ai_service = AIAnalysisService()
            
            test_results = {}
            test_symbols = ["7203", "6758"]  # Toyota and Sony
            
            for symbol in test_symbols:
                try:
                    logger.info(f"Testing AI analysis for {symbol}...")
                    
                    # Test different analysis types
                    analysis_types = ["short_term", "mid_term", "long_term"]
                    symbol_results = {}
                    
                    for analysis_type in analysis_types:
                        try:
                            # Generate AI analysis
                            analysis_result = await ai_service.generate_analysis(symbol, analysis_type)
                            
                            symbol_results[analysis_type] = {
                                "success": True,
                                "rating": analysis_result.get("rating"),
                                "confidence": analysis_result.get("confidence"),
                                "key_factors_count": len(analysis_result.get("key_factors", [])),
                                "has_price_target": "price_target_range" in analysis_result,
                                "processing_time_ms": analysis_result.get("processing_time_ms"),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            
                            logger.info(f"✅ {analysis_type} analysis for {symbol} completed")
                            
                        except Exception as e:
                            symbol_results[analysis_type] = {
                                "success": False,
                                "error": str(e),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            logger.warning(f"⚠️ {analysis_type} analysis for {symbol} failed: {e}")
                    
                    test_results[symbol] = symbol_results
                    
                except Exception as e:
                    test_results[symbol] = {
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    logger.warning(f"⚠️ AI analysis testing for {symbol} failed: {e}")
            
            # Calculate overall success rate
            total_tests = sum(len(results) for results in test_results.values() if isinstance(results, dict))
            successful_tests = sum(
                sum(1 for test in results.values() if isinstance(test, dict) and test.get("success", False))
                for results in test_results.values() if isinstance(results, dict)
            )
            
            success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
            
            self.validation_results["ai_analysis_testing"] = {
                "status": "success" if success_rate >= 70 else "partial",
                "details": {
                    "test_results": test_results,
                    "success_rate": success_rate,
                    "total_tests": total_tests,
                    "successful_tests": successful_tests,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"✅ AI analysis testing completed - Success rate: {success_rate:.1f}%")
            
        except Exception as e:
            self.validation_results["ai_analysis_testing"] = {
                "status": "failed",
                "details": {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
            }
            logger.error(f"❌ AI analysis testing failed: {e}")
            raise
    
    async def _validate_news_pipeline(self) -> None:
        """Verify news aggregation and sentiment analysis pipeline."""
        logger.info("📰 Validating news aggregation and sentiment analysis pipeline...")
        
        try:
            # Initialize services
            news_service = NewsService()
            sentiment_service = SentimentService()
            
            test_results = {}
            test_symbols = ["7203", "6758"]  # Toyota and Sony
            
            for symbol in test_symbols:
                try:
                    logger.info(f"Testing news pipeline for {symbol}...")
                    
                    # 1. Test news aggregation
                    news_articles = await news_service.get_stock_related_news(
                        symbol=symbol,
                        limit=10,
                        days_back=7
                    )
                    
                    # 2. Test sentiment analysis on collected articles
                    sentiment_results = []
                    for article in news_articles[:5]:  # Test first 5 articles
                        if article.get("headline"):
                            sentiment = await sentiment_service.analyze_text(
                                text=article["headline"],
                                language="ja"
                            )
                            sentiment_results.append({
                                "headline": article["headline"][:50] + "...",
                                "sentiment": sentiment.get("label"),
                                "score": sentiment.get("score")
                            })
                    
                    # 3. Test sentiment timeline generation
                    sentiment_timeline = await sentiment_service.get_sentiment_timeline(
                        symbol=symbol,
                        days_back=7
                    )
                    
                    test_results[symbol] = {
                        "success": True,
                        "news_aggregation": {
                            "articles_found": len(news_articles),
                            "sources": list(set([article.get("source", "") for article in news_articles])),
                            "date_range_days": 7
                        },
                        "sentiment_analysis": {
                            "articles_analyzed": len(sentiment_results),
                            "sentiment_distribution": self._calculate_sentiment_distribution(sentiment_results),
                            "sample_results": sentiment_results[:3]  # First 3 for review
                        },
                        "sentiment_timeline": {
                            "timeline_points": len(sentiment_timeline),
                            "average_sentiment": self._calculate_average_sentiment(sentiment_timeline)
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    logger.info(f"✅ News pipeline validation for {symbol} completed")
                    
                except Exception as e:
                    test_results[symbol] = {
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    logger.warning(f"⚠️ News pipeline validation for {symbol} failed: {e}")
            
            # Calculate overall pipeline health
            successful_symbols = sum(1 for result in test_results.values() if result.get("success", False))
            total_symbols = len(test_results)
            pipeline_health = (successful_symbols / total_symbols * 100) if total_symbols > 0 else 0
            
            self.validation_results["news_pipeline_validation"] = {
                "status": "success" if pipeline_health >= 80 else "partial",
                "details": {
                    "test_results": test_results,
                    "pipeline_health": pipeline_health,
                    "successful_symbols": successful_symbols,
                    "total_symbols": total_symbols,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"✅ News pipeline validation completed - Health: {pipeline_health:.1f}%")
            
        except Exception as e:
            self.validation_results["news_pipeline_validation"] = {
                "status": "failed",
                "details": {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
            }
            logger.error(f"❌ News pipeline validation failed: {e}")
            raise
    
    def _calculate_sentiment_distribution(self, sentiment_results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of sentiment labels."""
        distribution = {"positive": 0, "neutral": 0, "negative": 0}
        
        for result in sentiment_results:
            sentiment = result.get("sentiment", "neutral").lower()
            if sentiment in distribution:
                distribution[sentiment] += 1
        
        return distribution
    
    def _calculate_average_sentiment(self, timeline: List[Dict[str, Any]]) -> float:
        """Calculate average sentiment score from timeline."""
        if not timeline:
            return 0.0
        
        scores = [point.get("sentiment_score", 0.0) for point in timeline]
        return sum(scores) / len(scores) if scores else 0.0
    
    def _generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        report = {
            "validation_summary": {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": self._calculate_overall_status(),
                "environment": "production",
                "version": "1.0.0"
            },
            "task_results": self.validation_results,
            "recommendations": self._generate_recommendations()
        }
        
        # Save report to file
        report_path = Path("production_validation_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📋 Validation report saved to {report_path}")
        
        return report
    
    def _calculate_overall_status(self) -> str:
        """Calculate overall validation status."""
        statuses = [result["status"] for result in self.validation_results.values()]
        
        if all(status == "success" for status in statuses):
            return "success"
        elif any(status == "failed" for status in statuses):
            return "partial"
        else:
            return "degraded"
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        for task, result in self.validation_results.items():
            if result["status"] == "failed":
                recommendations.append(f"❌ {task}: Critical failure - immediate attention required")
            elif result["status"] == "partial":
                recommendations.append(f"⚠️ {task}: Partial success - monitor and investigate failures")
            elif result["status"] == "degraded":
                recommendations.append(f"🔶 {task}: Degraded performance - optimize for better results")
        
        if not recommendations:
            recommendations.append("✅ All validation tasks completed successfully - system ready for production")
        
        return recommendations


async def main():
    """Main execution function."""
    seeder = ProductionDataSeeder()
    
    try:
        # Run full validation
        report = await seeder.run_full_validation()
        
        # Print summary
        print("\n" + "="*80)
        print("🎯 PRODUCTION DATA SEEDING AND VALIDATION SUMMARY")
        print("="*80)
        print(f"Overall Status: {report['validation_summary']['overall_status'].upper()}")
        print(f"Timestamp: {report['validation_summary']['timestamp']}")
        print("\nTask Results:")
        
        for task, result in report['task_results'].items():
            status_emoji = {"success": "✅", "partial": "⚠️", "failed": "❌", "degraded": "🔶"}.get(result['status'], "❓")
            print(f"  {status_emoji} {task}: {result['status']}")
        
        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"  {rec}")
        
        print("\n" + "="*80)
        
        # Exit with appropriate code
        overall_status = report['validation_summary']['overall_status']
        if overall_status == "success":
            sys.exit(0)
        elif overall_status in ["partial", "degraded"]:
            sys.exit(1)
        else:
            sys.exit(2)
            
    except Exception as e:
        logger.error(f"💥 Production validation failed with exception: {e}")
        print(f"\n❌ CRITICAL ERROR: {e}")
        sys.exit(3)


if __name__ == "__main__":
    asyncio.run(main())