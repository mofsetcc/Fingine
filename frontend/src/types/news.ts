/**
 * News and sentiment related types
 */

import { Timestamp, UUID } from './base';

export interface NewsArticle {
  id: UUID;
  headline: string;
  content_summary?: string;
  source?: string;
  author?: string;
  published_at: Timestamp;
  article_url?: string;
  sentiment_label?: 'positive' | 'negative' | 'neutral';
  sentiment_score?: number; // -1.0 to 1.0
  language: string;
  relevance_score?: number; // 0.0 to 1.0 (for stock-specific news)
}

export interface SentimentSummary {
  overall_sentiment: 'positive' | 'negative' | 'neutral';
  sentiment_score: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  total_articles: number;
}

export interface SentimentTimelinePoint {
  timestamp: Timestamp;
  sentiment_score: number;
  article_count: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
}

export interface NewsResponse {
  articles: NewsArticle[];
  sentiment_summary?: SentimentSummary;
  sentiment_timeline?: SentimentTimelinePoint[];
  total_count: number;
  has_more: boolean;
}

export interface NewsFilters {
  sentiment?: 'positive' | 'negative' | 'neutral' | 'all';
  source?: string;
  date_range?: {
    start: string;
    end: string;
  };
  min_relevance?: number;
}

export interface NewsSortOptions {
  field: 'published_at' | 'relevance_score' | 'sentiment_score';
  order: 'asc' | 'desc';
}

export interface NewsState {
  articles: NewsArticle[];
  sentiment_summary?: SentimentSummary;
  sentiment_timeline?: SentimentTimelinePoint[];
  filters: NewsFilters;
  sort: NewsSortOptions;
  isLoading: boolean;
  error: string | null;
  hasMore: boolean;
  totalCount: number;
}