"""
AI Analysis Service for generating stock analysis using Google Gemini API.
"""

import hashlib
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis import AIAnalysisCache


# Define AIAnalysisRequest locally since it's not properly imported
class AIAnalysisRequest:
    """AI analysis request."""

    def __init__(self, ticker: str, analysis_type: str, force_refresh: bool = False):
        self.ticker = ticker
        self.analysis_type = analysis_type
        self.force_refresh = force_refresh


from app.services.cost_manager import CostManager
from app.services.data_transformer import DataTransformer

logger = logging.getLogger(__name__)


class GeminiAnalysisClient:
    """Google Gemini API client for stock analysis."""

    def __init__(self, api_key: str):
        """Initialize Gemini client."""
        if not api_key:
            raise ValueError("Google Gemini API key is required")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-pro")
        self.cost_tracker = CostManager()

        # Token cost estimates (approximate)
        self.input_token_cost = 0.00025  # $0.00025 per 1K input tokens
        self.output_token_cost = 0.0005  # $0.0005 per 1K output tokens

    def estimate_cost(
        self, prompt_length: int, expected_response_length: int = 2000
    ) -> float:
        """Estimate cost for API call based on token count."""
        # Rough estimation: 1 token ≈ 4 characters
        input_tokens = prompt_length / 4
        output_tokens = expected_response_length / 4

        input_cost = (input_tokens / 1000) * self.input_token_cost
        output_cost = (output_tokens / 1000) * self.output_token_cost

        return input_cost + output_cost

    async def generate_analysis(
        self, prompt: str, ticker: str, analysis_type: str
    ) -> Dict[str, Any]:
        """Generate analysis using Gemini API."""
        try:
            # Estimate cost
            estimated_cost = self.estimate_cost(len(prompt))

            # Check budget
            if not await self.cost_tracker.can_afford(estimated_cost):
                raise BudgetExceededException(
                    f"Insufficient budget for analysis. Estimated cost: ${estimated_cost:.4f}"
                )

            # Generate content
            start_time = datetime.now()
            response = await self.model.generate_content_async(prompt)
            end_time = datetime.now()

            processing_time = (end_time - start_time).total_seconds() * 1000  # ms

            # Parse response
            result = self._parse_response(response.text, analysis_type)

            # Track cost
            await self.cost_tracker.record_usage(ticker, estimated_cost)

            return {
                "result": result,
                "processing_time_ms": int(processing_time),
                "estimated_cost": estimated_cost,
                "model_version": "gemini-pro",
                "generated_at": datetime.now(),
            }

        except Exception as e:
            logger.error(f"Error generating analysis for {ticker}: {str(e)}")
            raise AnalysisGenerationException(f"Failed to generate analysis: {str(e)}")

    def _parse_response(self, response_text: str, analysis_type: str) -> Dict[str, Any]:
        """Parse and validate Gemini response."""
        try:
            # Try to extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                # Look for JSON-like structure
                json_text = response_text.strip()

            # Parse JSON
            parsed_result = json.loads(json_text)

            # Validate required fields based on analysis type
            self._validate_analysis_result(parsed_result, analysis_type)

            return parsed_result

        except json.JSONDecodeError:
            # If JSON parsing fails, return structured text response
            logger.warning(
                f"Could not parse JSON response for {analysis_type}, returning text"
            )
            return {"analysis_text": response_text, "format": "text", "parsed": False}
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            raise ResponseParsingException(
                f"Failed to parse analysis response: {str(e)}"
            )

    def _validate_analysis_result(self, result: Dict[str, Any], analysis_type: str):
        """Validate analysis result structure."""
        required_fields = {
            "short_term": ["rating", "confidence", "key_factors", "price_target_range"],
            "mid_term": ["rating", "confidence", "key_factors", "price_target_range"],
            "long_term": ["rating", "confidence", "key_factors", "price_target_range"],
            "comprehensive": [
                "rating",
                "confidence",
                "key_factors",
                "price_target_range",
            ],
        }

        if analysis_type in required_fields:
            missing_fields = []
            for field in required_fields[analysis_type]:
                if field not in result:
                    missing_fields.append(field)

            if missing_fields:
                logger.warning(
                    f"Missing fields in {analysis_type} analysis: {missing_fields}"
                )


