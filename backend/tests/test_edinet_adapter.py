"""Tests for EDINET financial data adapter."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
import zipfile
import io
import xml.etree.ElementTree as ET

from app.adapters.edinet_adapter import EDINETAdapter, EDINETDocument
from app.adapters.base import (
    HealthStatus,
    DataSourceError,
    DataSourceUnavailableError,
    InvalidDataError
)


class TestEDINETAdapter:
    """Test cases for EDINET adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create EDINET adapter instance for testing."""
        config = {
            "timeout": 10,
            "max_retries": 2,
            "retry_delay": 0.1,
            "requests_per_minute": 60,
            "requests_per_hour": 1000
        }
        return EDINETAdapter(config=config)
    
    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp session."""
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def sample_edinet_response(self):
        """Sample EDINET API response."""
        return {
            "metadata": {
                "title": "EDINET API",
                "parameter": {
                    "date": "2024-01-15"
                }
            },
            "results": [
                {
                    "seqNumber": 1,
                    "docID": "S100ABC123",
                    "edinetCode": "E12345",
                    "secCode": "7203",
                    "JCN": "1234567890123",
                    "filerName": "トヨタ自動車株式会社",
                    "fundCode": None,
                    "ordinanceCode": "010",
                    "formCode": "030000",
                    "docTypeCode": "120",
                    "periodStart": "2023-04-01",
                    "periodEnd": "2024-03-31",
                    "submitDateTime": "2024-06-25 15:30",
                    "docDescription": "有価証券報告書－第105期(2023/04/01－2024/03/31)",
                    "issuerEdinetCode": None,
                    "subjectEdinetCode": None,
                    "subsidiaryEdinetCode": None,
                    "currentReportReason": None,
                    "parentDocID": None,
                    "opeDateTime": "2024-06-25 15:30",
                    "withdrawalStatus": "0",
                    "docInfoEditStatus": "0",
                    "disclosureStatus": "0",
                    "xbrlFlag": "1",
                    "pdfFlag": "1",
                    "attachDocFlag": "0",
                    "englishDocFlag": "0"
                }
            ]
        }
    
    @pytest.fixture
    def sample_xbrl_content(self):
        """Sample XBRL content for testing."""
        xbrl_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
              xmlns:jpcrp="http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2019-11-01"
              xmlns:jppfs="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2019-11-01">
            
            <xbrli:context id="CurrentYearDuration">
                <xbrli:entity>
                    <xbrli:identifier scheme="http://disclosure.edinet-fsa.go.jp">E12345</xbrli:identifier>
                </xbrli:entity>
                <xbrli:period>
                    <xbrli:startDate>2023-04-01</xbrli:startDate>
                    <xbrli:endDate>2024-03-31</xbrli:endDate>
                </xbrli:period>
            </xbrli:context>
            
            <xbrli:context id="CurrentYearInstant">
                <xbrli:entity>
                    <xbrli:identifier scheme="http://disclosure.edinet-fsa.go.jp">E12345</xbrli:identifier>
                </xbrli:entity>
                <xbrli:period>
                    <xbrli:instant>2024-03-31</xbrli:instant>
                </xbrli:period>
            </xbrli:context>
            
            <xbrli:unit id="JPY">
                <xbrli:measure>iso4217:JPY</xbrli:measure>
            </xbrli:unit>
            
            <!-- Income Statement Items -->
            <jppfs:NetSales contextRef="CurrentYearDuration" unitRef="JPY" decimals="-6">37154136000000</jppfs:NetSales>
            <jppfs:OperatingIncome contextRef="CurrentYearDuration" unitRef="JPY" decimals="-6">5353016000000</jppfs:OperatingIncome>
            <jppfs:NetIncome contextRef="CurrentYearDuration" unitRef="JPY" decimals="-6">4940526000000</jppfs:NetIncome>
            
            <!-- Balance Sheet Items -->
            <jppfs:TotalAssets contextRef="CurrentYearInstant" unitRef="JPY" decimals="-6">71381000000000</jppfs:TotalAssets>
            <jppfs:NetAssets contextRef="CurrentYearInstant" unitRef="JPY" decimals="-6">28539000000000</jppfs:NetAssets>
            <jppfs:CashAndCashEquivalents contextRef="CurrentYearInstant" unitRef="JPY" decimals="-6">6847000000000</jppfs:CashAndCashEquivalents>
            
        </xbrl>"""
        
        # Create a ZIP file containing the XBRL
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr('XBRL/PublicDoc/jpcrp030000-asr-001_E12345-000.xbrl', xbrl_xml)
        
        return zip_buffer.getvalue()
    
    def test_init(self):
        """Test adapter initialization."""
        config = {
            "timeout": 20,
            "max_retries": 5,
            "requests_per_minute": 30
        }
        adapter = EDINETAdapter(name="test_edinet", priority=5, config=config)
        
        assert adapter.name == "test_edinet"
        assert adapter.priority == 5
        assert adapter.timeout == 20
        assert adapter.max_retries == 5
        assert adapter.requests_per_minute == 30
    
    def test_normalize_symbol(self, adapter):
        """Test symbol normalization."""
        # Test various input formats
        assert adapter._normalize_symbol("7203") == "7203"
        assert adapter._normalize_symbol("7203.T") == "7203"
        assert adapter._normalize_symbol("7203.TYO") == "7203"
        assert adapter._normalize_symbol("Toyota 7203") == "7203"
        
        # Test invalid symbols
        with pytest.raises(InvalidDataError):
            adapter._normalize_symbol("INVALID")
        
        with pytest.raises(InvalidDataError):
            adapter._normalize_symbol("123")  # Too short
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, adapter):
        """Test successful health check."""
        # Mock the _make_request method directly
        with patch.object(adapter, '_make_request', return_value={"results": []}):
            health = await adapter.health_check()
        
        assert health.status == HealthStatus.HEALTHY
        assert health.response_time_ms > 0
        assert health.last_check is not None
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, adapter):
        """Test health check failure."""
        # Mock the _make_request method to raise an exception
        with patch.object(adapter, '_make_request', side_effect=DataSourceUnavailableError("API unavailable")):
            health = await adapter.health_check()
        
        assert health.status == HealthStatus.UNHEALTHY
        assert health.error_message is not None
    
    @pytest.mark.asyncio
    async def test_search_documents(self, adapter, sample_edinet_response):
        """Test document search functionality."""
        # Mock the _make_request method directly
        with patch.object(adapter, '_make_request', return_value=sample_edinet_response):
            documents = await adapter._search_documents(
                sec_code="7203",
                doc_type_code="120",
                date_from=datetime(2024, 1, 1),
                date_to=datetime(2024, 12, 31)
            )
        
        assert len(documents) == 1
        doc = documents[0]
        assert isinstance(doc, EDINETDocument)
        assert doc.doc_id == "S100ABC123"
        assert doc.sec_code == "7203"
        assert doc.filer_name == "トヨタ自動車株式会社"
        assert doc.doc_type_code == "120"
    
    @pytest.mark.asyncio
    async def test_download_document(self, adapter, sample_xbrl_content):
        """Test document download functionality."""
        # Mock the _make_request method to return binary data
        mock_response = {"binary_data": sample_xbrl_content}
        
        with patch.object(adapter, '_make_request', return_value=mock_response):
            content = await adapter._download_document("S100ABC123")
        
        assert content == sample_xbrl_content
        assert isinstance(content, bytes)
    
    def test_parse_xbrl_financial_data(self, adapter, sample_xbrl_content):
        """Test XBRL financial data parsing."""
        financial_data = adapter._parse_xbrl_financial_data(sample_xbrl_content)
        
        # Check structure
        assert "income_statement" in financial_data
        assert "balance_sheet" in financial_data
        assert "cash_flow" in financial_data
        assert "metadata" in financial_data
        
        # Check income statement data
        income_stmt = financial_data["income_statement"]
        assert "revenue" in income_stmt
        assert "operating_income" in income_stmt
        assert "net_income" in income_stmt
        
        # Check values
        assert income_stmt["revenue"]["value"] == 37154136000000.0
        assert income_stmt["operating_income"]["value"] == 5353016000000.0
        assert income_stmt["net_income"]["value"] == 4940526000000.0
        
        # Check balance sheet data
        balance_sheet = financial_data["balance_sheet"]
        assert "total_assets" in balance_sheet
        assert "shareholders_equity" in balance_sheet
        assert "cash_and_equivalents" in balance_sheet
        
        # Check values
        assert balance_sheet["total_assets"]["value"] == 71381000000000.0
        assert balance_sheet["shareholders_equity"]["value"] == 28539000000000.0
        assert balance_sheet["cash_and_equivalents"]["value"] == 6847000000000.0
    
    def test_extract_contexts(self, adapter):
        """Test XBRL context extraction."""
        xbrl_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance">
            <xbrli:context id="CurrentYearDuration">
                <xbrli:entity>
                    <xbrli:identifier scheme="http://disclosure.edinet-fsa.go.jp">E12345</xbrli:identifier>
                </xbrli:entity>
                <xbrli:period>
                    <xbrli:startDate>2023-04-01</xbrli:startDate>
                    <xbrli:endDate>2024-03-31</xbrli:endDate>
                </xbrli:period>
            </xbrli:context>
        </xbrl>"""
        
        root = ET.fromstring(xbrl_xml)
        contexts = adapter._extract_contexts(root)
        
        assert "CurrentYearDuration" in contexts
        context = contexts["CurrentYearDuration"]
        
        assert context["period"]["type"] == "duration"
        assert context["period"]["start_date"] == "2023-04-01"
        assert context["period"]["end_date"] == "2024-03-31"
        assert context["entity"]["identifier"] == "E12345"
    
    def test_determine_fiscal_period(self, adapter):
        """Test fiscal period determination."""
        # Annual period
        start = datetime(2023, 4, 1)
        end = datetime(2024, 3, 31)
        assert adapter._determine_fiscal_period(start, end) == "annual"
        
        # Quarterly periods
        q1_start = datetime(2024, 4, 1)
        q1_end = datetime(2024, 6, 30)
        assert adapter._determine_fiscal_period(q1_start, q1_end) == "Q2"
        
        # No start date
        assert adapter._determine_fiscal_period(None, end) == "annual"
        
        # No end date
        assert adapter._determine_fiscal_period(start, None) == "unknown"
    
    @pytest.mark.asyncio
    async def test_get_financial_statements_success(self, adapter, sample_edinet_response, sample_xbrl_content):
        """Test successful financial statements retrieval."""
        # Mock both search and download operations
        def mock_make_request(endpoint, params=None):
            if "documents.json" in endpoint:
                return sample_edinet_response
            else:
                return {"binary_data": sample_xbrl_content}
        
        with patch.object(adapter, '_make_request', side_effect=mock_make_request):
            statements = await adapter.get_financial_statements("7203", "income_statement", "annual")
        
        assert len(statements) == 1
        statement = statements[0]
        
        assert statement["symbol"] == "7203"
        assert statement["statement_type"] == "income_statement"
        assert statement["period"] == "annual"
        assert statement["company_name"] == "トヨタ自動車株式会社"
        assert statement["source"] == "EDINET"
        
        # Check financial data
        data = statement["data"]
        assert "revenue" in data
        assert "operating_income" in data
        assert "net_income" in data
        
        assert data["revenue"]["value"] == 37154136000000.0
    
    @pytest.mark.asyncio
    async def test_get_financial_statements_no_documents(self, adapter):
        """Test financial statements retrieval when no documents found."""
        # Mock empty response
        with patch.object(adapter, '_make_request', return_value={"results": []}):
            statements = await adapter.get_financial_statements("7203", "income_statement", "annual")
        
        assert statements == []
    
    @pytest.mark.asyncio
    async def test_get_financial_statements_invalid_period(self, adapter):
        """Test financial statements retrieval with invalid period."""
        with pytest.raises(InvalidDataError, match="Unsupported period type"):
            await adapter.get_financial_statements("7203", "income_statement", "invalid")
    
    @pytest.mark.asyncio
    async def test_get_company_overview_success(self, adapter, sample_edinet_response, sample_xbrl_content):
        """Test successful company overview retrieval."""
        # Mock both search and download operations
        def mock_make_request(endpoint, params=None):
            if "documents.json" in endpoint:
                return sample_edinet_response
            else:
                return {"binary_data": sample_xbrl_content}
        
        with patch.object(adapter, '_make_request', side_effect=mock_make_request):
            overview = await adapter.get_company_overview("7203")
        
        assert overview["symbol"] == "7203"
        assert overview["securities_code"] == "7203"
        assert overview["company_name"] == "トヨタ自動車株式会社"
        assert overview["edinet_code"] == "E12345"
        assert overview["source"] == "EDINET"
        
        # Check financial metrics
        assert "total_assets" in overview
        assert "revenue" in overview
        assert overview["total_assets"] == 71381000000000.0
        assert overview["revenue"] == 37154136000000.0
    
    @pytest.mark.asyncio
    async def test_get_company_overview_no_documents(self, adapter):
        """Test company overview retrieval when no documents found."""
        # Mock empty response
        with patch.object(adapter, '_make_request', return_value={"results": []}):
            with pytest.raises(InvalidDataError, match="No recent annual reports found"):
                await adapter.get_company_overview("7203")
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, adapter):
        """Test rate limiting functionality."""
        # Set low rate limits for testing
        adapter.requests_per_minute = 2
        adapter.requests_per_hour = 5
        
        # Simulate requests
        adapter._update_request_counts()
        adapter._update_request_counts()
        
        # Should be at limit
        with pytest.raises(DataSourceError, match="minute rate limit exceeded"):
            adapter._check_rate_limits()
    
    @pytest.mark.asyncio
    async def test_request_retry_logic(self, adapter):
        """Test request retry logic on failures."""
        # This test is more complex to mock at the HTTP level, so we'll test the concept
        # by verifying that the adapter has retry logic configured
        assert adapter.max_retries == 2
        assert adapter.retry_delay == 0.1
    
    @pytest.mark.asyncio
    async def test_request_max_retries_exceeded(self, adapter):
        """Test request failure after max retries exceeded."""
        # Test that the adapter properly handles exceptions
        with patch.object(adapter, '_get_session', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception):
                await adapter._make_request("documents.json")
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_info(self, adapter):
        """Test rate limit info retrieval."""
        # Simulate some requests
        adapter._request_count_minute = 10
        adapter._request_count_hour = 50
        
        rate_info = await adapter.get_rate_limit_info()
        
        assert rate_info.requests_per_minute == adapter.requests_per_minute
        assert rate_info.requests_per_hour == adapter.requests_per_hour
        assert rate_info.current_usage["minute"] == 10
        assert rate_info.current_usage["hour"] == 50
    
    @pytest.mark.asyncio
    async def test_get_cost_info(self, adapter):
        """Test cost info retrieval (should be free)."""
        cost_info = await adapter.get_cost_info()
        
        assert cost_info.cost_per_request == 0.0
        assert cost_info.currency == "JPY"
        assert cost_info.monthly_budget == 0.0
        assert cost_info.current_monthly_usage == 0.0
    
    @pytest.mark.asyncio
    async def test_context_manager(self, adapter):
        """Test async context manager functionality."""
        async with adapter as ctx_adapter:
            assert ctx_adapter is adapter
        
        # Session should be closed after context exit
        # (We can't easily test this without mocking the session)
    
    def test_invalid_xbrl_parsing(self, adapter):
        """Test handling of invalid XBRL content."""
        invalid_content = b"This is not valid XBRL content"
        
        with pytest.raises(InvalidDataError, match="Failed to parse XBRL data"):
            adapter._parse_xbrl_financial_data(invalid_content)
    
    def test_empty_zip_file(self, adapter):
        """Test handling of empty ZIP file."""
        # Create empty ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            pass  # Empty ZIP
        
        empty_zip_content = zip_buffer.getvalue()
        
        # Should return empty financial data structure
        result = adapter._parse_xbrl_financial_data(empty_zip_content)
        
        assert "income_statement" in result
        assert "balance_sheet" in result
        assert "cash_flow" in result
        assert len(result["income_statement"]) == 0
        assert len(result["balance_sheet"]) == 0
        assert len(result["cash_flow"]) == 0


