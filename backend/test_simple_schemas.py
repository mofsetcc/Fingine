"""
Simple test to verify schema validation works.
"""

from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, ValidationError
import pytest


class SimpleUserRegistration(BaseModel):
    """Simple user registration schema for testing."""
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")


class SimplePriceData(BaseModel):
    """Simple price data schema for testing."""
    ticker: str = Field(..., max_length=10, description="Stock ticker")
    date: date = Field(..., description="Price date")
    open_price: Decimal = Field(..., description="Opening price")
    close_price: Decimal = Field(..., description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")


def test_user_registration_valid():
    """Test valid user registration."""
    data = {
        "email": "test@example.com",
        "password": "SecurePass123"
    }
    user_reg = SimpleUserRegistration(**data)
    assert user_reg.email == "test@example.com"
    assert user_reg.password == "SecurePass123"


def test_user_registration_invalid_password():
    """Test user registration with invalid password."""
    data = {
        "email": "test@example.com",
        "password": "weak"  # Too short
    }
    with pytest.raises(ValidationError):
        SimpleUserRegistration(**data)


def test_price_data_valid():
    """Test valid price data."""
    data = {
        "ticker": "7203",
        "date": date(2024, 1, 15),
        "open_price": Decimal("2500.00"),
        "close_price": Decimal("2520.00"),
        "volume": 1000000
    }
    price_data = SimplePriceData(**data)
    assert price_data.ticker == "7203"
    assert price_data.open_price == Decimal("2500.00")
    assert price_data.volume == 1000000


def test_price_data_invalid_volume():
    """Test price data with invalid volume."""
    data = {
        "ticker": "7203",
        "date": date(2024, 1, 15),
        "open_price": Decimal("2500.00"),
        "close_price": Decimal("2520.00"),
        "volume": -1000  # Negative volume
    }
    with pytest.raises(ValidationError):
        SimplePriceData(**data)


if __name__ == "__main__":
    test_user_registration_valid()
    test_price_data_valid()
    print("All basic schema validation tests passed!")