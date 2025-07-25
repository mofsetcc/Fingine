/**
 * News and sentiment state management slice.
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { NewsArticle } from '../../types';

interface NewsState {
  articles: NewsArticle[];
  isLoading: boolean;
  error: string | null;
}

const initialState: NewsState = {
  articles: [],
  isLoading: false,
  error: null,
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
      state.articles = [...newArticles, ...state.articles];
    },
    clearArticles: (state) => {
      state.articles = [];
    },
  },
});

export const {
  setLoading,
  setError,
  setArticles,
  addArticles,
  clearArticles,
} = newsSlice.actions;

export default newsSlice.reducer;