class PromptTemplateManager:
    """Manages prompt templates for different analysis types."""

    def __init__(self):
        """Initialize prompt templates."""
        self.templates = {
            "short_term": self._get_short_term_template(),
            "mid_term": self._get_mid_term_template(),
            "long_term": self._get_long_term_template(),
            "comprehensive": self._get_comprehensive_template(),
        }

    def build_prompt(
        self,
        analysis_type: str,
        context: Dict[str, Any],
        ticker: str,
        company_name: str,
    ) -> str:
        """Build analysis prompt from template and context."""
        if analysis_type not in self.templates:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

        template = self.templates[analysis_type]

        # Format template with context
        try:
            prompt = template.format(
                ticker=ticker, company_name=company_name, **context
            )
            return prompt
        except KeyError as e:
            logger.error(f"Missing context key for prompt template: {e}")
            raise PromptBuildException(f"Missing required context: {e}")

    def _get_short_term_template(self) -> str:
        """Get short-term analysis prompt template."""
        return """
あなたは日本株の専門アナリストです。以下のデータに基づいて、{company_name} ({ticker}) の短期（1-4週間）分析を行ってください。

## 分析データ
### 株価データ
{price_data}

### テクニカル指標
{technical_indicators}

### 最近のニュース・センチメント
{news_sentiment}

### 出来高分析
{volume_analysis}

## 分析要求
以下の形式でJSON形式で回答してください：

```json
{{
  "rating": "Strong Bullish / Bullish / Neutral / Bearish / Strong Bearish",
  "confidence": 0.0-1.0の数値,
  "key_factors": ["要因1", "要因2", "要因3"],
  "price_target_range": {{"min": 最低目標価格, "max": 最高目標価格}},
  "risk_factors": ["リスク1", "リスク2"],
  "technical_outlook": "テクニカル分析の見通し",
  "catalyst_events": ["短期的な材料1", "短期的な材料2"],
  "trading_strategy": "推奨取引戦略",
  "reasoning": "分析の根拠と理由"
}}
```

## 注意事項
- 日本の市場環境を考慮してください
- テクニカル分析を重視してください
- 短期的な値動きに影響する要因を重点的に分析してください
- 信頼度は客観的な根拠に基づいて設定してください
"""

    def _get_mid_term_template(self) -> str:
        """Get mid-term analysis prompt template."""
        return """
あなたは日本株の専門アナリストです。以下のデータに基づいて、{company_name} ({ticker}) の中期（1-6ヶ月）分析を行ってください。

## 分析データ
### 財務データ
{financial_data}

### 業界動向
{industry_trends}

### 四半期業績トレンド
{quarterly_trends}

### 競合比較
{peer_comparison}

### マクロ経済環境
{macro_environment}

## 分析要求
以下の形式でJSON形式で回答してください：

```json
{{
  "rating": "Strong Bullish / Bullish / Neutral / Bearish / Strong Bearish",
  "confidence": 0.0-1.0の数値,
  "key_factors": ["要因1", "要因2", "要因3"],
  "price_target_range": {{"min": 最低目標価格, "max": 最高目標価格}},
  "risk_factors": ["リスク1", "リスク2"],
  "fundamental_outlook": "ファンダメンタル分析の見通し",
  "growth_drivers": ["成長要因1", "成長要因2"],
  "industry_position": "業界内でのポジション分析",
  "earnings_forecast": "業績予想",
  "valuation_analysis": "バリュエーション分析",
  "reasoning": "分析の根拠と理由"
}}
```

## 注意事項
- 日本企業の特性を考慮してください
- ファンダメンタル分析を重視してください
- 業界動向と競合状況を詳しく分析してください
- 四半期決算の影響を考慮してください
"""

    def _get_long_term_template(self) -> str:
        """Get long-term analysis prompt template."""
        return """
あなたは日本株の専門アナリストです。以下のデータに基づいて、{company_name} ({ticker}) の長期（1年以上）投資分析を行ってください。

## 分析データ
### 年次財務データ
{annual_financial_data}

### 事業戦略・計画
{business_strategy}

### ESG評価
{esg_metrics}

### 長期業界見通し
{long_term_industry_outlook}

### 経営陣評価
{management_analysis}

### 配当政策
{dividend_policy}

## 分析要求
以下の形式でJSON形式で回答してください：

```json
{{
  "rating": "Strong Bullish / Bullish / Neutral / Bearish / Strong Bearish",
  "confidence": 0.0-1.0の数値,
  "key_factors": ["要因1", "要因2", "要因3"],
  "price_target_range": {{"min": 最低目標価格, "max": 最高目標価格}},
  "risk_factors": ["リスク1", "リスク2"],
  "investment_thesis": "投資テーマ",
  "competitive_advantages": ["競争優位性1", "競争優位性2"],
  "long_term_catalysts": ["長期材料1", "長期材料2"],
  "sustainability_analysis": "持続可能性分析",
  "dividend_outlook": "配当見通し",
  "valuation_metrics": "バリュエーション指標",
  "reasoning": "分析の根拠と理由"
}}
```

## 注意事項
- 日本企業の長期的な価値創造能力を評価してください
- ESGの観点も含めて分析してください
- 持続的な競争優位性を重視してください
- 配当政策と株主還元を考慮してください
"""

    def _get_comprehensive_template(self) -> str:
        """Get comprehensive analysis prompt template."""
        return """
あなたは日本株の専門アナリストです。以下のデータに基づいて、{company_name} ({ticker}) の包括的な投資分析を行ってください。

## 分析データ
### 株価・テクニカルデータ
{price_technical_data}

### 財務・ファンダメンタルデータ
{fundamental_data}

### ニュース・センチメントデータ
{news_sentiment_data}

### 業界・競合データ
{industry_competitive_data}

### マクロ経済データ
{macro_economic_data}

## 分析要求
以下の形式でJSON形式で回答してください：

```json
{{
  "overall_rating": "Strong Bullish / Bullish / Neutral / Bearish / Strong Bearish",
  "confidence": 0.0-1.0の数値,
  "short_term_outlook": {{
    "rating": "評価",
    "key_factors": ["要因1", "要因2"],
    "time_horizon": "1-4週間"
  }},
  "mid_term_outlook": {{
    "rating": "評価", 
    "key_factors": ["要因1", "要因2"],
    "time_horizon": "1-6ヶ月"
  }},
  "long_term_outlook": {{
    "rating": "評価",
    "key_factors": ["要因1", "要因2"], 
    "time_horizon": "1年以上"
  }},
  "price_targets": {{
    "short_term": {{"min": 価格, "max": 価格}},
    "mid_term": {{"min": 価格, "max": 価格}},
    "long_term": {{"min": 価格, "max": 価格}}
  }},
  "investment_recommendation": "推奨投資判断",
  "key_strengths": ["強み1", "強み2", "強み3"],
  "key_risks": ["リスク1", "リスク2", "リスク3"],
  "catalysts": ["材料1", "材料2"],
  "valuation_summary": "バリュエーション要約",
  "reasoning": "総合的な分析根拠"
}}
```

## 注意事項
- 短期・中期・長期の全ての観点から分析してください
- テクニカル・ファンダメンタル・センチメント分析を統合してください
- 日本市場の特性を十分に考慮してください
- 包括的で実用的な投資判断を提供してください
"""


