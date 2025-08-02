/**
 * News and Sentiment Component
 * Displays news articles related to a stock with sentiment analysis
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
    NewsArticle,
    NewsFilters,
    NewsSortOptions,
    SentimentSummary,
    SentimentTimelinePoint
} from '../types/news';

interface NewsAndSentimentProps {
  ticker: string;
  maxArticles?: number;
}

const NewsAndSentiment: React.FC<NewsAndSentimentProps> = ({
  ticker,
  maxArticles = 20
}) => {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [sentimentSummary, setSentimentSummary] = useState<SentimentSummary | null>(null);
  const [sentimentTimeline, setSentimentTimeline] = useState<SentimentTimelinePoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  
  // Filters and sorting
  const [filters, setFilters] = useState<NewsFilters>({
    sentiment: 'all',
    min_relevance: 0.1
  });
  const [sort, setSort] = useState<NewsSortOptions>({
    field: 'published_at',
    order: 'desc'
  });
  
  // UI state
  const [showFilters, setShowFilters] = useState(false);
  const [selectedTimeRange, setSelectedTimeRange] = useState<'1d' | '3d' | '7d' | '30d'>('7d');

  useEffect(() => {
    fetchNewsData();
  }, [ticker, filters, sort, selectedTimeRange]);

  const fetchNewsData = async (loadMore = false) => {
    if (!loadMore) {
      setIsLoading(true);
      setError(null);
    }

    try {
      const params = new URLSearchParams({
        limit: maxArticles.toString(),
        offset: loadMore ? articles.length.toString() : '0',
        sort_by: sort.field,
        sort_order: sort.order,
        time_range: selectedTimeRange
      });

      // Add filters
      if (filters.sentiment && filters.sentiment !== 'all') {
        params.append('sentiment', filters.sentiment);
      }
      if (filters.source) {
        params.append('source', filters.source);
      }
      if (filters.min_relevance !== undefined) {
        params.append('min_relevance', filters.min_relevance.toString());
      }
      if (filters.date_range) {
        params.append('start_date', filters.date_range.start);
        params.append('end_date', filters.date_range.end);
      }

      const response = await fetch(`/api/v1/stocks/${ticker}/news?${params}`);
      if (!response.ok) {
        throw new Error('Failed to fetch news data');
      }

      const data = await response.json();
      
      if (loadMore) {
        setArticles(prev => [...prev, ...(data.articles || [])]);
      } else {
        setArticles(data.articles || []);
        setSentimentSummary(data.sentiment_summary || null);
        setSentimentTimeline(data.sentiment_timeline || []);
        setTotalCount(data.total_count || 0);
      }
      
      setHasMore(data.has_more || false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch news');
    } finally {
      setIsLoading(false);
    }
  };

  const loadMoreArticles = () => {
    if (!isLoading && hasMore) {
      fetchNewsData(true);
    }
  };

  // Utility functions
  const getSentimentColor = (score?: number) => {
    if (!score) return 'text-gray-600 bg-gray-50';
    if (score > 0.1) return 'text-green-600 bg-green-50';
    if (score < -0.1) return 'text-red-600 bg-red-50';
    return 'text-gray-600 bg-gray-50';
  };

  const getSentimentLabel = (score?: number) => {
    if (!score) return 'Neutral';
    if (score > 0.5) return 'Very Positive';
    if (score > 0.1) return 'Positive';
    if (score < -0.5) return 'Very Negative';
    if (score < -0.1) return 'Negative';
    return 'Neutral';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatRelativeTime = (dateString: string) => {
    const now = new Date();
    const date = new Date(dateString);
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(dateString);
  };

  // Get unique sources for filter dropdown
  const availableSources = useMemo(() => {
    const sources = new Set(articles.map(article => article.source).filter(Boolean));
    return Array.from(sources).sort();
  }, [articles]);

  // Handle filter changes
  const handleFilterChange = (newFilters: Partial<NewsFilters>) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
  };

  const handleSortChange = (newSort: NewsSortOptions) => {
    setSort(newSort);
  };

  const clearFilters = () => {
    setFilters({
      sentiment: 'all',
      min_relevance: 0.1
    });
  };

  // Sentiment Timeline Component
  const SentimentTimeline: React.FC<{ data: SentimentTimelinePoint[] }> = ({ data }) => {
    if (!data || data.length === 0) return null;

    const normalizedData = data.map(point => ({
      ...point,
      normalizedScore: (point.sentiment_score + 1) / 2 // Convert -1,1 to 0,1
    }));

    return (
      <div className="mb-6">
        <h4 className="font-semibold text-gray-900 mb-3">Sentiment Timeline ({selectedTimeRange})</h4>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
            <span>Negative</span>
            <span>Neutral</span>
            <span>Positive</span>
          </div>
          
          <div className="relative h-20 bg-gradient-to-r from-red-100 via-gray-100 to-green-100 rounded">
            {normalizedData.map((point, index) => (
              <div
                key={point.timestamp}
                className="absolute w-2 bg-blue-500 rounded-full opacity-70 hover:opacity-100 transition-opacity cursor-pointer"
                style={{
                  left: `${(index / (normalizedData.length - 1)) * 100}%`,
                  bottom: `${point.normalizedScore * 100}%`,
                  height: `${Math.max(8, (point.article_count / Math.max(...data.map(d => d.article_count))) * 20)}px`,
                  transform: 'translateX(-50%)'
                }}
                title={`${formatDate(point.timestamp)}: ${getSentimentLabel(point.sentiment_score)} (${point.article_count} articles)`}
              />
            ))}
          </div>
          
          <div className="flex justify-between text-xs text-gray-500 mt-2">
            <span>{formatDate(data[0]?.timestamp || '')}</span>
            <span>{formatDate(data[data.length - 1]?.timestamp || '')}</span>
          </div>
        </div>
      </div>
    );
  };

  if (isLoading && articles.length === 0) {
    return (
      <div className="p-8 flex justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" role="status" aria-label="Loading news"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center">
        <div className="text-red-400 mb-4">
          <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">News Unavailable</h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button onClick={() => fetchNewsData()} className="btn-primary">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header with Controls */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">News & Sentiment</h3>
          {totalCount > 0 && (
            <p className="text-sm text-gray-500">{totalCount} articles found</p>
          )}
        </div>
        
        <div className="flex items-center space-x-3">
          {/* Time Range Selector */}
          <div className="flex bg-gray-100 rounded-lg p-1">
            {(['1d', '3d', '7d', '30d'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setSelectedTimeRange(range)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  selectedTimeRange === range
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
          
          {/* Filter Toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 rounded-lg transition-colors ${
              showFilters ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            aria-label="Toggle filters"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Sentiment Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Sentiment</label>
              <select
                value={filters.sentiment || 'all'}
                onChange={(e) => handleFilterChange({ sentiment: e.target.value as any })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Sentiments</option>
                <option value="positive">Positive</option>
                <option value="neutral">Neutral</option>
                <option value="negative">Negative</option>
              </select>
            </div>

            {/* Source Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Source</label>
              <select
                value={filters.source || ''}
                onChange={(e) => handleFilterChange({ source: e.target.value || undefined })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Sources</option>
                {availableSources.map(source => (
                  <option key={source} value={source}>{source}</option>
                ))}
              </select>
            </div>

            {/* Sort Options */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Sort By</label>
              <select
                value={`${sort.field}-${sort.order}`}
                onChange={(e) => {
                  const [field, order] = e.target.value.split('-');
                  handleSortChange({ field: field as any, order: order as any });
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="published_at-desc">Newest First</option>
                <option value="published_at-asc">Oldest First</option>
                <option value="relevance_score-desc">Most Relevant</option>
                <option value="sentiment_score-desc">Most Positive</option>
                <option value="sentiment_score-asc">Most Negative</option>
              </select>
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={clearFilters}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              Clear Filters
            </button>
          </div>
        </div>
      )}

      {/* Sentiment Timeline */}
      <SentimentTimeline data={sentimentTimeline} />

      {/* Sentiment Summary */}
      {sentimentSummary && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <h4 className="font-semibold text-gray-900 mb-3">Market Sentiment Overview</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className={`text-2xl font-bold ${getSentimentColor(sentimentSummary.sentiment_score).split(' ')[0]}`}>
                {getSentimentLabel(sentimentSummary.sentiment_score)}
              </div>
              <div className="text-sm text-gray-500">Overall Sentiment</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {sentimentSummary.positive_count}
              </div>
              <div className="text-sm text-gray-500">Positive Articles</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-600">
                {sentimentSummary.neutral_count}
              </div>
              <div className="text-sm text-gray-500">Neutral Articles</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {sentimentSummary.negative_count}
              </div>
              <div className="text-sm text-gray-500">Negative Articles</div>
            </div>
          </div>
          
          {/* Sentiment Score Bar */}
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
              <span>Negative</span>
              <span>Sentiment Score: {sentimentSummary.sentiment_score.toFixed(2)}</span>
              <span>Positive</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div 
                className="h-3 rounded-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500"
                style={{ width: '100%' }}
              ></div>
              <div 
                className="relative -mt-3 w-1 h-3 bg-gray-800 rounded-full"
                style={{ 
                  marginLeft: `${((sentimentSummary.sentiment_score + 1) / 2) * 100}%`,
                  transform: 'translateX(-50%)'
                }}
              ></div>
            </div>
          </div>
        </div>
      )}

      {/* News Articles */}
      <div className="space-y-4">
        {articles.length === 0 && !isLoading ? (
          <div className="text-center py-8">
            <div className="text-gray-400 mb-4">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9.5a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No News Found</h3>
            <p className="text-gray-600">
              No news articles found for the selected filters and time range.
            </p>
            {(filters.sentiment !== 'all' || filters.source) && (
              <button
                onClick={clearFilters}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Clear Filters
              </button>
            )}
          </div>
        ) : (
          articles.map((article) => (
            <div key={article.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-all duration-200 bg-white">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <h5 className="font-semibold text-gray-900 mb-2 leading-tight">
                    <a 
                      href={article.article_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="hover:text-blue-600 transition-colors line-clamp-2"
                    >
                      {article.headline}
                    </a>
                  </h5>
                  <div className="flex flex-wrap items-center gap-2 text-sm text-gray-500 mb-2">
                    {article.source && (
                      <span className="bg-gray-100 px-2 py-1 rounded text-xs font-medium">
                        {article.source}
                      </span>
                    )}
                    <span>{formatRelativeTime(article.published_at)}</span>
                    {article.relevance_score && (
                      <>
                        <span>•</span>
                        <span>Relevance: {(article.relevance_score * 100).toFixed(0)}%</span>
                      </>
                    )}
                  </div>
                </div>
                
                {/* Sentiment Badge */}
                <div className={`ml-4 px-3 py-1 rounded-full text-sm font-medium whitespace-nowrap ${getSentimentColor(article.sentiment_score)}`}>
                  {getSentimentLabel(article.sentiment_score)}
                </div>
              </div>
              
              {article.content_summary && (
                <p className="text-gray-700 text-sm leading-relaxed mb-3 line-clamp-3">
                  {article.content_summary}
                </p>
              )}
              
              <div className="flex items-center justify-between pt-2 border-t border-gray-100">
                <div className="flex items-center space-x-4 text-xs text-gray-500">
                  {article.sentiment_score !== undefined && (
                    <span className="flex items-center space-x-1">
                      <span>Sentiment:</span>
                      <span className={`font-medium ${
                        article.sentiment_score > 0 ? 'text-green-600' : 
                        article.sentiment_score < 0 ? 'text-red-600' : 'text-gray-600'
                      }`}>
                        {article.sentiment_score > 0 ? '+' : ''}{article.sentiment_score.toFixed(2)}
                      </span>
                    </span>
                  )}
                  {article.author && (
                    <span>By {article.author}</span>
                  )}
                </div>
                
                {article.article_url && (
                  <a 
                    href={article.article_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-700 text-sm font-medium flex items-center space-x-1 transition-colors"
                  >
                    <span>Read more</span>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Load More Button */}
      {hasMore && (
        <div className="mt-6 text-center">
          <button 
            onClick={loadMoreArticles}
            disabled={isLoading}
            className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 mx-auto"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                <span>Loading...</span>
              </>
            ) : (
              <>
                <span>Load More Articles</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </>
            )}
          </button>
        </div>
      )}

      {/* Loading indicator for additional articles */}
      {isLoading && articles.length > 0 && (
        <div className="mt-4 text-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
        </div>
      )}

      {/* Data Attribution */}
      <div className="mt-8 pt-4 border-t border-gray-200">
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-2">
            News data aggregated from Nikkei, Reuters Japan, Yahoo Finance Japan, and company press releases.
          </p>
          <p className="text-xs text-gray-500">
            Sentiment analysis powered by Japanese NLP models. Data updated hourly.
          </p>
          {sentimentSummary && (
            <p className="text-xs text-gray-400 mt-1">
              Last updated: {formatDate(new Date().toISOString())}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default NewsAndSentiment;