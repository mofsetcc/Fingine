#!/usr/bin/env python3
"""
Simple test script for data transformer functionality without database dependencies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import json

# Import the technical indicator calculator
from test_indicators_simple import TechnicalIndicatorCalculator


class MockDataTransformer:
    """Mock data transformer for testing without database dependencies."""
    
    def __init__(self):
        self.indicator_calc = TechnicalIndicatorCalculator()
    
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
            signals["error"] = f"シグナル分析エラー: {str(e)}"
        
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
            return f"テクニカル分析サマリー生成エラー: {str(e)}"
    
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
            return f"モメンタム分析エラー: {str(e)}"
    
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
            return {"error": f"Growth calculation error: {str(e)}"}
    
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


def test_data_transformation():
    """Test data transformation functionality."""
    transformer = MockDataTransformer()
    
    print("Testing Data Transformation Pipeline")
    print("=" * 50)
    
    # Test price data formatting
    price_data = [
        {"date": "2024-01-01", "close": 1000, "volume": 100000},
        {"date": "2024-01-02", "close": 1050, "volume": 120000},
        {"date": "2024-01-03", "close": 1020, "volume": 90000}
    ]
    
    formatted_price = transformer._format_price_data(price_data)
    print("Price Data Formatting:")
    print(formatted_price)
    assert "最近の株価データ" in formatted_price
    assert "前日比" in formatted_price
    print("✅ Price data formatting test passed!\n")
    
    # Test technical signals analysis
    closes = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118]
    sma_20 = [105, 107, 109, 111, 113]
    sma_50 = [103, 105, 107, 109, 111]
    rsi = [45, 50, 55, 60, 65]
    macd = {"macd": [0.5, 1.0, 1.5], "signal": [0.3, 0.8, 1.2]}
    bollinger = {"upper": [120, 122, 124], "middle": [110, 112, 114], "lower": [100, 102, 104]}
    
    signals = transformer._analyze_technical_signals(closes, sma_20, sma_50, rsi, macd, bollinger)
    print("Technical Signals Analysis:")
    print(json.dumps(signals, indent=2, ensure_ascii=False))
    assert "trend" in signals
    assert "rsi" in signals
    print("✅ Technical signals analysis test passed!\n")
    
    # Test technical summary generation
    technical_summary = transformer._generate_technical_summary(118.0, 2.5, rsi, signals)
    print("Technical Summary:")
    print(technical_summary)
    assert "現在価格" in technical_summary
    assert "トレンド" in technical_summary
    print("✅ Technical summary generation test passed!\n")
    
    # Test momentum analysis
    momentum_5 = [8.0, 10.0, 12.0]
    momentum_10 = [5.0, 6.0, 7.0]
    momentum_trend = transformer._analyze_momentum_trend(momentum_5, momentum_10)
    print("Momentum Analysis:")
    print(momentum_trend)
    assert "モメンタム" in momentum_trend
    print("✅ Momentum analysis test passed!\n")
    
    # Test growth rates calculation
    financial_data = [
        {
            "fiscal_year": 2024,
            "fiscal_period": "Q1",
            "metrics": {"revenue": 1000000, "net_income": 100000}
        },
        {
            "fiscal_year": 2023,
            "fiscal_period": "Q4",
            "metrics": {"revenue": 900000, "net_income": 80000}
        },
        {
            "fiscal_year": 2023,
            "fiscal_period": "Q3",
            "metrics": {"revenue": 850000, "net_income": 70000}
        }
    ]
    
    growth_metrics = transformer._calculate_growth_rates(financial_data)
    print("Growth Rates Calculation:")
    print(json.dumps(growth_metrics, indent=2, ensure_ascii=False))
    assert "revenue_growth" in growth_metrics
    assert "profit_growth" in growth_metrics
    print("✅ Growth rates calculation test passed!\n")
    
    # Test sentiment analysis
    news_data = [
        {"sentiment_label": "positive"},
        {"sentiment_label": "positive"},
        {"sentiment_label": "negative"},
        {"sentiment_label": "neutral"}
    ]
    
    sentiment_analysis = transformer._analyze_sentiment_trends(news_data)
    print("Sentiment Analysis:")
    print(sentiment_analysis)
    assert "ニュースセンチメント" in sentiment_analysis
    print("✅ Sentiment analysis test passed!\n")
    
    print("🎉 All data transformation tests passed!")


if __name__ == "__main__":
    test_data_transformation()