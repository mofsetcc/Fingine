/**
 * Financial data TypeScript interfaces
 */

import { BaseEntity, DateString, PaginatedResponse, Timestamp } from './base';

// Financial Report Types
export type FiscalPeriod = 'Q1' | 'Q2' | 'Q3' | 'Q4' | 'FY' | 'H1' | 'H2';
export type ReportType = 'earnings' | 'balance_sheet' | 'cash_flow' | 'income_statement';

export interface FinancialReport extends BaseEntity {
  ticker: string;
  fiscal_year: number;
  fiscal_period: FiscalPeriod;
  report_type: ReportType;
  announced_at: Timestamp;
  source_url?: string;
  data: Record<string, any>;
}

export interface FinancialReportCreate {
  ticker: string;
  fiscal_year: number;
  fiscal_period: FiscalPeriod;
  report_type: ReportType;
  announced_at: Timestamp;
  source_url?: string;
  data: Record<string, any>;
}

// Earnings Types
export interface Earnings extends BaseEntity {
  ticker: string;
  fiscal_year: number;
  fiscal_quarter: number;
  earnings_date: DateString;
  revenue?: number;
  net_income?: number;
  eps_actual?: number;
  eps_estimate?: number;
  eps_surprise?: number;
  revenue_estimate?: number;
  revenue_surprise?: number;
}

export interface EarningsCreate {
  ticker: string;
  fiscal_year: number;
  fiscal_quarter: number;
  earnings_date: DateString;
  revenue?: number;
  net_income?: number;
  eps_actual?: number;
  eps_estimate?: number;
  eps_surprise?: number;
  revenue_estimate?: number;
  revenue_surprise?: number;
}

// Balance Sheet Types
export interface BalanceSheet extends BaseEntity {
  ticker: string;
  fiscal_year: number;
  fiscal_period: FiscalPeriod;
  report_date: DateString;
  
  // Assets
  total_assets?: number;
  current_assets?: number;
  cash_and_equivalents?: number;
  accounts_receivable?: number;
  inventory?: number;
  property_plant_equipment?: number;
  
  // Liabilities
  total_liabilities?: number;
  current_liabilities?: number;
  accounts_payable?: number;
  short_term_debt?: number;
  long_term_debt?: number;
  
  // Equity
  total_equity?: number;
  retained_earnings?: number;
}

export interface BalanceSheetCreate {
  ticker: string;
  fiscal_year: number;
  fiscal_period: FiscalPeriod;
  report_date: DateString;
  total_assets?: number;
  current_assets?: number;
  cash_and_equivalents?: number;
  accounts_receivable?: number;
  inventory?: number;
  property_plant_equipment?: number;
  total_liabilities?: number;
  current_liabilities?: number;
  accounts_payable?: number;
  short_term_debt?: number;
  long_term_debt?: number;
  total_equity?: number;
  retained_earnings?: number;
}

// Income Statement Types
export interface IncomeStatement extends BaseEntity {
  ticker: string;
  fiscal_year: number;
  fiscal_period: FiscalPeriod;
  report_date: DateString;
  
  // Revenue
  total_revenue?: number;
  cost_of_revenue?: number;
  gross_profit?: number;
  
  // Operating
  operating_expenses?: number;
  operating_income?: number;
  
  // Other
  interest_expense?: number;
  interest_income?: number;
  other_income?: number;
  
  // Income
  income_before_tax?: number;
  income_tax_expense?: number;
  net_income?: number;
  
  // Per Share
  basic_eps?: number;
  diluted_eps?: number;
  weighted_average_shares?: number;
}

export interface IncomeStatementCreate {
  ticker: string;
  fiscal_year: number;
  fiscal_period: FiscalPeriod;
  report_date: DateString;
  total_revenue?: number;
  cost_of_revenue?: number;
  gross_profit?: number;
  operating_expenses?: number;
  operating_income?: number;
  interest_expense?: number;
  interest_income?: number;
  other_income?: number;
  income_before_tax?: number;
  income_tax_expense?: number;
  net_income?: number;
  basic_eps?: number;
  diluted_eps?: number;
  weighted_average_shares?: number;
}

