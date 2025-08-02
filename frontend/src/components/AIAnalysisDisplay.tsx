/**
 * AI Analysis Display Component
 * Shows AI-generated stock analysis with rating, confidence, and detailed insights
 */

import React from 'react';
import { AIAnalysisResult } from '../types/ai-analysis';
import LoadingSpinner from './LoadingSpinner';

interface AIAnalysisDisplayProps {
  analysis: AIAnalysisResult | null;
  isLoading: boolean;
  analysisType: 'short_term' | 'mid_term' | 'long_term';
  onRefresh: () => void;
}

const AIAnalysisDisplay: React.FC<AIAnalysisDisplayProps> = ({
  analysis,
  isLoading,
  analysisType,
  onRefresh
}) => {
  const getRatingColor = (rating: string) => {
    switch (rating.toLowerCase()) {
      case 'strong bullish':
        return 'text-success-700 bg-success-50 border-success-200';
      case 'bullish':
        return 'text-success-600 bg-success-50 border-success-200';
      case 'neutral':
        return 'text-gray-600 bg-gray-50 border-gray-200';
      case 'bearish':
        return 'text-danger-600 bg-danger-50 border-danger-200';
      case 'strong bearish':
        return 'text-danger-700 bg-danger-50 border-danger-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-success-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-danger-600';
  };

  const getAnalysisTypeDescription = (type: string) => {
    switch (type) {
      case 'short_term':
        return 'Technical momentum analysis based on price action, volume, and sentiment';
      case 'mid_term':
        return 'Fundamental trend analysis based on earnings, growth, and industry outlook';
      case 'long_term':
        return 'Strategic value analysis based on business quality and competitive advantages';
      default:
        return 'Comprehensive analysis';
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center">
        <LoadingSpinner size="large" />
        <p className="mt-4 text-gray-600">Generating AI analysis...</p>
        <p className="text-sm text-gray-500">This may take 10-30 seconds</p>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="p-8 text-center">
        <div className="text-gray-400 mb-4">
          <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Analysis Available</h3>
        <p className="text-gray-600 mb-4">Click the button below to generate AI analysis</p>
        <button
          onClick={onRefresh}
          className="btn-primary"
        >
          Generate Analysis
        </button>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Analysis Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <div className={`px-4 py-2 rounded-lg border font-semibold ${getRatingColor(analysis.rating)}`}>
            {analysis.rating}
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">Confidence:</span>
            <span className={`font-semibold ${getConfidenceColor(analysis.confidence)}`}>
              {(analysis.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
        <button
          onClick={onRefresh}
          className="text-primary-600 hover:text-primary-700 text-sm font-medium flex items-center space-x-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>Refresh</span>
        </button>
      </div>

      {/* Analysis Type Description */}
      <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <p className="text-sm text-blue-800">
          <strong>{analysisType.replace('_', '-').toUpperCase()} ANALYSIS:</strong>{' '}
          {getAnalysisTypeDescription(analysisType)}
        </p>
      </div>

      {/* Price Target Range */}
      {analysis.priceTargetRange && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <h4 className="font-semibold text-gray-900 mb-2">Price Target Range</h4>
          <div className="flex items-center space-x-4">
            <div className="text-center">
              <div className="text-sm text-gray-500">Min Target</div>
              <div className="text-lg font-semibold text-gray-900">
                ¥{analysis.priceTargetRange.min?.toLocaleString() || 'N/A'}
              </div>
            </div>
            <div className="flex-1 h-2 bg-gray-200 rounded-full relative">
              <div className="absolute inset-0 bg-gradient-to-r from-danger-400 via-yellow-400 to-success-400 rounded-full"></div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-500">Max Target</div>
              <div className="text-lg font-semibold text-gray-900">
                ¥{analysis.priceTargetRange.max?.toLocaleString() || 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Key Factors */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-900 mb-3">Key Factors</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {analysis.keyFactors.map((factor, index) => (
            <div key={index} className="flex items-start space-x-2 p-3 bg-green-50 rounded-lg border border-green-200">
              <svg className="w-5 h-5 text-success-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="text-sm text-gray-700">{factor}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Risk Factors */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-900 mb-3">Risk Factors</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {analysis.riskFactors.map((risk, index) => (
            <div key={index} className="flex items-start space-x-2 p-3 bg-red-50 rounded-lg border border-red-200">
              <svg className="w-5 h-5 text-danger-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span className="text-sm text-gray-700">{risk}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Detailed Reasoning */}
      {analysis.reasoning && (
        <div className="mb-6">
          <h4 className="font-semibold text-gray-900 mb-3">Analysis Reasoning</h4>
          <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
            <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
              {analysis.reasoning}
            </p>
          </div>
        </div>
      )}

      {/* Analysis Metadata */}
      <div className="pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm text-gray-500">
          <div className="flex items-center space-x-4">
            <span>Generated: {new Date(analysis.generatedAt).toLocaleString()}</span>
            <span>Model: {analysis.modelVersion}</span>
          </div>
          <div className="flex items-center space-x-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>AI-generated analysis</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIAnalysisDisplay;