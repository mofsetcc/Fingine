/**
 * News and Sentiment Component
 * Displays news articles related to a stock with sentiment analysis
 */

import React, { useEffect, useState } from 'react';

interface NewsArticle {
  id: string;
  headline: string;
  summary: string;
  source: string;
  published_at: string;
  url: string;
  sentiment_score: number;
  relevance_score: number;
}

interface SentimentSummary {
  overall_sentiment: 'positive' | 'negative' | 'neutral';
  sentiment_score: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  total_articles: number;
}

interface NewsAndSentimentProps {
  ticker: string;
  maxArticles?: number;
}

const NewsAndSentiment: React.FC<NewsAndSentimentProps> = ({
  ticker,
  maxArticles = 10
}) => {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [sentimentSummary, setSentimentSummary] = useState<SentimentSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchNewsData();
  }, [ticker]);

  const fetchNewsData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/v1/stocks/${ticker}/news?limit=${maxArticles}`);
      if (!response.ok) {
        throw new Error('Failed to fetch news data');
      }

      const data = await response.json();
      setArticles(data.articles || []);
      setSentimentSummary(data.sentiment_summary || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch news');
    } finally {
      setIsLoading(false);
    }
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.1) return 'text-success-600 bg-success-50';
    if (score < -0.1) return 'text-danger-600 bg-danger-50';
    return 'text-gray-600 bg-gray-50';
  };

  const getSentimentLabel = (score: number) => {
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

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center">
        <div className="loading-spinner"></div>
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
        <button onClick={fetchNewsData} className="btn-primary">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-6">
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
              <div className="text-2xl font-bold text-success-600">
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
              <div className="text-2xl font-bold text-danger-600">
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
        {articles.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-gray-400 mb-4">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9.5a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Recent News</h3>
            <p className="text-gray-600">No news articles found for this stock in the past week.</p>
          </div>
        ) : (
          articles.map((article) => (
            <div key={article.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <h5 className="font-semibold text-gray-900 mb-1 line-clamp-2">
                    <a 
                      href={article.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="hover:text-primary-600 transition-colors"
                    >
                      {article.headline}
                    </a>
                  </h5>
                  <div className="flex items-center space-x-3 text-sm text-gray-500 mb-2">
                    <span>{article.source}</span>
                    <span>•</span>
                    <span>{formatDate(article.published_at)}</span>
                    <span>•</span>
                    <span>Relevance: {(article.relevance_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <div className={`px-3 py-1 rounded-full text-sm font-medium ${getSentimentColor(article.sentiment_score)}`}>
                  {getSentimentLabel(article.sentiment_score)}
                </div>
              </div>
              
              {article.summary && (
                <p className="text-gray-700 text-sm leading-relaxed line-clamp-3">
                  {article.summary}
                </p>
              )}
              
              <div className="mt-3 flex items-center justify-between">
                <div className="flex items-center space-x-2 text-xs text-gray-500">
                  <span>Sentiment Score: {article.sentiment_score.toFixed(2)}</span>
                </div>
                <a 
                  href={article.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:text-primary-700 text-sm font-medium flex items-center space-x-1"
                >
                  <span>Read more</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Load More Button */}
      {articles.length >= maxArticles && (
        <div className="mt-6 text-center">
          <button 
            onClick={() => {/* TODO: Implement load more functionality */}}
            className="btn-secondary"
          >
            Load More Articles
          </button>
        </div>
      )}

      {/* Data Attribution */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 text-center">
          News data aggregated from Nikkei, Reuters Japan, Yahoo Finance Japan, and company press releases.
          Sentiment analysis powered by Japanese NLP models.
        </p>
      </div>
    </div>
  );
};

export default NewsAndSentiment;