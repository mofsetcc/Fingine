/**
 * AI Analysis TypeScript interfaces
 */

import { BaseEntity, PaginatedResponse, Timestamp, UUID } from './base';

// AI Analysis Request Types
export type AnalysisType = 
  | 'fundamental' 
  | 'technical' 
  | 'sentiment' 
  | 'risk_assessment'
  | 'price_prediction' 
  | 'earnings_forecast' 
  | 'peer_comparison'
  | 'market_outlook' 
  | 'investment_recommendation';

export type AnalysisLanguage = 'ja' | 'en';

export interface AIAnalysisRequest {
  ticker: string;
  analysis_type: AnalysisType;
  parameters?: Record<string, any>;
  language: AnalysisLanguage;
}

export interface BulkAnalysisRequest {
  tickers: string[];
  analysis_type: AnalysisType;
  parameters?: Record<string, any>;
  language: AnalysisLanguage;
}

// AI Analysis Response Types
export type AnalysisStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface AIAnalysis extends BaseEntity {
  ticker: string;
  analysis_type: AnalysisType;
  status: AnalysisStatus;
  language: AnalysisLanguage;
  user_id: UUID;
  result?: Record<string, any>;
  error_message?: string;
  processing_time_seconds?: number;
  tokens_used?: number;
  cost_usd?: number;
}

export interface AIAnalysisCreate {
  ticker: string;
  analysis_type: AnalysisType;
  status: AnalysisStatus;
  language: AnalysisLanguage;
  user_id: UUID;
  parameters?: Record<string, any>;
}

// Specific Analysis Result Types
export interface FundamentalAnalysisResult {
  overall_score: number; // 0-100
  financial_health: Record<string, any>;
  valuation: Record<string, any>;
  growth_prospects: Record<string, any>;
  competitive_position: Record<string, any>;
  risks: string[];
  opportunities: string[];
  summary: string;
  recommendation: string;
  target_price?: number;
  confidence_level: number; // 0-1
}

export type TechnicalSignal = 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';

export interface TechnicalAnalysisResult {
  overall_signal: TechnicalSignal;
  trend_analysis: Record<string, any>;
  support_resistance: Record<string, any>;
  indicators: Record<string, any>;
  chart_patterns: string[];
  volume_analysis: Record<string, any>;
  momentum: Record<string, any>;
  summary: string;
  short_term_outlook: string;
  medium_term_outlook: string;
  key_levels: Record<string, number>;
}

export type SentimentLevel = 'very_positive' | 'positive' | 'neutral' | 'negative' | 'very_negative';

export interface SentimentAnalysisResult {
  overall_sentiment: SentimentLevel;
  sentiment_score: number; // -1 to 1
  news_sentiment: Record<string, any>;
  social_sentiment: Record<string, any>;
  analyst_sentiment: Record<string, any>;
  sentiment_trends: Array<Record<string, any>>;
  key_themes: string[];
  sentiment_drivers: string[];
  summary: string;
}

export type RiskLevel = 'very_low' | 'low' | 'moderate' | 'high' | 'very_high';

export interface RiskAssessmentResult {
  overall_risk_level: RiskLevel;
  risk_score: number; // 0-100
  financial_risks: Array<Record<string, any>>;
  market_risks: Array<Record<string, any>>;
  operational_risks: Array<Record<string, any>>;
  regulatory_risks: Array<Record<string, any>>;
  volatility_analysis: Record<string, any>;
  correlation_analysis: Record<string, any>;
  risk_mitigation: string[];
  summary: string;
}

export type PredictionHorizon = '1_week' | '1_month' | '3_months' | '6_months' | '1_year';

export interface PricePredictionResult {
  prediction_horizon: PredictionHorizon;
  predicted_price: number;
  current_price: number;
  price_change_percent: number;
  confidence_interval: Record<string, number>;
  prediction_factors: string[];
  model_accuracy?: number;
  scenarios: Record<string, Record<string, number>>;
  risks_to_prediction: string[];
  summary: string;
}

// Analysis History Types
export interface AnalysisHistory {
  user_id: UUID;
  analyses: AIAnalysis[];
  total_analyses: number;
  analyses_this_month: number;
  favorite_analysis_types: string[];
  total_cost_usd: number;
}

// Analysis Queue Types
export interface AnalysisQueueStatus {
  queue_position: number;
  estimated_wait_time: number; // seconds
  total_queue_size: number;
  processing_capacity: number;
}

// Analysis Comparison Types
export interface AnalysisComparison {
  tickers: string[];
  analysis_type: AnalysisType;
  comparison_metrics: Record<string, any>;
  rankings: Array<Record<string, any>>;
  summary: string;
  created_at: Timestamp;
}

// Analysis Export Types
export type AnalysisExportFormat = 'pdf' | 'excel' | 'csv' | 'json';

export interface AnalysisExportRequest {
  analysis_ids: UUID[];
  format: AnalysisExportFormat;
  include_charts: boolean;
  language: AnalysisLanguage;
}

export type ExportStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'expired';

export interface AnalysisExportResponse {
  export_id: UUID;
  download_url?: string;
  status: ExportStatus;
  created_at: Timestamp;
  expires_at?: Timestamp;
}