class AIAnalysisService:
    """Main AI analysis service with multi-source data aggregation."""

    def __init__(self, db: Session):
        """Initialize AI analysis service."""
        self.db = db
        self.gemini_client = GeminiAnalysisClient(settings.GOOGLE_GEMINI_API_KEY)
        self.prompt_manager = PromptTemplateManager()
        self.data_transformer = DataTransformer(db)
        self.cost_manager = CostManager(db)

    async def generate_analysis(
        self, request: AIAnalysisRequest, user_id: str
    ) -> Dict[str, Any]:
        """Generate AI analysis for a stock with multi-source data aggregation."""
        ticker = request.ticker
        analysis_type = request.analysis_type

        logger.info(f"Starting analysis generation for {ticker} - {analysis_type}")

        # Check cache first to avoid unnecessary LLM calls
        cached_analysis = await self._check_cache(ticker, analysis_type)
        if cached_analysis and not request.force_refresh:
            should_use_cache = await self._should_use_cache(cached_analysis)
            if should_use_cache:
                logger.info(f"Using cached analysis for {ticker} - {analysis_type}")
                return self._format_cached_result(cached_analysis)

        # Multi-source data aggregation
        try:
            context = await self._aggregate_multi_source_data(ticker, analysis_type)

            # Build analysis prompt
            company_name = context.get("company_name", ticker)
            prompt = self.prompt_manager.build_prompt(
                analysis_type, context, ticker, company_name
            )

            # Generate analysis using LLM
            result = await self.gemini_client.generate_analysis(
                prompt, ticker, analysis_type
            )

            # Enhance result with additional metadata
            enhanced_result = await self._enhance_analysis_result(
                result, ticker, analysis_type, context
            )

            # Cache result for future use
            await self._cache_analysis(ticker, analysis_type, enhanced_result, prompt)

            logger.info(
                f"Successfully generated analysis for {ticker} - {analysis_type}"
            )
            return enhanced_result

        except Exception as e:
            logger.error(f"Error generating analysis for {ticker}: {str(e)}")
            raise AnalysisGenerationException(f"Failed to generate analysis: {str(e)}")

    async def generate_short_term_analysis(
        self, ticker: str, user_id: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Generate short-term momentum analysis (1-4 weeks)."""
        request = AIAnalysisRequest(
            ticker=ticker, analysis_type="short_term", force_refresh=force_refresh
        )
        return await self.generate_analysis(request, user_id)

    async def generate_mid_term_analysis(
        self, ticker: str, user_id: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Generate mid-term trend analysis (1-6 months)."""
        request = AIAnalysisRequest(
            ticker=ticker, analysis_type="mid_term", force_refresh=force_refresh
        )
        return await self.generate_analysis(request, user_id)

    async def generate_long_term_analysis(
        self, ticker: str, user_id: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Generate long-term value analysis (1+ years)."""
        request = AIAnalysisRequest(
            ticker=ticker, analysis_type="long_term", force_refresh=force_refresh
        )
        return await self.generate_analysis(request, user_id)

    async def generate_comprehensive_analysis(
        self, ticker: str, user_id: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Generate comprehensive analysis covering all time horizons."""
        request = AIAnalysisRequest(
            ticker=ticker, analysis_type="comprehensive", force_refresh=force_refresh
        )
        return await self.generate_analysis(request, user_id)

    async def _aggregate_multi_source_data(
        self, ticker: str, analysis_type: str
    ) -> Dict[str, Any]:
        """Aggregate data from multiple sources for comprehensive analysis."""
        logger.info(f"Aggregating multi-source data for {ticker} - {analysis_type}")

        # Prepare comprehensive analysis context
        context = await self.data_transformer.prepare_analysis_context(
            ticker, analysis_type
        )

        # Add analysis-specific enhancements
        if analysis_type == "short_term":
            # Enhance with real-time market data
            context.update(await self._get_real_time_market_context(ticker))

        elif analysis_type == "mid_term":
            # Enhance with quarterly earnings and industry trends
            context.update(await self._get_quarterly_context(ticker))
            context.update(await self._get_industry_context(ticker))

        elif analysis_type == "long_term":
            # Enhance with annual data and strategic analysis
            context.update(await self._get_annual_context(ticker))
            context.update(await self._get_strategic_context(ticker))

        elif analysis_type == "comprehensive":
            # Combine all data sources
            context.update(await self._get_real_time_market_context(ticker))
            context.update(await self._get_quarterly_context(ticker))
            context.update(await self._get_industry_context(ticker))
            context.update(await self._get_annual_context(ticker))
            context.update(await self._get_strategic_context(ticker))

        # Add data quality metrics
        context["data_quality"] = await self._assess_data_quality(context)

        return context

    async def _enhance_analysis_result(
        self,
        result: Dict[str, Any],
        ticker: str,
        analysis_type: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enhance analysis result with additional metadata and validation."""
        enhanced_result = result.copy()

        # Add analysis metadata
        enhanced_result["analysis_metadata"] = {
            "ticker": ticker,
            "analysis_type": analysis_type,
            "data_sources_used": context.get("data_sources", []),
            "data_quality_score": context.get("data_quality", {}).get(
                "overall_score", 0.0
            ),
            "analysis_timestamp": datetime.now().isoformat(),
            "model_version": result.get("model_version", "gemini-pro"),
            "processing_time_ms": result.get("processing_time_ms", 0),
        }

        # Add confidence scoring
        enhanced_result[
            "confidence_metrics"
        ] = await self._calculate_confidence_metrics(result, context)

        # Add risk assessment
        enhanced_result["risk_assessment"] = await self._assess_analysis_risks(
            result, ticker, analysis_type
        )

        # Validate analysis result
        validation_result = await self._validate_analysis_result(result, analysis_type)
        enhanced_result["validation"] = validation_result

        return enhanced_result

    async def _check_cache(
        self, ticker: str, analysis_type: str
    ) -> Optional[AIAnalysisCache]:
        """Check for cached analysis."""
        return (
            self.db.query(AIAnalysisCache)
            .filter(
                AIAnalysisCache.ticker == ticker,
                AIAnalysisCache.analysis_type == analysis_type,
            )
            .order_by(AIAnalysisCache.created_at.desc())
            .first()
        )

    async def _should_use_cache(self, cached_analysis: AIAnalysisCache) -> bool:
        """Determine if cached analysis should be used."""
        return await self.cost_manager.should_use_cache(
            cached_analysis.ticker, cached_analysis.created_at
        )

    async def _cache_analysis(
        self, ticker: str, analysis_type: str, result: Dict[str, Any], prompt: str
    ):
        """Cache analysis result."""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

        cache_entry = AIAnalysisCache(
            ticker=ticker,
            analysis_date=date.today(),
            analysis_type=analysis_type,
            model_version=result.get("model_version", "gemini-pro"),
            prompt_hash=prompt_hash,
            analysis_result=result["result"],
            confidence_score=result["result"].get("confidence"),
            processing_time_ms=result.get("processing_time_ms"),
            cost_usd=Decimal(str(result.get("estimated_cost", 0))),
        )

        self.db.add(cache_entry)
        self.db.commit()

    def _format_cached_result(self, cached_analysis: AIAnalysisCache) -> Dict[str, Any]:
        """Format cached analysis result."""
        return {
            "result": cached_analysis.analysis_result,
            "processing_time_ms": cached_analysis.processing_time_ms,
            "estimated_cost": float(cached_analysis.cost_usd or 0),
            "model_version": cached_analysis.model_version,
            "generated_at": cached_analysis.created_at,
            "from_cache": True,
            "cache_age_seconds": (
                datetime.now() - cached_analysis.created_at
            ).total_seconds(),
        }

    async def _get_real_time_market_context(self, ticker: str) -> Dict[str, Any]:
        """Get real-time market context for short-term analysis."""
        try:
            # Get current market conditions
            market_context = {
                "market_status": await self._get_market_status(),
                "sector_performance": await self._get_sector_performance(ticker),
                "market_volatility": await self._get_market_volatility(),
                "trading_volume": await self._get_current_trading_volume(ticker),
            }
            return {"real_time_market_context": market_context}
        except Exception as e:
            logger.warning(f"Error getting real-time market context: {str(e)}")
            return {"real_time_market_context": "Real-time data unavailable"}

    async def _get_quarterly_context(self, ticker: str) -> Dict[str, Any]:
        """Get quarterly earnings context for mid-term analysis."""
        try:
            quarterly_context = {
                "earnings_calendar": await self._get_earnings_calendar(ticker),
                "quarterly_trends": await self._get_quarterly_performance_trends(
                    ticker
                ),
                "guidance_updates": await self._get_management_guidance(ticker),
            }
            return {"quarterly_context": quarterly_context}
        except Exception as e:
            logger.warning(f"Error getting quarterly context: {str(e)}")
            return {"quarterly_context": "Quarterly data unavailable"}

    async def _get_industry_context(self, ticker: str) -> Dict[str, Any]:
        """Get industry context for analysis."""
        try:
            industry_context = {
                "industry_trends": await self._get_industry_trends(ticker),
                "competitive_landscape": await self._get_competitive_analysis(ticker),
                "regulatory_environment": await self._get_regulatory_updates(ticker),
            }
            return {"industry_context": industry_context}
        except Exception as e:
            logger.warning(f"Error getting industry context: {str(e)}")
            return {"industry_context": "Industry data unavailable"}

    async def _get_annual_context(self, ticker: str) -> Dict[str, Any]:
        """Get annual financial context for long-term analysis."""
        try:
            annual_context = {
                "annual_reports": await self._get_annual_reports(ticker),
                "strategic_initiatives": await self._get_strategic_initiatives(ticker),
                "capital_allocation": await self._get_capital_allocation_history(
                    ticker
                ),
            }
            return {"annual_context": annual_context}
        except Exception as e:
            logger.warning(f"Error getting annual context: {str(e)}")
            return {"annual_context": "Annual data unavailable"}

    async def _get_strategic_context(self, ticker: str) -> Dict[str, Any]:
        """Get strategic context for long-term analysis."""
        try:
            strategic_context = {
                "business_model": await self._analyze_business_model(ticker),
                "competitive_advantages": await self._identify_competitive_advantages(
                    ticker
                ),
                "esg_factors": await self._get_esg_analysis(ticker),
                "management_quality": await self._assess_management_quality(ticker),
            }
            return {"strategic_context": strategic_context}
        except Exception as e:
            logger.warning(f"Error getting strategic context: {str(e)}")
            return {"strategic_context": "Strategic data unavailable"}

    async def _assess_data_quality(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of aggregated data."""
        quality_metrics = {
            "completeness": 0.0,
            "freshness": 0.0,
            "accuracy": 0.0,
            "overall_score": 0.0,
        }

        try:
            # Calculate completeness score
            required_fields = ["price_data", "technical_indicators", "financial_data"]
            available_fields = sum(
                1 for field in required_fields if field in context and context[field]
            )
            quality_metrics["completeness"] = available_fields / len(required_fields)

            # Calculate freshness score (based on data timestamps)
            freshness_scores = []
            if "analysis_timestamp" in context:
                # Simple freshness calculation - can be enhanced
                freshness_scores.append(0.9)  # Assume good freshness for now
            quality_metrics["freshness"] = (
                sum(freshness_scores) / len(freshness_scores)
                if freshness_scores
                else 0.0
            )

            # Calculate accuracy score (placeholder - would need validation logic)
            quality_metrics["accuracy"] = 0.85  # Assume good accuracy

            # Calculate overall score
            quality_metrics["overall_score"] = (
                quality_metrics["completeness"] * 0.4
                + quality_metrics["freshness"] * 0.3
                + quality_metrics["accuracy"] * 0.3
            )

        except Exception as e:
            logger.warning(f"Error assessing data quality: {str(e)}")

        return quality_metrics

    async def _calculate_confidence_metrics(
        self, result: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate confidence metrics for the analysis."""
        confidence_metrics = {
            "data_confidence": 0.0,
            "model_confidence": 0.0,
            "overall_confidence": 0.0,
        }

        try:
            # Data confidence based on data quality
            data_quality = context.get("data_quality", {})
            confidence_metrics["data_confidence"] = data_quality.get(
                "overall_score", 0.0
            )

            # Model confidence from LLM result
            llm_result = result.get("result", {})
            confidence_metrics["model_confidence"] = llm_result.get("confidence", 0.0)

            # Overall confidence calculation
            confidence_metrics["overall_confidence"] = (
                confidence_metrics["data_confidence"] * 0.4
                + confidence_metrics["model_confidence"] * 0.6
            )

        except Exception as e:
            logger.warning(f"Error calculating confidence metrics: {str(e)}")

        return confidence_metrics

    async def _assess_analysis_risks(
        self, result: Dict[str, Any], ticker: str, analysis_type: str
    ) -> Dict[str, Any]:
        """Assess risks associated with the analysis."""
        risk_assessment = {
            "data_risks": [],
            "model_risks": [],
            "market_risks": [],
            "overall_risk_level": "medium",
        }

        try:
            # Data risks
            if result.get("from_cache"):
                cache_age = result.get("cache_age_seconds", 0)
                if cache_age > 3600:  # 1 hour
                    risk_assessment["data_risks"].append(
                        "Analysis based on cached data older than 1 hour"
                    )

            # Model risks
            confidence = result.get("result", {}).get("confidence", 0.0)
            if confidence < 0.6:
                risk_assessment["model_risks"].append(
                    "Low model confidence in analysis"
                )

            # Market risks (placeholder)
            risk_assessment["market_risks"].append("General market volatility risk")

            # Calculate overall risk level
            total_risks = (
                len(risk_assessment["data_risks"])
                + len(risk_assessment["model_risks"])
                + len(risk_assessment["market_risks"])
            )
            if total_risks <= 1:
                risk_assessment["overall_risk_level"] = "low"
            elif total_risks <= 3:
                risk_assessment["overall_risk_level"] = "medium"
            else:
                risk_assessment["overall_risk_level"] = "high"

        except Exception as e:
            logger.warning(f"Error assessing analysis risks: {str(e)}")

        return risk_assessment

    async def _validate_analysis_result(
        self, result: Dict[str, Any], analysis_type: str
    ) -> Dict[str, Any]:
        """Validate the analysis result structure and content."""
        validation_result = {
            "is_valid": True,
            "validation_errors": [],
            "validation_warnings": [],
        }

        try:
            llm_result = result.get("result", {})

            # Check required fields based on analysis type
            required_fields = {
                "short_term": ["rating", "confidence", "key_factors"],
                "mid_term": ["rating", "confidence", "key_factors"],
                "long_term": ["rating", "confidence", "key_factors"],
                "comprehensive": ["overall_rating", "confidence"],
            }

            if analysis_type in required_fields:
                for field in required_fields[analysis_type]:
                    if field not in llm_result:
                        validation_result["validation_errors"].append(
                            f"Missing required field: {field}"
                        )
                        validation_result["is_valid"] = False

            # Validate confidence score
            confidence = llm_result.get("confidence", 0.0)
            if not isinstance(confidence, (int, float)) or not (
                0.0 <= confidence <= 1.0
            ):
                validation_result["validation_warnings"].append(
                    "Confidence score should be between 0.0 and 1.0"
                )

            # Validate rating
            rating = llm_result.get("rating") or llm_result.get("overall_rating")
            valid_ratings = [
                "Strong Bullish",
                "Bullish",
                "Neutral",
                "Bearish",
                "Strong Bearish",
            ]
            if rating and rating not in valid_ratings:
                validation_result["validation_warnings"].append(
                    f"Unexpected rating value: {rating}"
                )

        except Exception as e:
            logger.warning(f"Error validating analysis result: {str(e)}")
            validation_result["validation_errors"].append(f"Validation error: {str(e)}")
            validation_result["is_valid"] = False

        return validation_result

    # Placeholder methods for data retrieval - these would be implemented with actual data sources
    async def _get_market_status(self) -> str:
        """Get current market status."""
        return "open"  # Placeholder

    async def _get_sector_performance(self, ticker: str) -> Dict[str, Any]:
        """Get sector performance data."""
        return {"sector_trend": "neutral"}  # Placeholder

    async def _get_market_volatility(self) -> Dict[str, Any]:
        """Get market volatility metrics."""
        return {"volatility_level": "normal"}  # Placeholder

    async def _get_current_trading_volume(self, ticker: str) -> Dict[str, Any]:
        """Get current trading volume data."""
        return {"volume_trend": "average"}  # Placeholder

    async def _get_earnings_calendar(self, ticker: str) -> Dict[str, Any]:
        """Get earnings calendar data."""
        return {"next_earnings": "TBD"}  # Placeholder

    async def _get_quarterly_performance_trends(self, ticker: str) -> Dict[str, Any]:
        """Get quarterly performance trends."""
        return {"trend": "stable"}  # Placeholder

    async def _get_management_guidance(self, ticker: str) -> Dict[str, Any]:
        """Get management guidance updates."""
        return {"guidance": "no recent updates"}  # Placeholder

    async def _get_industry_trends(self, ticker: str) -> Dict[str, Any]:
        """Get industry trends."""
        return {"industry_outlook": "stable"}  # Placeholder

    async def _get_competitive_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get competitive analysis."""
        return {"competitive_position": "average"}  # Placeholder

    async def _get_regulatory_updates(self, ticker: str) -> Dict[str, Any]:
        """Get regulatory updates."""
        return {"regulatory_changes": "none"}  # Placeholder

    async def _get_annual_reports(self, ticker: str) -> Dict[str, Any]:
        """Get annual reports data."""
        return {"latest_annual_report": "available"}  # Placeholder

    async def _get_strategic_initiatives(self, ticker: str) -> Dict[str, Any]:
        """Get strategic initiatives."""
        return {"initiatives": "digital transformation"}  # Placeholder

    async def _get_capital_allocation_history(self, ticker: str) -> Dict[str, Any]:
        """Get capital allocation history."""
        return {"allocation_strategy": "balanced"}  # Placeholder

    async def _analyze_business_model(self, ticker: str) -> Dict[str, Any]:
        """Analyze business model."""
        return {"business_model": "traditional"}  # Placeholder

    async def _identify_competitive_advantages(self, ticker: str) -> Dict[str, Any]:
        """Identify competitive advantages."""
        return {"advantages": ["market position"]}  # Placeholder

    async def _get_esg_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get ESG analysis."""
        return {"esg_score": "B"}  # Placeholder

    async def _assess_management_quality(self, ticker: str) -> Dict[str, Any]:
        """Assess management quality."""
        return {"management_rating": "good"}  # Placeholder


# Custom exceptions
class BudgetExceededException(Exception):
    """Raised when AI analysis budget is exceeded."""

    pass


class AnalysisGenerationException(Exception):
    """Raised when analysis generation fails."""

    pass


class ResponseParsingException(Exception):
    """Raised when response parsing fails."""

    pass


class PromptBuildException(Exception):
    """Raised when prompt building fails."""

    pass
