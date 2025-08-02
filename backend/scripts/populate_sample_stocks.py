"""
Script to populate the database with sample Japanese stock data for testing.
"""

import sys
import os
from datetime import date, timedelta
from decimal import Decimal
import random

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.stock import Stock, StockPriceHistory, StockDailyMetrics


def create_sample_stocks(db: Session):
    """Create sample stock data."""
    
    # Major Japanese companies for realistic testing
    sample_companies = [
        {
            "ticker": "7203",
            "company_name_jp": "トヨタ自動車",
            "company_name_en": "Toyota Motor Corporation",
            "sector_jp": "輸送用機器",
            "industry_jp": "自動車",
            "description": "世界最大級の自動車メーカー"
        },
        {
            "ticker": "9984",
            "company_name_jp": "ソフトバンクグループ",
            "company_name_en": "SoftBank Group Corp",
            "sector_jp": "情報・通信業",
            "industry_jp": "通信",
            "description": "投資持株会社"
        },
        {
            "ticker": "6758",
            "company_name_jp": "ソニーグループ",
            "company_name_en": "Sony Group Corporation",
            "sector_jp": "電気機器",
            "industry_jp": "電子機器",
            "description": "エレクトロニクス・エンターテインメント企業"
        },
        {
            "ticker": "8306",
            "company_name_jp": "三菱UFJフィナンシャル・グループ",
            "company_name_en": "Mitsubishi UFJ Financial Group",
            "sector_jp": "銀行業",
            "industry_jp": "銀行",
            "description": "日本最大の金融グループ"
        },
        {
            "ticker": "9432",
            "company_name_jp": "日本電信電話",
            "company_name_en": "Nippon Telegraph and Telephone Corporation",
            "sector_jp": "情報・通信業",
            "industry_jp": "通信",
            "description": "日本最大の通信事業者"
        },
        {
            "ticker": "6861",
            "company_name_jp": "キーエンス",
            "company_name_en": "Keyence Corporation",
            "sector_jp": "電気機器",
            "industry_jp": "電子機器",
            "description": "センサー・測定器メーカー"
        },
        {
            "ticker": "4519",
            "company_name_jp": "中外製薬",
            "company_name_en": "Chugai Pharmaceutical Co., Ltd.",
            "sector_jp": "医薬品",
            "industry_jp": "医薬品",
            "description": "製薬会社"
        },
        {
            "ticker": "8035",
            "company_name_jp": "東京エレクトロン",
            "company_name_en": "Tokyo Electron Limited",
            "sector_jp": "電気機器",
            "industry_jp": "半導体製造装置",
            "description": "半導体製造装置メーカー"
        },
        {
            "ticker": "6954",
            "company_name_jp": "ファナック",
            "company_name_en": "FANUC Corporation",
            "sector_jp": "電気機器",
            "industry_jp": "工作機械",
            "description": "工作機械・ロボットメーカー"
        },
        {
            "ticker": "4661",
            "company_name_jp": "オリエンタルランド",
            "company_name_en": "Oriental Land Co., Ltd.",
            "sector_jp": "サービス業",
            "industry_jp": "テーマパーク",
            "description": "東京ディズニーリゾート運営"
        }
    ]
    
    # Additional sample companies for search testing
    additional_companies = []
    sectors = ["電気機器", "情報・通信業", "銀行業", "小売業", "建設業", "不動産業", "化学", "食品"]
    industries = ["電子機器", "通信", "銀行", "小売", "建設", "不動産", "化学製品", "食品製造"]
    
    for i in range(100):
        ticker = f"{1000 + i:04d}"
        sector = random.choice(sectors)
        industry = random.choice(industries)
        
        additional_companies.append({
            "ticker": ticker,
            "company_name_jp": f"テスト株式会社{i+1}",
            "company_name_en": f"Test Corporation {i+1}",
            "sector_jp": sector,
            "industry_jp": industry,
            "description": f"テスト用の{sector}企業"
        })
    
    all_companies = sample_companies + additional_companies
    
    # Create stock records
    stocks_created = 0
    for company_data in all_companies:
        # Check if stock already exists
        existing_stock = db.query(Stock).filter(Stock.ticker == company_data["ticker"]).first()
        if existing_stock:
            print(f"Stock {company_data['ticker']} already exists, skipping...")
            continue
        
        stock = Stock(
            ticker=company_data["ticker"],
            company_name_jp=company_data["company_name_jp"],
            company_name_en=company_data["company_name_en"],
            sector_jp=company_data["sector_jp"],
            industry_jp=company_data["industry_jp"],
            description=company_data["description"],
            listing_date=date(2000, 1, 1),  # Default listing date
            is_active=True
        )
        
        db.add(stock)
        stocks_created += 1
    
    db.commit()
    print(f"Created {stocks_created} stock records")
    return all_companies


