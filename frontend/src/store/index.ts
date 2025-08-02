/**
 * Redux store configuration for Project Kessan.
 */

import { configureStore } from '@reduxjs/toolkit';
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';

// Slice imports (will be created in later tasks)
import analysisSlice from './slices/analysisSlice';
import authSlice from './slices/authSlice';
import newsSlice from './slices/newsSlice';
import stocksSlice from './slices/stocksSlice';
import subscriptionSlice from './slices/subscriptionSlice';
import uiSlice from './slices/uiSlice';
import watchlistSlice from './slices/watchlistSlice';

export const store = configureStore({
  reducer: {
    auth: authSlice,
    stocks: stocksSlice,
    analysis: analysisSlice,
    news: newsSlice,
    subscription: subscriptionSlice,
    ui: uiSlice,
    watchlist: watchlistSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
  devTools: process.env.NODE_ENV !== 'production',
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Typed hooks
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;