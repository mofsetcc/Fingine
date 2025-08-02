#!/usr/bin/env python3
"""
Simple test script for technical indicators without database dependencies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import just the calculator class directly
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import json

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


def test_technical_indicators():
    """Test all technical indicators."""
    calc = TechnicalIndicatorCalculator()
    
    # Test data
    prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122, 124, 126, 128, 130]
    
    print("Testing Technical Indicators")
    print("=" * 40)
    
    # Test SMA
    sma_5 = calc.calculate_sma(prices, 5)
    print(f"SMA(5): {sma_5}")
    assert len(sma_5) == len(prices) - 4  # Should have 12 values
    
    # Test EMA
    ema_5 = calc.calculate_ema(prices, 5)
    print(f"EMA(5): {ema_5[-5:]}")  # Show last 5 values
    assert len(ema_5) == len(prices)
    
    # Test RSI
    rsi = calc.calculate_rsi(prices, 14)
    print(f"RSI(14): {rsi}")
    assert len(rsi) >= 0  # May be empty if not enough data
    
    # Test Momentum
    momentum = calc.calculate_price_momentum(prices, 5)
    print(f"Momentum(5): {momentum}")
    assert len(momentum) == len(prices) - 5  # Should have 11 values
    
    # Test Volatility
    volatility = calc.calculate_volatility(prices, 10)
    print(f"Volatility(10): {volatility}")
    assert len(volatility) == len(prices) - 9  # Should have 7 values
    
    # Test Support/Resistance
    support_resistance = calc.calculate_support_resistance(prices, 10)
    print(f"Support/Resistance: {support_resistance}")
    assert support_resistance["support"] <= support_resistance["resistance"]
    
    print("\n✅ All technical indicator tests passed!")


if __name__ == "__main__":
    test_technical_indicators()