// Cash Flow Types
export interface CashFlow extends BaseEntity {
  ticker: string;
  fiscal_year: number;
  fiscal_period: FiscalPeriod;
  report_date: DateString;
  
  // Operating Activities
  net_income?: number;
  depreciation_amortization?: number;
  changes_working_capital?: number;
  operating_cash_flow?: number;
  
  // Investing Activities
  capital_expenditures?: number;
  investments?: number;
  investing_cash_flow?: number;
  
  // Financing Activities
  debt_issuance?: number;
  debt_repayment?: number;
  dividends_paid?: number;
  share_repurchases?: number;
  financing_cash_flow?: number;
  
  // Net Change
  net_change_cash?: number;
  free_cash_flow?: number;
}

export interface CashFlowCreate {
  ticker: string;
  fiscal_year: number;
  fiscal_period: FiscalPeriod;
  report_date: DateString;
  net_income?: number;
  depreciation_amortization?: number;
  changes_working_capital?: number;
  operating_cash_flow?: number;
  capital_expenditures?: number;
  investments?: number;
  investing_cash_flow?: number;
  debt_issuance?: number;
  debt_repayment?: number;
  dividends_paid?: number;
  share_repurchases?: number;
  financing_cash_flow?: number;
  net_change_cash?: number;
  free_cash_flow?: number;
}

// Financial Ratios Types
export interface FinancialRatios extends BaseEntity {
  ticker: string;
  fiscal_year: number;
  fiscal_period: FiscalPeriod;
  calculation_date: DateString;
  
  // Profitability Ratios
  gross_margin?: number;
  operating_margin?: number;
  net_margin?: number;
  return_on_assets?: number;
  return_on_equity?: number;
  
  // Liquidity Ratios
  current_ratio?: number;
  quick_ratio?: number;
  cash_ratio?: number;
  
  // Leverage Ratios
  debt_to_equity?: number;
  debt_to_assets?: number;
  interest_coverage?: number;
  
  // Efficiency Ratios
  asset_turnover?: number;
  inventory_turnover?: number;
  receivables_turnover?: number;
}

export interface FinancialRatiosCreate {
  ticker: string;
  fiscal_year: number;
  fiscal_period: FiscalPeriod;
  calculation_date: DateString;
  gross_margin?: number;
  operating_margin?: number;
  net_margin?: number;
  return_on_assets?: number;
  return_on_equity?: number;
  current_ratio?: number;
  quick_ratio?: number;
  cash_ratio?: number;
  debt_to_equity?: number;
  debt_to_assets?: number;
  interest_coverage?: number;
  asset_turnover?: number;
  inventory_turnover?: number;
  receivables_turnover?: number;
}

// Financial Summary Types
export interface FinancialSummary {
  ticker: string;
  company_name: string;
  latest_fiscal_year: number;
  latest_fiscal_period: string;
  
  // Latest Financial Data
  latest_revenue?: number;
  latest_net_income?: number;
  latest_eps?: number;
  latest_total_assets?: number;
  latest_total_equity?: number;
  
  // Key Ratios
  pe_ratio?: number;
  pb_ratio?: number;
  roe?: number;
  roa?: number;
  debt_to_equity?: number;
  
  // Growth Rates (YoY)
  revenue_growth?: number;
  earnings_growth?: number;
  
  last_updated: Timestamp;
}

// Earnings Calendar Types
export interface EarningsCalendarEntry {
  ticker: string;
  company_name: string;
  earnings_date: DateString;
  fiscal_year: number;
  fiscal_quarter: number;
  eps_estimate?: number;
  revenue_estimate?: number;
  confirmed: boolean;
  market_time: 'BMO' | 'AMC' | 'DMT'; // Before Market Open, After Market Close, During Market Time
}

export interface EarningsCalendarResponse {
  date_range: string;
  entries: EarningsCalendarEntry[];
  total_count: number;
}

