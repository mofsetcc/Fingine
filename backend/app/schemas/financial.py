"""Financial data Pydantic schemas."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema, PaginatedResponse


# Financial Report Schemas
class FinancialReportBase(BaseModel):
    """Base financial report schema."""
    
    ticker: str = Field(..., max_length=10, description="Stock ticker")
    fiscal_year: int = Field(..., ge=1900, le=2100, description="Fiscal year")
    fiscal_period: str = Field(..., description="Fiscal period")
    report_type: str = Field(..., description="Report type")
    announced_at: datetime = Field(..., description="Announcement date")
    source_url: Optional[str] = Field(None, max_length=500, description="Source URL")
    
    @validator('fiscal_period')
    def validate_fiscal_period(cls, v):
        """Validate fiscal period."""
        valid_periods = ['Q1', 'Q2', 'Q3', 'Q4', 'FY', 'H1', 'H2']
        if v not in valid_periods:
            raise ValueError(f'Fiscal period must be one of: {", ".join(valid_periods)}')
        return v
    
    @validator('report_type')
    def validate_report_type(cls, v):
        """Validate report type."""
        valid_types = ['earnings', 'balance_sheet', 'cash_flow', 'income_statement']
        if v not in valid_types:
            raise ValueError(f'Report type must be one of: {", ".join(valid_types)}')
        return v


class FinancialReportCreate(FinancialReportBase):
    """Financial report creation schema."""
    
    data: Dict[str, Any] = Field(..., description="Financial data")


class FinancialReport(BaseSchema, FinancialReportBase, TimestampSchema):
    """Financial report response schema."""
    
    data: Dict[str, Any] = Field(..., description="Financial data")


# Earnings Schemas
class EarningsBase(BaseModel):
    """Base earnings schema."""
    
    ticker: str = Field(..., max_length=10, description="Stock ticker")
    fiscal_year: int = Field(..., ge=1900, le=2100, description="Fiscal year")
    fiscal_quarter: int = Field(..., ge=1, le=4, description="Fiscal quarter")
    earnings_date: date = Field(..., description="Earnings announcement date")
    revenue: Optional[Decimal] = Field(None, description="Revenue")
    net_income: Optional[Decimal] = Field(None, description="Net income")
    eps_actual: Optional[Decimal] = Field(None, description="Actual EPS")
    eps_estimate: Optional[Decimal] = Field(None, description="EPS estimate")
    eps_surprise: Optional[Decimal] = Field(None, description="EPS surprise")
    revenue_estimate: Optional[Decimal] = Field(None, description="Revenue estimate")
    revenue_surprise: Optional[Decimal] = Field(None, description="Revenue surprise")


class EarningsCreate(EarningsBase):
    """Earnings creation schema."""
    pass


class Earnings(BaseSchema, EarningsBase, TimestampSchema):
    """Earnings response schema."""
    pass


# Balance Sheet Schemas
class BalanceSheetBase(BaseModel):
    """Base balance sheet schema."""
    
    ticker: str = Field(..., max_length=10, description="Stock ticker")
    fiscal_year: int = Field(..., ge=1900, le=2100, description="Fiscal year")
    fiscal_period: str = Field(..., description="Fiscal period")
    report_date: date = Field(..., description="Report date")
    
    # Assets
    total_assets: Optional[Decimal] = Field(None, description="Total assets")
    current_assets: Optional[Decimal] = Field(None, description="Current assets")
    cash_and_equivalents: Optional[Decimal] = Field(None, description="Cash and cash equivalents")
    accounts_receivable: Optional[Decimal] = Field(None, description="Accounts receivable")
    inventory: Optional[Decimal] = Field(None, description="Inventory")
    property_plant_equipment: Optional[Decimal] = Field(None, description="Property, plant & equipment")
    
    # Liabilities
    total_liabilities: Optional[Decimal] = Field(None, description="Total liabilities")
    current_liabilities: Optional[Decimal] = Field(None, description="Current liabilities")
    accounts_payable: Optional[Decimal] = Field(None, description="Accounts payable")
    short_term_debt: Optional[Decimal] = Field(None, description="Short-term debt")
    long_term_debt: Optional[Decimal] = Field(None, description="Long-term debt")
    
    # Equity
    total_equity: Optional[Decimal] = Field(None, description="Total shareholders' equity")
    retained_earnings: Optional[Decimal] = Field(None, description="Retained earnings")
    
    @validator('fiscal_period')
    def validate_fiscal_period(cls, v):
        """Validate fiscal period."""
        valid_periods = ['Q1', 'Q2', 'Q3', 'Q4', 'FY']
        if v not in valid_periods:
            raise ValueError(f'Fiscal period must be one of: {", ".join(valid_periods)}')
        return v


class BalanceSheetCreate(BalanceSheetBase):
    """Balance sheet creation schema."""
    pass


class BalanceSheet(BaseSchema, BalanceSheetBase, TimestampSchema):
    """Balance sheet response schema."""
    pass


# Income Statement Schemas
class IncomeStatementBase(BaseModel):
    """Base income statement schema."""
    
    ticker: str = Field(..., max_length=10, description="Stock ticker")
    fiscal_year: int = Field(..., ge=1900, le=2100, description="Fiscal year")
    fiscal_period: str = Field(..., description="Fiscal period")
    report_date: date = Field(..., description="Report date")
    
    # Revenue
    total_revenue: Optional[Decimal] = Field(None, description="Total revenue")
    cost_of_revenue: Optional[Decimal] = Field(None, description="Cost of revenue")
    gross_profit: Optional[Decimal] = Field(None, description="Gross profit")
    
    # Operating
    operating_expenses: Optional[Decimal] = Field(None, description="Operating expenses")
    operating_income: Optional[Decimal] = Field(None, description="Operating income")
    
    # Other
    interest_expense: Optional[Decimal] = Field(None, description="Interest expense")
    interest_income: Optional[Decimal] = Field(None, description="Interest income")
    other_income: Optional[Decimal] = Field(None, description="Other income")
    
    # Income
    income_before_tax: Optional[Decimal] = Field(None, description="Income before tax")
    income_tax_expense: Optional[Decimal] = Field(None, description="Income tax expense")
    net_income: Optional[Decimal] = Field(None, description="Net income")
    
    # Per Share
    basic_eps: Optional[Decimal] = Field(None, description="Basic EPS")
    diluted_eps: Optional[Decimal] = Field(None, description="Diluted EPS")
    weighted_average_shares: Optional[int] = Field(None, description="Weighted average shares")
    
    @validator('fiscal_period')
    def validate_fiscal_period(cls, v):
        """Validate fiscal period."""
        valid_periods = ['Q1', 'Q2', 'Q3', 'Q4', 'FY']
        if v not in valid_periods:
            raise ValueError(f'Fiscal period must be one of: {", ".join(valid_periods)}')
        return v


class IncomeStatementCreate(IncomeStatementBase):
    """Income statement creation schema."""
    pass


class IncomeStatement(BaseSchema, IncomeStatementBase, TimestampSchema):
    """Income statement response schema."""
    pass


# Cash Flow Schemas
class CashFlowBase(BaseModel):
    """Base cash flow schema."""
    
    ticker: str = Field(..., max_length=10, description="Stock ticker")
    fiscal_year: int = Field(..., ge=1900, le=2100, description="Fiscal year")
    fiscal_period: str = Field(..., description="Fiscal period")
    report_date: date = Field(..., description="Report date")
    
    # Operating Activities
    net_income: Optional[Decimal] = Field(None, description="Net income")
    depreciation_amortization: Optional[Decimal] = Field(None, description="Depreciation & amortization")
    changes_working_capital: Optional[Decimal] = Field(None, description="Changes in working capital")
    operating_cash_flow: Optional[Decimal] = Field(None, description="Operating cash flow")
    
    # Investing Activities
    capital_expenditures: Optional[Decimal] = Field(None, description="Capital expenditures")
    investments: Optional[Decimal] = Field(None, description="Investments")
    investing_cash_flow: Optional[Decimal] = Field(None, description="Investing cash flow")
    
    # Financing Activities
    debt_issuance: Optional[Decimal] = Field(None, description="Debt issuance")
    debt_repayment: Optional[Decimal] = Field(None, description="Debt repayment")
    dividends_paid: Optional[Decimal] = Field(None, description="Dividends paid")
    share_repurchases: Optional[Decimal] = Field(None, description="Share repurchases")
    financing_cash_flow: Optional[Decimal] = Field(None, description="Financing cash flow")
    
    # Net Change
    net_change_cash: Optional[Decimal] = Field(None, description="Net change in cash")
    free_cash_flow: Optional[Decimal] = Field(None, description="Free cash flow")
    
    @validator('fiscal_period')
    def validate_fiscal_period(cls, v):
        """Validate fiscal period."""
        valid_periods = ['Q1', 'Q2', 'Q3', 'Q4', 'FY']
        if v not in valid_periods:
            raise ValueError(f'Fiscal period must be one of: {", ".join(valid_periods)}')
        return v


class CashFlowCreate(CashFlowBase):
    """Cash flow creation schema."""
    pass


class CashFlow(BaseSchema, CashFlowBase, TimestampSchema):
    """Cash flow response schema."""
    pass


# Financial Ratios Schemas
class FinancialRatiosBase(BaseModel):
    """Base financial ratios schema."""
    
    ticker: str = Field(..., max_length=10, description="Stock ticker")
    fiscal_year: int = Field(..., ge=1900, le=2100, description="Fiscal year")
    fiscal_period: str = Field(..., description="Fiscal period")
    calculation_date: date = Field(..., description="Calculation date")
    
    # Profitability Ratios
    gross_margin: Optional[float] = Field(None, description="Gross margin")
    operating_margin: Optional[float] = Field(None, description="Operating margin")
    net_margin: Optional[float] = Field(None, description="Net margin")
    return_on_assets: Optional[float] = Field(None, description="Return on assets")
    return_on_equity: Optional[float] = Field(None, description="Return on equity")
    
    # Liquidity Ratios
    current_ratio: Optional[float] = Field(None, description="Current ratio")
    quick_ratio: Optional[float] = Field(None, description="Quick ratio")
    cash_ratio: Optional[float] = Field(None, description="Cash ratio")
    
    # Leverage Ratios
    debt_to_equity: Optional[float] = Field(None, description="Debt-to-equity ratio")
    debt_to_assets: Optional[float] = Field(None, description="Debt-to-assets ratio")
    interest_coverage: Optional[float] = Field(None, description="Interest coverage ratio")
    
    # Efficiency Ratios
    asset_turnover: Optional[float] = Field(None, description="Asset turnover")
    inventory_turnover: Optional[float] = Field(None, description="Inventory turnover")
    receivables_turnover: Optional[float] = Field(None, description="Receivables turnover")
    
    @validator('fiscal_period')
    def validate_fiscal_period(cls, v):
        """Validate fiscal period."""
        valid_periods = ['Q1', 'Q2', 'Q3', 'Q4', 'FY']
        if v not in valid_periods:
            raise ValueError(f'Fiscal period must be one of: {", ".join(valid_periods)}')
        return v


class FinancialRatiosCreate(FinancialRatiosBase):
    """Financial ratios creation schema."""
    pass


class FinancialRatios(BaseSchema, FinancialRatiosBase, TimestampSchema):
    """Financial ratios response schema."""
    pass


# Financial Summary Schemas
class FinancialSummary(BaseModel):
    """Financial summary schema."""
    
    ticker: str = Field(..., description="Stock ticker")
    company_name: str = Field(..., description="Company name")
    latest_fiscal_year: int = Field(..., description="Latest fiscal year")
    latest_fiscal_period: str = Field(..., description="Latest fiscal period")
    
    # Latest Financial Data
    latest_revenue: Optional[Decimal] = Field(None, description="Latest revenue")
    latest_net_income: Optional[Decimal] = Field(None, description="Latest net income")
    latest_eps: Optional[Decimal] = Field(None, description="Latest EPS")
    latest_total_assets: Optional[Decimal] = Field(None, description="Latest total assets")
    latest_total_equity: Optional[Decimal] = Field(None, description="Latest total equity")
    
    # Key Ratios
    pe_ratio: Optional[float] = Field(None, description="P/E ratio")
    pb_ratio: Optional[float] = Field(None, description="P/B ratio")
    roe: Optional[float] = Field(None, description="Return on equity")
    roa: Optional[float] = Field(None, description="Return on assets")
    debt_to_equity: Optional[float] = Field(None, description="Debt-to-equity ratio")
    
    # Growth Rates (YoY)
    revenue_growth: Optional[float] = Field(None, description="Revenue growth rate")
    earnings_growth: Optional[float] = Field(None, description="Earnings growth rate")
    
    last_updated: datetime = Field(..., description="Last update timestamp")


# Earnings Calendar Schemas
class EarningsCalendarEntry(BaseModel):
    """Earnings calendar entry schema."""
    
    ticker: str = Field(..., description="Stock ticker")
    company_name: str = Field(..., description="Company name")
    earnings_date: date = Field(..., description="Earnings announcement date")
    fiscal_year: int = Field(..., description="Fiscal year")
    fiscal_quarter: int = Field(..., description="Fiscal quarter")
    eps_estimate: Optional[Decimal] = Field(None, description="EPS estimate")
    revenue_estimate: Optional[Decimal] = Field(None, description="Revenue estimate")
    confirmed: bool = Field(False, description="Date confirmed by company")
    market_time: str = Field("AMC", description="Market timing (BMO, AMC, DMT)")
    
    @validator('market_time')
    def validate_market_time(cls, v):
        """Validate market timing."""
        if v not in ['BMO', 'AMC', 'DMT']:  # Before Market Open, After Market Close, During Market Time
            raise ValueError('Market time must be BMO, AMC, or DMT')
        return v


class EarningsCalendarResponse(BaseModel):
    """Earnings calendar response schema."""
    
    date_range: str = Field(..., description="Date range for calendar")
    entries: List[EarningsCalendarEntry] = Field(..., description="Calendar entries")
    total_count: int = Field(..., description="Total number of entries")


# Paginated Financial Responses
class PaginatedFinancialReportsResponse(PaginatedResponse):
    """Paginated financial reports response."""
    
    items: List[FinancialReport]


class PaginatedEarningsResponse(PaginatedResponse):
    """Paginated earnings response."""
    
    items: List[Earnings]


class PaginatedBalanceSheetsResponse(PaginatedResponse):
    """Paginated balance sheets response."""
    
    items: List[BalanceSheet]


class PaginatedIncomeStatementsResponse(PaginatedResponse):
    """Paginated income statements response."""
    
    items: List[IncomeStatement]


class PaginatedCashFlowsResponse(PaginatedResponse):
    """Paginated cash flows response."""
    
    items: List[CashFlow]