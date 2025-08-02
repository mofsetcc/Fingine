"""
Basic validation test to verify Pydantic works.
"""

from pydantic import BaseModel, EmailStr
from datetime import date
from decimal import Decimal


class BasicUser(BaseModel):
    """Basic user model."""
    email: EmailStr
    password: str


class BasicStock(BaseModel):
    """Basic stock model."""
    ticker: str
    company_name: str
    price: Decimal
    volume: int


def test_basic_validation():
    """Test basic validation functionality."""
    
    # Test user validation
    try:
        user = BasicUser(email="test@example.com", password="password123")
        print(f"✓ User validation works: {user.email}")
    except Exception as e:
        print(f"✗ User validation failed: {e}")
        return False
    
    # Test stock validation
    try:
        stock = BasicStock(
            ticker="7203",
            company_name="Toyota",
            price=Decimal("2500.00"),
            volume=1000000
        )
        print(f"✓ Stock validation works: {stock.ticker} - {stock.price}")
    except Exception as e:
        print(f"✗ Stock validation failed: {e}")
        return False
    
    # Test validation error
    try:
        invalid_user = BasicUser(email="invalid-email", password="123")
        print("✗ Should have failed validation")
        return False
    except Exception:
        print("✓ Validation error handling works")
    
    return True


if __name__ == "__main__":
    if test_basic_validation():
        print("\n✓ All basic validation tests passed!")
    else:
        print("\n✗ Some tests failed!")