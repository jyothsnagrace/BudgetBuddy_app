"""
Authentication Manager
Username-only authentication with JWT tokens
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import HTTPException, Header

# JWT Configuration
# Prefer JWT_SECRET_KEY, but support legacy JWT_SECRET for backward compatibility.
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET") or "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


class AuthManager:
    """Handles authentication and token management"""
    
    def __init__(self, db=None):
        # Use shared database client to avoid connection issues
        self.db = db
    
    async def login_or_create(self, username: str) -> Dict[str, Any]:
        """
        Login with username or create new user if doesn't exist
        """
        # Validate username
        if not username or len(username) < 3 or len(username) > 30:
            raise ValueError("Username must be 3-30 characters")
        
        # Check if user exists
        user = await self.db.get_user_by_username(username)
        
        if not user:
            # Create new user
            user = await self.db.create_user(username)
        else:
            # Update last activity
            await self.db.update_user_activity(user['id'])
        
        # Generate JWT token
        token = self.create_access_token(user['id'], username)
        
        return {
            'user_id': user['id'],
            'username': user['username'],
            'display_name': user.get('display_name', username),
            'token': token
        }
    
    def create_access_token(self, user_id: str, username: str) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
        
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': expire,
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return user data"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            user_id = payload.get('user_id')
            username = payload.get('username')
            
            if not user_id or not username:
                raise HTTPException(401, "Invalid token")
            
            return {
                'user_id': user_id,
                'username': username
            }
            
        except JWTError as e:
            raise HTTPException(401, f"Invalid token: {str(e)}")
    
    async def get_current_user(
        self,
        authorization: Optional[str] = Header(None)
    ) -> str:
        """
        Dependency for FastAPI endpoints
        Extracts and validates user from Authorization header
        """
        if not authorization:
            raise HTTPException(401, "Authorization header missing")
        
        # Extract token from "Bearer <token>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise HTTPException(401, "Invalid authorization header format")
        
        token = parts[1]
        
        # Verify token
        user_data = await self.verify_token(token)
        
        return user_data['user_id']
    
    def decode_token_payload(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode token without verification (for debugging)"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_signature": False})
            return payload
        except Exception:
            return None


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test():
        auth = AuthManager()
        
        # Test login/create
        result = await auth.login_or_create("testuser")
        print("Login result:", result)
        
        # Test token verification
        user_data = await auth.verify_token(result['token'])
        print("Verified user:", user_data)
    
    # Uncomment to test
    # asyncio.run(test())
    
    print("Auth manager module loaded successfully")