// Analysis Statistics Types
export interface AnalysisStatistics {
  total_analyses: number;
  analyses_by_type: Record<string, number>;
  analyses_by_language: Record<string, number>;
  average_processing_time: number;
  success_rate: number;
  total_cost_usd: number;
  most_analyzed_stocks: Array<Record<string, any>>;
  peak_usage_hours: number[];
  user_satisfaction_score?: number;
}

// Analysis Configuration Types
export interface AnalysisConfig {
  analysis_type: AnalysisType;
  parameters: {
    time_horizon?: PredictionHorizon;
    include_technical_indicators?: boolean;
    include_fundamental_data?: boolean;
    include_news_sentiment?: boolean;
    include_peer_comparison?: boolean;
    risk_tolerance?: 'conservative' | 'moderate' | 'aggressive';
    investment_style?: 'value' | 'growth' | 'momentum' | 'dividend';
    market_conditions?: 'bull' | 'bear' | 'sideways';
  };
  output_preferences: {
    language: AnalysisLanguage;
    detail_level: 'summary' | 'detailed' | 'comprehensive';
    include_charts: boolean;
    include_recommendations: boolean;
    format: 'text' | 'structured' | 'bullet_points';
  };
}

// Analysis Template Types
export interface AnalysisTemplate {
  id: UUID;
  name: string;
  description: string;
  analysis_type: AnalysisType;
  config: AnalysisConfig;
  is_public: boolean;
  created_by: UUID;
  usage_count: number;
  created_at: Timestamp;
  updated_at: Timestamp;
}

export interface AnalysisTemplateCreate {
  name: string;
  description: string;
  analysis_type: AnalysisType;
  config: AnalysisConfig;
  is_public?: boolean;
}

// Analysis Feedback Types
export interface AnalysisFeedback {
  id: UUID;
  analysis_id: UUID;
  user_id: UUID;
  rating: number; // 1-5 scale
  feedback_text?: string;
  helpful_aspects: string[];
  improvement_suggestions: string[];
  would_recommend: boolean;
  created_at: Timestamp;
}

export interface AnalysisFeedbackCreate {
  analysis_id: UUID;
  rating: number;
  feedback_text?: string;
  helpful_aspects: string[];
  improvement_suggestions: string[];
  would_recommend: boolean;
}

// Analysis Sharing Types
export interface AnalysisShare {
  id: UUID;
  analysis_id: UUID;
  shared_by: UUID;
  share_token: string;
  is_public: boolean;
  expires_at?: Timestamp;
  view_count: number;
  created_at: Timestamp;
}

export interface AnalysisShareCreate {
  analysis_id: UUID;
  is_public: boolean;
  expires_at?: Timestamp;
}

// Analysis State Types (for Redux/Context)
export interface AIAnalysisState {
  // Current analyses
  analyses: {
    [ticker: string]: {
      [analysisType: string]: AIAnalysis;
    };
  };
  
  // Analysis history
  history: AIAnalysis[];
  historyPagination: {
    page: number;
    total_pages: number;
    total_items: number;
  };
  
  // Queue status
  queueStatus: AnalysisQueueStatus | null;
  
  // Templates
  templates: AnalysisTemplate[];
  
  // Current analysis request
  currentRequest: AIAnalysisRequest | null;
  
  // Loading states
  isLoadingAnalysis: boolean;
  isLoadingHistory: boolean;
  isLoadingTemplates: boolean;
  isSubmittingRequest: boolean;
  
  // Error states
  analysisError?: string;
  historyError?: string;
  templatesError?: string;
  requestError?: string;
  
  // UI state
  selectedAnalysisType: AnalysisType;
  selectedLanguage: AnalysisLanguage;
  analysisConfig: AnalysisConfig;
  
  // Statistics
  statistics: AnalysisStatistics | null;
  
  // Last updated timestamps
  lastUpdated: {
    analyses?: Timestamp;
    history?: Timestamp;
    templates?: Timestamp;
    statistics?: Timestamp;
  };
}

// Analysis Form Types
export interface AnalysisFormData {
  ticker: string;
  analysis_type: AnalysisType;
  language: AnalysisLanguage;
  parameters: Record<string, any>;
  save_as_template: boolean;
  template_name?: string;
  template_description?: string;
}

export interface BulkAnalysisFormData {
  tickers: string[];
  analysis_type: AnalysisType;
  language: AnalysisLanguage;
  parameters: Record<string, any>;
  batch_name?: string;
}

// Analysis Display Types
export interface AnalysisDisplayConfig {
  show_summary: boolean;
  show_details: boolean;
  show_charts: boolean;
  show_recommendations: boolean;
  show_risks: boolean;
  show_metadata: boolean;
  compact_view: boolean;
}

export interface AnalysisCard {
  analysis: AIAnalysis;
  displayConfig: AnalysisDisplayConfig;
  onShare?: (analysis: AIAnalysis) => void;
  onExport?: (analysis: AIAnalysis) => void;
  onFeedback?: (analysis: AIAnalysis) => void;
  onDelete?: (analysis: AIAnalysis) => void;
}

// Paginated AI Analysis Response
export type PaginatedAIAnalysisResponse = PaginatedResponse<AIAnalysis>;