// Financial Analysis Types
export interface FinancialAnalysis {
  ticker: string;
  analysis_date: Timestamp;
  
  // Trend Analysis
  revenue_trend: {
    direction: 'up' | 'down' | 'stable';
    growth_rate: number;
    consistency_score: number;
  };
  
  profitability_trend: {
    direction: 'up' | 'down' | 'stable';
    margin_improvement: number;
    efficiency_score: number;
  };
  
  // Financial Health
  liquidity_score: number; // 0-100
  solvency_score: number; // 0-100
  efficiency_score: number; // 0-100
  overall_health_score: number; // 0-100
  
  // Peer Comparison
  peer_comparison: {
    revenue_percentile: number;
    profitability_percentile: number;
    efficiency_percentile: number;
    valuation_percentile: number;
  };
  
  // Key Insights
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  risks: string[];
}

// Financial Chart Data Types
export interface FinancialChartData {
  ticker: string;
  chart_type: 'revenue' | 'earnings' | 'margins' | 'ratios' | 'cash_flow';
  time_series: {
    period: string;
    value: number;
    label: string;
  }[];
  comparison_data?: {
    ticker: string;
    company_name: string;
    time_series: {
      period: string;
      value: number;
    }[];
  }[];
}

// Financial Metrics Comparison Types
export interface FinancialComparison {
  tickers: string[];
  comparison_type: 'peer_analysis' | 'sector_analysis' | 'historical_analysis';
  metrics: {
    [ticker: string]: {
      revenue: number;
      net_income: number;
      eps: number;
      roe: number;
      roa: number;
      debt_to_equity: number;
      current_ratio: number;
      pe_ratio: number;
      pb_ratio: number;
    };
  };
  rankings: {
    metric: string;
    rankings: {
      ticker: string;
      value: number;
      rank: number;
    }[];
  }[];
}

// Financial State Types (for Redux/Context)
export interface FinancialState {
  // Current financial data
  currentFinancials: {
    [ticker: string]: {
      earnings: Earnings[];
      balanceSheet: BalanceSheet[];
      incomeStatement: IncomeStatement[];
      cashFlow: CashFlow[];
      ratios: FinancialRatios[];
      summary: FinancialSummary;
    };
  };
  
  // Earnings calendar
  earningsCalendar: EarningsCalendarEntry[];
  earningsCalendarDateRange: string;
  
  // Financial analysis
  financialAnalysis: {
    [ticker: string]: FinancialAnalysis;
  };
  
  // Chart data
  chartData: {
    [ticker: string]: {
      [chartType: string]: FinancialChartData;
    };
  };
  
  // Loading states
  isLoadingFinancials: boolean;
  isLoadingEarningsCalendar: boolean;
  isLoadingAnalysis: boolean;
  isLoadingChartData: boolean;
  
  // Error states
  financialsError?: string;
  earningsCalendarError?: string;
  analysisError?: string;
  chartDataError?: string;
  
  // Last updated timestamps
  lastUpdated: {
    financials?: Timestamp;
    earningsCalendar?: Timestamp;
    analysis?: Timestamp;
    chartData?: Timestamp;
  };
}

// Financial Export Types
export interface FinancialDataExport {
  ticker: string;
  export_type: 'earnings' | 'balance_sheet' | 'income_statement' | 'cash_flow' | 'all';
  format: 'csv' | 'excel' | 'json';
  date_range: {
    start_year: number;
    end_year: number;
  };
  include_estimates: boolean;
  include_ratios: boolean;
}

// Paginated Financial Responses
export type PaginatedFinancialReportsResponse = PaginatedResponse<FinancialReport>;
export type PaginatedEarningsResponse = PaginatedResponse<Earnings>;
export type PaginatedBalanceSheetsResponse = PaginatedResponse<BalanceSheet>;
export type PaginatedIncomeStatementsResponse = PaginatedResponse<IncomeStatement>;
export type PaginatedCashFlowsResponse = PaginatedResponse<CashFlow>;