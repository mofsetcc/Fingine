/**
 * News and sentiment state management slice.
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import {
    NewsArticle,
    NewsFilters,
    NewsSortOptions,
    NewsState,
    SentimentSummary,
    SentimentTimelinePoint
} from '../../types/news';

const initialState: NewsState = {
  articles: [],
  sentiment_summary: undefined,
  sentiment_timeline: undefined,
  filters: {
    sentiment: 'all',
    min_relevance: 0.1
  },
  sort: {
    field: 'published_at',
    order: 'desc'
  },
  isLoading: false,
  error: null,
  hasMore: false,
  totalCount: 0
};

const newsSlice = createSlice({
  name: 'news',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    setArticles: (state, action: PayloadAction<NewsArticle[]>) => {
      state.articles = action.payload;
    },
    addArticles: (state, action: PayloadAction<NewsArticle[]>) => {
      // Add new articles and remove duplicates
      const existingIds = new Set(state.articles.map(article => article.id));
      const newArticles = action.payload.filter(article => !existingIds.has(article.id));
      state.articles = [...state.articles, ...newArticles];
    },
    clearArticles: (state) => {
      state.articles = [];
    },
    setSentimentSummary: (state, action: PayloadAction<SentimentSummary | undefined>) => {
      state.sentiment_summary = action.payload;
    },
    setSentimentTimeline: (state, action: PayloadAction<SentimentTimelinePoint[] | undefined>) => {
      state.sentiment_timeline = action.payload;
    },
    setFilters: (state, action: PayloadAction<NewsFilters>) => {
      state.filters = action.payload;
    },
    updateFilters: (state, action: PayloadAction<Partial<NewsFilters>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    setSort: (state, action: PayloadAction<NewsSortOptions>) => {
      state.sort = action.payload;
    },
    setHasMore: (state, action: PayloadAction<boolean>) => {
      state.hasMore = action.payload;
    },
    setTotalCount: (state, action: PayloadAction<number>) => {
      state.totalCount = action.payload;
    },
    resetNewsState: (state) => {
      return { ...initialState };
    }
  },
});

export const {
  setLoading,
  setError,
  setArticles,
  addArticles,
  clearArticles,
  setSentimentSummary,
  setSentimentTimeline,
  setFilters,
  updateFilters,
  setSort,
  setHasMore,
  setTotalCount,
  resetNewsState
} = newsSlice.actions;

export default newsSlice.reducer;