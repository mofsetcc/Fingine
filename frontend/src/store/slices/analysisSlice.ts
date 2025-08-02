/**
 * AI Analysis state management slice.
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { AIAnalysisResult } from '../../types/ai-analysis';

interface AnalysisState {
  currentAnalysis: AIAnalysisResult | null;
  analysisHistory: AIAnalysisResult[];
  isLoading: boolean;
  error: string | null;
}

const initialState: AnalysisState = {
  currentAnalysis: null,
  analysisHistory: [],
  isLoading: false,
  error: null,
};

const analysisSlice = createSlice({
  name: 'analysis',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    setCurrentAnalysis: (state, action: PayloadAction<AIAnalysisResult | null>) => {
      state.currentAnalysis = action.payload;
      if (action.payload) {
        // Add to history if not already present
        const exists = state.analysisHistory.find(
          analysis => 
            analysis.ticker === action.payload!.ticker && 
            analysis.analysisType === action.payload!.analysisType &&
            analysis.generatedAt === action.payload!.generatedAt
        );
        if (!exists) {
          state.analysisHistory.unshift(action.payload);
          // Keep only last 50 analyses
          state.analysisHistory = state.analysisHistory.slice(0, 50);
        }
      }
    },
    setAnalysisHistory: (state, action: PayloadAction<AIAnalysisResult[]>) => {
      state.analysisHistory = action.payload;
    },
    clearCurrentAnalysis: (state) => {
      state.currentAnalysis = null;
    },
    clearAnalysisHistory: (state) => {
      state.analysisHistory = [];
    },
  },
});

export const {
  setLoading,
  setError,
  setCurrentAnalysis,
  setAnalysisHistory,
  clearCurrentAnalysis,
  clearAnalysisHistory,
} = analysisSlice.actions;

export default analysisSlice.reducer;