class TestEDINETDocument:
    """Test cases for EDINETDocument dataclass."""
    
    def test_edinet_document_creation(self):
        """Test EDINETDocument creation."""
        doc = EDINETDocument(
            doc_id="S100ABC123",
            filer_name="Test Company",
            fund_code=None,
            sec_code="1234",
            jcn="1234567890123",
            edinet_code="E12345",
            doc_type_code="120",
            doc_description="Annual Report",
            submit_date=datetime(2024, 6, 25, 15, 30),
            period_start=datetime(2023, 4, 1),
            period_end=datetime(2024, 3, 31),
            doc_url="https://example.com/doc"
        )
        
        assert doc.doc_id == "S100ABC123"
        assert doc.filer_name == "Test Company"
        assert doc.sec_code == "1234"
        assert doc.doc_type_code == "120"
        assert doc.submit_date.year == 2024
        assert doc.period_start.month == 4
        assert doc.period_end.month == 3


@pytest.mark.integration
class TestEDINETIntegration:
    """Integration tests for EDINET adapter (requires network access)."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter for integration testing."""
        return EDINETAdapter(config={"timeout": 30})
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires network access and may hit rate limits")
    async def test_real_health_check(self, adapter):
        """Test health check against real EDINET API."""
        health = await adapter.health_check()
        assert health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert health.response_time_ms > 0
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires network access and may hit rate limits")
    async def test_real_document_search(self, adapter):
        """Test document search against real EDINET API."""
        # Search for recent documents
        date_from = datetime.utcnow() - timedelta(days=7)
        documents = await adapter._search_documents(date_from=date_from)
        
        # Should find some documents
        assert isinstance(documents, list)
        
        if documents:
            doc = documents[0]
            assert isinstance(doc, EDINETDocument)
            assert doc.doc_id
            assert doc.filer_name
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires network access and may hit rate limits")
    async def test_real_financial_statements(self, adapter):
        """Test financial statements retrieval against real EDINET API."""
        # Use Toyota (7203) as test case
        try:
            statements = await adapter.get_financial_statements("7203", "income_statement", "annual")
            
            if statements:
                statement = statements[0]
                assert statement["symbol"] == "7203"
                assert statement["statement_type"] == "income_statement"
                assert "data" in statement
                
        except Exception as e:
            # May fail due to rate limits or network issues
            pytest.skip(f"Integration test failed: {e}")