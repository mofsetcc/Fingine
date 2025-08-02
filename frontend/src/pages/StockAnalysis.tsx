/**
 * Individual stock analysis page component with inverted pyramid layout.
 * Implements comprehensive AI analysis display, TradingView charts, and financial data visualization.
 */

import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useParams } from 'react-router-dom';
import { RootState } from '../store';
import { setLoading as setAnalysisLoading, setCurrentAnalysis } from '../store/slices/analysisSlice';
import { setError, setLoading, setSelectedStock } from '../store/slices/stocksSlice';

// Components
import AIAnalysisDisplay from '../components/AIAnalysisDisplay';
import ErrorMessage from '../components/ErrorMessage';
import FinancialDataTable from '../components/FinancialDataTable';
import LoadingSpinner from '../components/LoadingSpinner';
import NewsAndSentiment from '../components/NewsAndSentiment';
import StockHeader from '../components/StockHeader';
import TradingViewChart from '../components/TradingViewChart';

// Types
import { AIAnalysisResult } from '../types/ai-analysis';
import { StockDetail } from '../types/stock';

const StockAnalysis: React.FC = () => {
  const { ticker } = useParams<{ ticker: string }>();
  const dispatch = useDispatch();
  
  // Redux state
  const { selectedStock, isLoading, error } = useSelector((state: RootState) => state.stocks);
  const { currentAnalysis, isLoading: isAnalysisLoading } = useSelector((state: RootState) => state.analysis);
  
  // Local state for component management
  const [activeAnalysisType, setActiveAnalysisType] = useState<'short_term' | 'mid_term' | 'long_term'>('short_term');
  const [chartPeriod, setChartPeriod] = useState<'1d' | '1w' | '1m' | '3m' | '6m' | '1y'>('1m');
  const [showFinancialDetails, setShowFinancialDetails] = useState(false);

  // Fetch stock data and analysis on component mount
  useEffect(() => {
    if (ticker) {
      fetchStockData(ticker);
      fetchAIAnalysis(ticker, activeAnalysisType);
    }
  }, [ticker, activeAnalysisType]);

  const fetchStockData = async (stockTicker: string) => {
    dispatch(setLoading(true));
    dispatch(setError(null));
    
    try {
      const response = await fetch(`/api/v1/stocks/${stockTicker}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch stock data: ${response.statusText}`);
      }
      
      const stockData: StockDetail = await response.json();
      dispatch(setSelectedStock(stockData));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch stock data'));
    } finally {
      dispatch(setLoading(false));
    }
  };

  const fetchAIAnalysis = async (stockTicker: string, analysisType: string) => {
    dispatch(setAnalysisLoading(true));
    
    try {
      const response = await fetch(`/api/v1/analysis/${stockTicker}/${analysisType}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch AI analysis: ${response.statusText}`);
      }
      
      const analysisData = await response.json();
      const analysisResult: AIAnalysisResult = {
        ticker: stockTicker,
        analysisType: analysisType as any,
        rating: analysisData.analysis.rating,
        confidence: analysisData.analysis.confidence,
        keyFactors: analysisData.analysis.key_factors,
        priceTargetRange: analysisData.analysis.price_target_range,
        riskFactors: analysisData.analysis.risk_factors,
        reasoning: analysisData.analysis.reasoning || '',
        generatedAt: new Date().toISOString(),
        modelVersion: analysisData.analysis.model_version || 'gemini-pro-1.0'
      };
      
      dispatch(setCurrentAnalysis(analysisResult));
    } catch (err) {
      console.error('Failed to fetch AI analysis:', err);
    } finally {
      dispatch(setAnalysisLoading(false));
    }
  };

  const handleAnalysisTypeChange = (type: 'short_term' | 'mid_term' | 'long_term') => {
    setActiveAnalysisType(type);
  };

  const handleChartPeriodChange = (period: '1d' | '1w' | '1m' | '3m' | '6m' | '1y') => {
    setChartPeriod(period);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <ErrorMessage 
          message={error} 
          onRetry={() => ticker && fetchStockData(ticker)}
        />
      </div>
    );
  }

  // No stock data
  if (!selectedStock || !ticker) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <ErrorMessage 
          message="Stock not found" 
          onRetry={() => ticker && fetchStockData(ticker)}
        />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-8">
      {/* Inverted Pyramid Layout - Most Important Content First */}
      
      {/* 1. Stock Header with Key Info */}
      <StockHeader 
        stock={selectedStock}
        onAddToWatchlist={() => {/* TODO: Implement watchlist functionality */}}
      />

      {/* 2. AI Analysis - Primary Content (Inverted Pyramid Top) */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            AI-Powered Analysis
          </h2>
          <div className="flex space-x-4 mb-6">
            <button
              onClick={() => handleAnalysisTypeChange('short_term')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeAnalysisType === 'short_term'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Short-term (1-4 weeks)
            </button>
            <button
              onClick={() => handleAnalysisTypeChange('mid_term')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeAnalysisType === 'mid_term'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Mid-term (1-6 months)
            </button>
            <button
              onClick={() => handleAnalysisTypeChange('long_term')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeAnalysisType === 'long_term'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Long-term (1+ years)
            </button>
          </div>
        </div>
        
        <AIAnalysisDisplay 
          analysis={currentAnalysis}
          isLoading={isAnalysisLoading}
          analysisType={activeAnalysisType}
          onRefresh={() => fetchAIAnalysis(ticker, activeAnalysisType)}
        />
      </div>

      {/* 3. Interactive Chart - Secondary Content */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-semibold text-gray-900">
              Price Chart & Technical Analysis
            </h3>
            <div className="flex space-x-2">
              {(['1d', '1w', '1m', '3m', '6m', '1y'] as const).map((period) => (
                <button
                  key={period}
                  onClick={() => handleChartPeriodChange(period)}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    chartPeriod === period
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {period.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>
        
        <TradingViewChart 
          ticker={ticker}
          period={chartPeriod}
          height={500}
        />
      </div>

      {/* 4. Financial Data - Supporting Content */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-semibold text-gray-900">
              Financial Data & Metrics
            </h3>
            <button
              onClick={() => setShowFinancialDetails(!showFinancialDetails)}
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              {showFinancialDetails ? 'Hide Details' : 'Show Details'}
            </button>
          </div>
        </div>
        
        <FinancialDataTable 
          ticker={ticker}
          showDetails={showFinancialDetails}
        />
      </div>

      {/* 5. News & Sentiment - Additional Context */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-xl font-semibold text-gray-900">
            News & Market Sentiment
          </h3>
        </div>
        
        <NewsAndSentiment 
          ticker={ticker}
          maxArticles={10}
        />
      </div>
    </div>
  );
};

export default StockAnalysis;