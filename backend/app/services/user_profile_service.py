"""
User profile service - minimal implementation for health check testing.
"""

from typing import Dict, Any, Optional
from app.models.user import User


class ProfileError(Exception):
    """Base exception for profile errors."""
    pass


class ProfileNotFoundError(ProfileError):
    """Raised when profile is not found."""
    pass


class InvalidProfileDataError(ProfileError):
    """Raised when profile data is invalid."""
    pass


class UserProfileService:
    """User profile service."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile."""
        # Minimal implementation for testing
        return {
            "user_id": user_id,
            "display_name": "Test User",
            "timezone": "Asia/Tokyo"
        }
    
    async def update_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile."""
        # Minimal implementation for testing
        return {
            "user_id": user_id,
            **profile_data
        }
    
    async def delete_profile(self, user_id: str) -> bool:
        """Delete user profile."""
        # Minimal implementation for testing
        return True