/**
 * Financial Data Table Component
 * Displays comprehensive financial metrics and statements for a stock
 */

import React, { useEffect, useState } from 'react';
import { BalanceSheet, CashFlow, FinancialSummary, IncomeStatement } from '../types/financial';
import LoadingSpinner from './LoadingSpinner';

interface FinancialDataTableProps {
  ticker: string;
  showDetails: boolean;
}

interface FinancialData {
  summary: FinancialSummary | null;
  incomeStatement: IncomeStatement[];
  balanceSheet: BalanceSheet[];
  cashFlow: CashFlow[];
}

const FinancialDataTable: React.FC<FinancialDataTableProps> = ({
  ticker,
  showDetails
}) => {
  const [financialData, setFinancialData] = useState<FinancialData>({
    summary: null,
    incomeStatement: [],
    balanceSheet: [],
    cashFlow: []
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'summary' | 'income' | 'balance' | 'cashflow'>('summary');

  useEffect(() => {
    fetchFinancialData();
  }, [ticker]);

  const fetchFinancialData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch financial summary
      const summaryResponse = await fetch(`/api/v1/financial/${ticker}/summary`);
      const summary = summaryResponse.ok ? await summaryResponse.json() : null;

      // Fetch detailed statements if needed
      let incomeStatement: IncomeStatement[] = [];
      let balanceSheet: BalanceSheet[] = [];
      let cashFlow: CashFlow[] = [];

      if (showDetails) {
        const [incomeRes, balanceRes, cashFlowRes] = await Promise.all([
          fetch(`/api/v1/financial/${ticker}/income-statement?limit=4`),
          fetch(`/api/v1/financial/${ticker}/balance-sheet?limit=4`),
          fetch(`/api/v1/financial/${ticker}/cash-flow?limit=4`)
        ]);

        if (incomeRes.ok) incomeStatement = await incomeRes.json();
        if (balanceRes.ok) balanceSheet = await balanceRes.json();
        if (cashFlowRes.ok) cashFlow = await cashFlowRes.json();
      }

      setFinancialData({
        summary,
        incomeStatement,
        balanceSheet,
        cashFlow
      });
    } catch (err) {
      setError('Failed to fetch financial data');
      console.error('Financial data fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (value: number | null | undefined, unit: 'JPY' | 'millions' = 'JPY') => {
    if (value === null || value === undefined) return 'N/A';
    
    if (unit === 'millions') {
      return `¥${(value / 1000000).toFixed(1)}M`;
    }
    
    return `¥${value.toLocaleString()}`;
  };

  const formatPercentage = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A';
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatRatio = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A';
    return value.toFixed(2);
  };

  const getChangeColor = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'text-gray-600';
    return value >= 0 ? 'text-success-600' : 'text-danger-600';
  };

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center">
        <LoadingSpinner size="medium" />
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
        <h3 className="text-lg font-medium text-gray-900 mb-2">Financial Data Unavailable</h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button onClick={fetchFinancialData} className="btn-primary">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Financial Summary */}
      {financialData.summary && (
        <div className="mb-8">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">Key Financial Metrics</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">Revenue (Latest)</div>
              <div className="text-xl font-semibold text-gray-900">
                {formatCurrency(financialData.summary.latest_revenue, 'millions')}
              </div>
              {financialData.summary.revenue_growth !== null && (
                <div className={`text-sm ${getChangeColor(financialData.summary.revenue_growth)}`}>
                  {financialData.summary.revenue_growth >= 0 ? '+' : ''}{formatPercentage(financialData.summary.revenue_growth)} YoY
                </div>
              )}
            </div>

            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">Net Income</div>
              <div className="text-xl font-semibold text-gray-900">
                {formatCurrency(financialData.summary.latest_net_income, 'millions')}
              </div>
              {financialData.summary.earnings_growth !== null && (
                <div className={`text-sm ${getChangeColor(financialData.summary.earnings_growth)}`}>
                  {financialData.summary.earnings_growth >= 0 ? '+' : ''}{formatPercentage(financialData.summary.earnings_growth)} YoY
                </div>
              )}
            </div>

            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">P/E Ratio</div>
              <div className="text-xl font-semibold text-gray-900">
                {formatRatio(financialData.summary.pe_ratio)}
              </div>
            </div>

            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">ROE</div>
              <div className="text-xl font-semibold text-gray-900">
                {formatPercentage(financialData.summary.roe)}
              </div>
            </div>

            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">P/B Ratio</div>
              <div className="text-xl font-semibold text-gray-900">
                {formatRatio(financialData.summary.pb_ratio)}
              </div>
            </div>

            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">ROA</div>
              <div className="text-xl font-semibold text-gray-900">
                {formatPercentage(financialData.summary.roa)}
              </div>
            </div>

            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">Debt/Equity</div>
              <div className="text-xl font-semibold text-gray-900">
                {formatRatio(financialData.summary.debt_to_equity)}
              </div>
            </div>

            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">EPS (Latest)</div>
              <div className="text-xl font-semibold text-gray-900">
                ¥{financialData.summary.latest_eps?.toFixed(2) || 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Detailed Financial Statements */}
      {showDetails && (
        <div>
          <div className="flex space-x-1 mb-6 border-b border-gray-200">
            {[
              { key: 'summary', label: 'Summary' },
              { key: 'income', label: 'Income Statement' },
              { key: 'balance', label: 'Balance Sheet' },
              { key: 'cashflow', label: 'Cash Flow' }
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Income Statement Tab */}
          {activeTab === 'income' && (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Metric
                    </th>
                    {financialData.incomeStatement.slice(0, 4).map((statement, index) => (
                      <th key={index} className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        {statement.fiscal_year} {statement.fiscal_period}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Total Revenue</td>
                    {financialData.incomeStatement.slice(0, 4).map((statement, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(statement.total_revenue, 'millions')}
                      </td>
                    ))}
                  </tr>
                  <tr className="bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Gross Profit</td>
                    {financialData.incomeStatement.slice(0, 4).map((statement, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(statement.gross_profit, 'millions')}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Operating Income</td>
                    {financialData.incomeStatement.slice(0, 4).map((statement, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(statement.operating_income, 'millions')}
                      </td>
                    ))}
                  </tr>
                  <tr className="bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Net Income</td>
                    {financialData.incomeStatement.slice(0, 4).map((statement, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(statement.net_income, 'millions')}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">EPS (Diluted)</td>
                    {financialData.incomeStatement.slice(0, 4).map((statement, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        ¥{statement.diluted_eps?.toFixed(2) || 'N/A'}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* Balance Sheet Tab */}
          {activeTab === 'balance' && (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Metric
                    </th>
                    {financialData.balanceSheet.slice(0, 4).map((sheet, index) => (
                      <th key={index} className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        {sheet.fiscal_year} {sheet.fiscal_period}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Total Assets</td>
                    {financialData.balanceSheet.slice(0, 4).map((sheet, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(sheet.total_assets, 'millions')}
                      </td>
                    ))}
                  </tr>
                  <tr className="bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Current Assets</td>
                    {financialData.balanceSheet.slice(0, 4).map((sheet, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(sheet.current_assets, 'millions')}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Total Liabilities</td>
                    {financialData.balanceSheet.slice(0, 4).map((sheet, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(sheet.total_liabilities, 'millions')}
                      </td>
                    ))}
                  </tr>
                  <tr className="bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Total Equity</td>
                    {financialData.balanceSheet.slice(0, 4).map((sheet, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(sheet.total_equity, 'millions')}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Cash & Equivalents</td>
                    {financialData.balanceSheet.slice(0, 4).map((sheet, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(sheet.cash_and_equivalents, 'millions')}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* Cash Flow Tab */}
          {activeTab === 'cashflow' && (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Metric
                    </th>
                    {financialData.cashFlow.slice(0, 4).map((cf, index) => (
                      <th key={index} className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        {cf.fiscal_year} {cf.fiscal_period}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Operating Cash Flow</td>
                    {financialData.cashFlow.slice(0, 4).map((cf, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(cf.operating_cash_flow, 'millions')}
                      </td>
                    ))}
                  </tr>
                  <tr className="bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Investing Cash Flow</td>
                    {financialData.cashFlow.slice(0, 4).map((cf, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(cf.investing_cash_flow, 'millions')}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Financing Cash Flow</td>
                    {financialData.cashFlow.slice(0, 4).map((cf, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(cf.financing_cash_flow, 'millions')}
                      </td>
                    ))}
                  </tr>
                  <tr className="bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Free Cash Flow</td>
                    {financialData.cashFlow.slice(0, 4).map((cf, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(cf.free_cash_flow, 'millions')}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Net Change in Cash</td>
                    {financialData.cashFlow.slice(0, 4).map((cf, index) => (
                      <td key={index} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {formatCurrency(cf.net_change_cash, 'millions')}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Data Source Attribution */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 text-center">
          Financial data sourced from EDINET (Financial Instruments and Exchange Act) and company IR reports.
          Data may be delayed. Last updated: {financialData.summary?.last_updated ? new Date(financialData.summary.last_updated).toLocaleDateString() : 'N/A'}
        </p>
      </div>
    </div>
  );
};

export default FinancialDataTable;