def create_sample_price_data(db: Session, companies):
    """Create sample price history data."""
    
    today = date.today()
    days_to_create = 90  # 3 months of data
    
    price_records_created = 0
    
    for company in companies[:20]:  # Only create price data for first 20 companies
        ticker = company["ticker"]
        
        # Check if price data already exists
        existing_data = db.query(StockPriceHistory).filter(
            StockPriceHistory.ticker == ticker
        ).first()
        
        if existing_data:
            print(f"Price data for {ticker} already exists, skipping...")
            continue
        
        # Generate base price based on company (for consistency)
        base_price = 1000 + (hash(ticker) % 10000)
        current_price = base_price
        
        for days_back in range(days_to_create):
            price_date = today - timedelta(days=days_back)
            
            # Skip weekends (simple approximation)
            if price_date.weekday() >= 5:
                continue
            
            # Generate realistic price movement
            daily_change = random.uniform(-0.05, 0.05)  # ±5% daily change
            current_price = max(current_price * (1 + daily_change), 100)  # Minimum price of 100
            
            # Generate OHLCV data
            open_price = current_price * random.uniform(0.98, 1.02)
            high_price = max(open_price, current_price) * random.uniform(1.0, 1.03)
            low_price = min(open_price, current_price) * random.uniform(0.97, 1.0)
            close_price = current_price
            volume = random.randint(100000, 10000000)
            
            price_record = StockPriceHistory(
                ticker=ticker,
                date=price_date,
                open=Decimal(f"{open_price:.2f}"),
                high=Decimal(f"{high_price:.2f}"),
                low=Decimal(f"{low_price:.2f}"),
                close=Decimal(f"{close_price:.2f}"),
                volume=volume,
                adjusted_close=Decimal(f"{close_price:.2f}")
            )
            
            db.add(price_record)
            price_records_created += 1
    
    db.commit()
    print(f"Created {price_records_created} price history records")


def create_sample_metrics_data(db: Session, companies):
    """Create sample daily metrics data."""
    
    today = date.today()
    metrics_created = 0
    
    for company in companies[:20]:  # Only create metrics for first 20 companies
        ticker = company["ticker"]
        
        # Check if metrics already exist
        existing_metrics = db.query(StockDailyMetrics).filter(
            StockDailyMetrics.ticker == ticker
        ).first()
        
        if existing_metrics:
            print(f"Metrics for {ticker} already exist, skipping...")
            continue
        
        # Get latest price for market cap calculation
        latest_price = db.query(StockPriceHistory).filter(
            StockPriceHistory.ticker == ticker
        ).order_by(StockPriceHistory.date.desc()).first()
        
        if not latest_price:
            continue
        
        # Generate realistic metrics
        shares_outstanding = random.randint(100000000, 5000000000)  # 100M to 5B shares
        market_cap = int(float(latest_price.close) * shares_outstanding)
        pe_ratio = Decimal(f"{random.uniform(5.0, 50.0):.2f}")
        pb_ratio = Decimal(f"{random.uniform(0.5, 5.0):.2f}")
        dividend_yield = Decimal(f"{random.uniform(0.0, 0.08):.4f}")  # 0-8%
        
        metrics = StockDailyMetrics(
            ticker=ticker,
            date=today,
            market_cap=market_cap,
            pe_ratio=pe_ratio,
            pb_ratio=pb_ratio,
            dividend_yield=dividend_yield,
            shares_outstanding=shares_outstanding
        )
        
        db.add(metrics)
        metrics_created += 1
    
    db.commit()
    print(f"Created {metrics_created} daily metrics records")


def main():
    """Main function to populate sample data."""
    print("Populating database with sample stock data...")
    
    db = SessionLocal()
    try:
        # Create sample stocks
        companies = create_sample_stocks(db)
        
        # Create sample price data
        create_sample_price_data(db, companies)
        
        # Create sample metrics data
        create_sample_metrics_data(db, companies)
        
        print("Sample data population completed successfully!")
        
    except Exception as e:
        print(f"Error populating sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()