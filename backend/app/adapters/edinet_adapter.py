"""EDINET financial data adapter for Japanese companies."""

import asyncio
import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode, urlparse

import aiohttp

from .base import (
    CostInfo,
    DataSourceError,
    DataSourceUnavailableError,
    FinancialDataAdapter,
    HealthCheck,
    HealthStatus,
    InvalidDataError,
    RateLimitInfo,
)

logger = logging.getLogger(__name__)


@dataclass
class EDINETDocument:
    """EDINET document metadata."""

    doc_id: str
    filer_name: str
    fund_code: Optional[str]
    sec_code: Optional[str]
    jcn: Optional[str]
    edinet_code: Optional[str]
    doc_type_code: str
    doc_description: str
    submit_date: datetime
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    doc_url: str


class EDINETAdapter(FinancialDataAdapter):
    """EDINET API adapter for Japanese financial data."""

    BASE_URL = "https://disclosure.edinet-fsa.go.jp/api/v1"
    DOCUMENT_URL = "https://disclosure.edinet-fsa.go.jp/api/v1/documents"

    # EDINET document type codes for financial statements
    FINANCIAL_STATEMENT_TYPES = {
        "120": "有価証券報告書",  # Annual Securities Report
        "130": "四半期報告書",  # Quarterly Report
        "140": "半期報告書",  # Semi-annual Report
        "350": "内部統制報告書",  # Internal Control Report
    }

    # XBRL namespace mappings
    XBRL_NAMESPACES = {
        "xbrli": "http://www.xbrl.org/2003/instance",
        "xbrl": "http://www.xbrl.org/2003/instance",
        "link": "http://www.xbrl.org/2003/linkbase",
        "xlink": "http://www.w3.org/1999/xlink",
        "jpcrp": "http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2019-11-01",
        "jppfs": "http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2019-11-01",
        "jpigp": "http://disclosure.edinet-fsa.go.jp/taxonomy/jpigp/2019-11-01",
    }

    def __init__(
        self,
        name: str = "edinet",
        priority: int = 10,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize EDINET adapter.

        Args:
            name: Adapter name
            priority: Adapter priority
            config: Configuration dictionary containing:
                - timeout: Request timeout in seconds (default: 30)
                - max_retries: Maximum retry attempts (default: 3)
                - retry_delay: Delay between retries in seconds (default: 2)
                - cache_ttl: Cache TTL for documents in seconds (default: 86400)
        """
        super().__init__(name, priority, config)

        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 2)
        self.cache_ttl = self.config.get("cache_ttl", 86400)  # 24 hours

        # EDINET is free but has rate limits
        self.requests_per_minute = self.config.get("requests_per_minute", 60)
        self.requests_per_hour = self.config.get("requests_per_hour", 1000)

        # Request tracking
        self._request_count_minute = 0
        self._request_count_hour = 0
        self._last_minute_reset = datetime.utcnow()
        self._last_hour_reset = datetime.utcnow()
        self._total_requests = 0

        # Session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None

        # Document cache
        self._document_cache: Dict[str, EDINETDocument] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                "User-Agent": "Project-Kessan/1.0 (Financial Analysis Platform)",
                "Accept": "application/json",
            }
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self._session

    async def _close_session(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _update_request_counts(self):
        """Update request counts for rate limiting."""
        now = datetime.utcnow()

        # Reset minute counter if needed
        if (now - self._last_minute_reset).total_seconds() >= 60:
            self._request_count_minute = 0
            self._last_minute_reset = now

        # Reset hour counter if needed
        if (now - self._last_hour_reset).total_seconds() >= 3600:
            self._request_count_hour = 0
            self._last_hour_reset = now

        # Increment counters
        self._request_count_minute += 1
        self._request_count_hour += 1
        self._total_requests += 1

    def _check_rate_limits(self):
        """Check if we're within rate limits."""
        if self._request_count_minute >= self.requests_per_minute:
            raise DataSourceError(
                f"EDINET minute rate limit exceeded ({self.requests_per_minute} requests/minute)"
            )

        if self._request_count_hour >= self.requests_per_hour:
            raise DataSourceError(
                f"EDINET hour rate limit exceeded ({self.requests_per_hour} requests/hour)"
            )

    async def _make_request(
        self, endpoint: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make API request to EDINET.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            API response data

        Raises:
            DataSourceUnavailableError: If API is unavailable
            InvalidDataError: If response data is invalid
        """
        # Check rate limits
        self._check_rate_limits()

        session = await self._get_session()
        url = f"{self.BASE_URL}/{endpoint}"

        if params:
            url += f"?{urlencode(params)}"

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Making EDINET API request: {endpoint}")

                async with session.get(url) as response:
                    # Update request counts
                    self._update_request_counts()

                    if response.status == 200:
                        # Check content type
                        content_type = response.headers.get("content-type", "")

                        if "application/json" in content_type:
                            data = await response.json()
                            return data
                        elif (
                            "application/zip" in content_type
                            or "application/octet-stream" in content_type
                        ):
                            # Binary data (XBRL documents)
                            data = await response.read()
                            return {"binary_data": data, "content_type": content_type}
                        else:
                            text_data = await response.text()
                            return {
                                "text_data": text_data,
                                "content_type": content_type,
                            }

                    elif response.status == 404:
                        raise InvalidDataError("EDINET document not found")

                    elif response.status == 429:
                        raise DataSourceError("EDINET rate limit exceeded")

                    elif response.status >= 500:
                        if attempt < self.max_retries:
                            logger.warning(
                                f"EDINET server error (attempt {attempt + 1}): {response.status}"
                            )
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                        else:
                            raise DataSourceUnavailableError(
                                f"EDINET server error: {response.status}"
                            )

                    else:
                        raise DataSourceError(f"EDINET API error: {response.status}")

            except aiohttp.ClientError as e:
                if attempt < self.max_retries:
                    logger.warning(
                        f"EDINET connection error (attempt {attempt + 1}): {e}"
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise DataSourceUnavailableError(f"EDINET connection error: {e}")

        raise DataSourceUnavailableError("EDINET API unavailable after retries")

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol for EDINET search.

        Args:
            symbol: Input symbol (e.g., "7203", "7203.T")

        Returns:
            Normalized symbol (securities code)
        """
        # Remove common suffixes
        if symbol.endswith(".T") or symbol.endswith(".TYO"):
            symbol = symbol.split(".")[0]

        # Ensure it's a 4-digit securities code
        if symbol.isdigit() and len(symbol) == 4:
            return symbol

        # Try to extract 4-digit code from longer strings
        match = re.search(r"\b(\d{4})\b", symbol)
        if match:
            return match.group(1)

        raise InvalidDataError(f"Invalid Japanese securities code: {symbol}")

    async def _search_documents(
        self,
        sec_code: Optional[str] = None,
        edinet_code: Optional[str] = None,
        doc_type_code: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[EDINETDocument]:
        """
        Search for documents in EDINET.

        Args:
            sec_code: Securities code (4-digit)
            edinet_code: EDINET code (5-digit)
            doc_type_code: Document type code
            date_from: Start date for search
            date_to: End date for search

        Returns:
            List of matching documents
        """
        params = {}

        if date_from:
            params["date"] = date_from.strftime("%Y-%m-%d")
        if date_to and date_from and date_to != date_from:
            # EDINET API supports date range queries
            params[
                "date"
            ] = f"{date_from.strftime('%Y-%m-%d')}-{date_to.strftime('%Y-%m-%d')}"

        if doc_type_code:
            params["type"] = doc_type_code

        try:
            data = await self._make_request("documents.json", params)

            if "results" not in data:
                return []

            documents = []
            for result in data["results"]:
                # Filter by securities code if provided
                if sec_code and result.get("secCode") != sec_code:
                    continue

                # Filter by EDINET code if provided
                if edinet_code and result.get("edinetCode") != edinet_code:
                    continue

                # Parse dates
                submit_date = datetime.strptime(
                    result["submitDateTime"], "%Y-%m-%d %H:%M"
                )
                period_start = None
                period_end = None

                if result.get("periodStart"):
                    period_start = datetime.strptime(result["periodStart"], "%Y-%m-%d")
                if result.get("periodEnd"):
                    period_end = datetime.strptime(result["periodEnd"], "%Y-%m-%d")

                doc = EDINETDocument(
                    doc_id=result["docID"],
                    filer_name=result.get("filerName", ""),
                    fund_code=result.get("fundCode"),
                    sec_code=result.get("secCode"),
                    jcn=result.get("JCN"),
                    edinet_code=result.get("edinetCode"),
                    doc_type_code=result["docTypeCode"],
                    doc_description=result.get("docDescription", ""),
                    submit_date=submit_date,
                    period_start=period_start,
                    period_end=period_end,
                    doc_url=f"{self.DOCUMENT_URL}/{result['docID']}",
                )

                documents.append(doc)

            # Sort by submit date (newest first)
            documents.sort(key=lambda x: x.submit_date, reverse=True)

            return documents

        except Exception as e:
            logger.error(f"Error searching EDINET documents: {e}")
            raise

    async def _download_document(self, doc_id: str) -> bytes:
        """
        Download XBRL document from EDINET.

        Args:
            doc_id: Document ID

        Returns:
            Document content as bytes
        """
        try:
            params = {"type": "1"}  # Type 1 = XBRL format
            data = await self._make_request(f"documents/{doc_id}", params)

            if "binary_data" in data:
                return data["binary_data"]
            else:
                raise InvalidDataError("Expected binary data for XBRL document")

        except Exception as e:
            logger.error(f"Error downloading EDINET document {doc_id}: {e}")
            raise

    def _parse_xbrl_financial_data(self, xbrl_content: bytes) -> Dict[str, Any]:
        """
        Parse XBRL/iXBRL financial data.

        Args:
            xbrl_content: XBRL document content

        Returns:
            Parsed financial data
        """
        try:
            # EDINET documents are typically ZIP files containing XBRL
            import io
            import zipfile

            financial_data = {
                "income_statement": {},
                "balance_sheet": {},
                "cash_flow": {},
                "metadata": {},
            }

            # Extract ZIP file
            with zipfile.ZipFile(io.BytesIO(xbrl_content)) as zip_file:
                # Look for XBRL instance documents
                xbrl_files = [f for f in zip_file.namelist() if f.endswith(".xbrl")]

                for xbrl_file in xbrl_files:
                    with zip_file.open(xbrl_file) as f:
                        xbrl_data = f.read()
                        parsed_data = self._parse_xbrl_instance(xbrl_data)

                        # Merge parsed data
                        for section, data in parsed_data.items():
                            if section in financial_data:
                                financial_data[section].update(data)

            return financial_data

        except Exception as e:
            logger.error(f"Error parsing XBRL content: {e}")
            raise InvalidDataError(f"Failed to parse XBRL data: {e}")

    def _parse_xbrl_instance(self, xbrl_data: bytes) -> Dict[str, Any]:
        """
        Parse XBRL instance document.

        Args:
            xbrl_data: XBRL instance document content

        Returns:
            Parsed financial data
        """
        try:
            # Parse XML
            root = ET.fromstring(xbrl_data)

            # Register namespaces
            for prefix, uri in self.XBRL_NAMESPACES.items():
                ET.register_namespace(prefix, uri)

            financial_data = {
                "income_statement": {},
                "balance_sheet": {},
                "cash_flow": {},
                "metadata": {},
            }

            # Extract context information
            contexts = self._extract_contexts(root)

            # Extract financial facts
            facts = self._extract_facts(root, contexts)

            # Categorize facts into financial statements
            financial_data = self._categorize_facts(facts)

            return financial_data

        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            raise InvalidDataError(f"Invalid XBRL XML: {e}")
        except Exception as e:
            logger.error(f"Error parsing XBRL instance: {e}")
            raise InvalidDataError(f"Failed to parse XBRL instance: {e}")

    def _extract_contexts(self, root: ET.Element) -> Dict[str, Dict[str, Any]]:
        """Extract context information from XBRL."""
        contexts = {}

        for context in root.findall(".//xbrli:context", self.XBRL_NAMESPACES):
            context_id = context.get("id")
            if not context_id:
                continue

            # Extract period information
            period_elem = context.find(".//xbrli:period", self.XBRL_NAMESPACES)
            period_info = {}

            if period_elem is not None:
                instant = period_elem.find("xbrli:instant", self.XBRL_NAMESPACES)
                start_date = period_elem.find("xbrli:startDate", self.XBRL_NAMESPACES)
                end_date = period_elem.find("xbrli:endDate", self.XBRL_NAMESPACES)

                if instant is not None:
                    period_info["type"] = "instant"
                    period_info["date"] = instant.text
                elif start_date is not None and end_date is not None:
                    period_info["type"] = "duration"
                    period_info["start_date"] = start_date.text
                    period_info["end_date"] = end_date.text

            contexts[context_id] = {
                "period": period_info,
                "entity": self._extract_entity_info(context),
            }

        return contexts

    def _extract_entity_info(self, context: ET.Element) -> Dict[str, Any]:
        """Extract entity information from context."""
        entity_info = {}

        entity = context.find(".//xbrli:entity", self.XBRL_NAMESPACES)
        if entity is not None:
            identifier = entity.find("xbrli:identifier", self.XBRL_NAMESPACES)
            if identifier is not None:
                entity_info["identifier"] = identifier.text
                entity_info["scheme"] = identifier.get("scheme")

        return entity_info

    def _extract_facts(
        self, root: ET.Element, contexts: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract financial facts from XBRL."""
        facts = []

        # Find all elements that are not in the xbrli namespace (these are the facts)
        for elem in root:
            if elem.tag.startswith("{") and not elem.tag.startswith(
                "{http://www.xbrl.org/2003/instance}"
            ):
                context_ref = elem.get("contextRef")
                unit_ref = elem.get("unitRef")

                if context_ref and context_ref in contexts:
                    fact = {
                        "name": elem.tag,
                        "value": elem.text,
                        "context": contexts[context_ref],
                        "unit_ref": unit_ref,
                        "decimals": elem.get("decimals"),
                        "precision": elem.get("precision"),
                    }
                    facts.append(fact)

        return facts

    def _categorize_facts(self, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Categorize facts into financial statement sections."""
        financial_data = {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
            "metadata": {},
        }

        # Mapping of XBRL element names to our standardized names
        element_mapping = {
            # Income Statement
            "NetSales": "revenue",
            "OperatingIncome": "operating_income",
            "NetIncome": "net_income",
            "GrossProfit": "gross_profit",
            "SellingGeneralAndAdministrativeExpenses": "sga_expenses",
            # Balance Sheet
            "TotalAssets": "total_assets",
            "TotalLiabilities": "total_liabilities",
            "NetAssets": "shareholders_equity",
            "CashAndCashEquivalents": "cash_and_equivalents",
            "CurrentAssets": "current_assets",
            "CurrentLiabilities": "current_liabilities",
            # Cash Flow
            "CashFlowsFromOperatingActivities": "operating_cash_flow",
            "CashFlowsFromInvestingActivities": "investing_cash_flow",
            "CashFlowsFromFinancingActivities": "financing_cash_flow",
        }

        for fact in facts:
            # Extract element name from full tag
            element_name = (
                fact["name"].split("}")[-1] if "}" in fact["name"] else fact["name"]
            )

            # Convert value to float if possible
            try:
                value = float(fact["value"]) if fact["value"] else None
            except (ValueError, TypeError):
                value = fact["value"]

            # Determine which statement this belongs to
            if element_name in element_mapping:
                standard_name = element_mapping[element_name]

                # Categorize by element type
                if element_name in [
                    "NetSales",
                    "OperatingIncome",
                    "NetIncome",
                    "GrossProfit",
                    "SellingGeneralAndAdministrativeExpenses",
                ]:
                    financial_data["income_statement"][standard_name] = {
                        "value": value,
                        "period": fact["context"]["period"],
                        "unit": fact["unit_ref"],
                    }
                elif element_name in [
                    "TotalAssets",
                    "TotalLiabilities",
                    "NetAssets",
                    "CashAndCashEquivalents",
                    "CurrentAssets",
                    "CurrentLiabilities",
                ]:
                    financial_data["balance_sheet"][standard_name] = {
                        "value": value,
                        "period": fact["context"]["period"],
                        "unit": fact["unit_ref"],
                    }
                elif element_name in [
                    "CashFlowsFromOperatingActivities",
                    "CashFlowsFromInvestingActivities",
                    "CashFlowsFromFinancingActivities",
                ]:
                    financial_data["cash_flow"][standard_name] = {
                        "value": value,
                        "period": fact["context"]["period"],
                        "unit": fact["unit_ref"],
                    }

        return financial_data

    async def health_check(self) -> HealthCheck:
        """Check EDINET API health."""
        start_time = datetime.utcnow()

        try:
            # Make a simple API call to check health
            params = {"date": datetime.utcnow().strftime("%Y-%m-%d")}
            await self._make_request("documents.json", params)

            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return HealthCheck(
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                metadata={
                    "requests_today": self._total_requests,
                    "requests_this_hour": self._request_count_hour,
                    "requests_this_minute": self._request_count_minute,
                },
            )

        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                error_message=str(e),
            )

    async def get_rate_limit_info(self) -> RateLimitInfo:
        """Get current rate limit information."""
        now = datetime.utcnow()

        return RateLimitInfo(
            requests_per_minute=self.requests_per_minute,
            requests_per_hour=self.requests_per_hour,
            requests_per_day=24 * self.requests_per_hour,  # Estimated
            current_usage={
                "minute": self._request_count_minute,
                "hour": self._request_count_hour,
                "day": self._total_requests,  # Simplified
            },
            reset_times={
                "minute": self._last_minute_reset + timedelta(minutes=1),
                "hour": self._last_hour_reset + timedelta(hours=1),
                "day": now + timedelta(days=1),
            },
        )

    async def get_cost_info(self) -> CostInfo:
        """Get cost information (EDINET is free)."""
        return CostInfo(
            cost_per_request=0.0,
            currency="JPY",
            monthly_budget=0.0,
            current_monthly_usage=0.0,
        )

    async def get_financial_statements(
        self, symbol: str, statement_type: str, period: str = "annual"
    ) -> List[Dict[str, Any]]:
        """
        Get financial statements for a company.

        Args:
            symbol: Stock symbol (securities code)
            statement_type: Type of statement (income, balance, cash_flow)
            period: Period type (annual, quarterly)

        Returns:
            List of financial statement data
        """
        try:
            sec_code = self._normalize_symbol(symbol)

            # Determine document type based on period
            if period == "annual":
                doc_type_code = "120"  # Annual Securities Report
            elif period == "quarterly":
                doc_type_code = "130"  # Quarterly Report
            else:
                raise InvalidDataError(f"Unsupported period type: {period}")

            # Search for recent documents (last 2 years)
            date_from = datetime.utcnow() - timedelta(days=730)
            date_to = datetime.utcnow()

            documents = await self._search_documents(
                sec_code=sec_code,
                doc_type_code=doc_type_code,
                date_from=date_from,
                date_to=date_to,
            )

            if not documents:
                return []

            results = []

            # Process up to 5 most recent documents
            for doc in documents[:5]:
                try:
                    # Download and parse document
                    xbrl_content = await self._download_document(doc.doc_id)
                    financial_data = self._parse_xbrl_financial_data(xbrl_content)

                    # Extract requested statement type
                    if statement_type in financial_data:
                        statement_data = {
                            "symbol": symbol,
                            "statement_type": statement_type,
                            "period": period,
                            "fiscal_year": doc.period_end.year
                            if doc.period_end
                            else None,
                            "fiscal_period": self._determine_fiscal_period(
                                doc.period_start, doc.period_end
                            ),
                            "submit_date": doc.submit_date.isoformat(),
                            "period_start": doc.period_start.isoformat()
                            if doc.period_start
                            else None,
                            "period_end": doc.period_end.isoformat()
                            if doc.period_end
                            else None,
                            "company_name": doc.filer_name,
                            "data": financial_data[statement_type],
                            "source": "EDINET",
                            "document_id": doc.doc_id,
                        }

                        results.append(statement_data)

                except Exception as e:
                    logger.warning(f"Error processing document {doc.doc_id}: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Error getting financial statements for {symbol}: {e}")
            raise

    def _determine_fiscal_period(
        self, start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> str:
        """Determine fiscal period from dates."""
        if not end_date:
            return "unknown"

        if not start_date:
            return "annual"

        # Calculate period length in months
        months = (end_date.year - start_date.year) * 12 + (
            end_date.month - start_date.month
        )

        if months >= 11:  # Annual (allowing for slight variations)
            return "annual"
        elif 2 <= months <= 4:  # Quarterly
            quarter = ((end_date.month - 1) // 3) + 1
            return f"Q{quarter}"
        elif 5 <= months <= 7:  # Semi-annual
            return "H1" if end_date.month <= 6 else "H2"
        else:
            return "other"

    async def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get company overview information.

        Args:
            symbol: Stock symbol

        Returns:
            Company overview data
        """
        try:
            sec_code = self._normalize_symbol(symbol)

            # Search for most recent annual report
            date_from = datetime.utcnow() - timedelta(days=365)
            date_to = datetime.utcnow()

            documents = await self._search_documents(
                sec_code=sec_code,
                doc_type_code="120",  # Annual Securities Report
                date_from=date_from,
                date_to=date_to,
            )

            if not documents:
                raise InvalidDataError(f"No recent annual reports found for {symbol}")

            latest_doc = documents[0]

            # Basic company information from document metadata
            overview = {
                "symbol": symbol,
                "securities_code": sec_code,
                "company_name": latest_doc.filer_name,
                "edinet_code": latest_doc.edinet_code,
                "jcn": latest_doc.jcn,
                "latest_report_date": latest_doc.submit_date.isoformat(),
                "fiscal_year_end": latest_doc.period_end.isoformat()
                if latest_doc.period_end
                else None,
                "source": "EDINET",
            }

            # Try to get additional financial metrics from latest report
            try:
                xbrl_content = await self._download_document(latest_doc.doc_id)
                financial_data = self._parse_xbrl_financial_data(xbrl_content)

                # Add key financial metrics to overview
                if "balance_sheet" in financial_data:
                    bs_data = financial_data["balance_sheet"]
                    if "total_assets" in bs_data:
                        overview["total_assets"] = bs_data["total_assets"]["value"]
                    if "shareholders_equity" in bs_data:
                        overview["shareholders_equity"] = bs_data[
                            "shareholders_equity"
                        ]["value"]

                if "income_statement" in financial_data:
                    is_data = financial_data["income_statement"]
                    if "revenue" in is_data:
                        overview["revenue"] = is_data["revenue"]["value"]
                    if "net_income" in is_data:
                        overview["net_income"] = is_data["net_income"]["value"]

            except Exception as e:
                logger.warning(f"Could not extract financial metrics for {symbol}: {e}")

            return overview

        except Exception as e:
            logger.error(f"Error getting company overview for {symbol}: {e}")
            raise

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
