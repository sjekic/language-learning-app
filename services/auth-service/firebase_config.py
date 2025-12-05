"""
Firebase Admin SDK Configuration
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, auth
from typing import Optional

_firebase_app: Optional[firebase_admin.App] = None


def initialize_firebase():
    """
    Initialize Firebase Admin SDK
    
    Two ways to configure:
    1. FIREBASE_SERVICE_ACCOUNT_KEY environment variable (JSON string)
    2. FIREBASE_SERVICE_ACCOUNT_PATH environment variable (path to JSON file)
    """
    global _firebase_app
    
    if _firebase_app is not None:
        return _firebase_app
    
    # Try to get service account from environment
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    
    if service_account_json:
        # Parse JSON string
        service_account_dict = json.loads(service_account_json)
        cred = credentials.Certificate(service_account_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized from FIREBASE_SERVICE_ACCOUNT_KEY")
    elif service_account_path:
        # Load from file path
        cred = credentials.Certificate(service_account_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        print(f"✅ Firebase initialized from {service_account_path}")
    else:
        # For local development without Firebase (optional fallback)
        print("⚠️  Warning: Firebase credentials not found. Set FIREBASE_SERVICE_ACCOUNT_KEY or FIREBASE_SERVICE_ACCOUNT_PATH")
        print("   Firebase authentication will not work!")
        return None
    
    return _firebase_app


def verify_firebase_token(id_token: str) -> dict:
    """
    Verify Firebase ID token and return decoded token
    
    Args:
        id_token: Firebase ID token from client
        
    Returns:
        dict: Decoded token with user information
        
    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        # Verify the token
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise ValueError(f"Invalid Firebase token: {str(e)}")


def get_firebase_user(uid: str) -> dict:
    """
    Get Firebase user by UID
    
    Args:
        uid: Firebase user UID
        
    Returns:
        dict: User information from Firebase
    """
    try:
        user = auth.get_user(uid)
        return {
            'uid': user.uid,
            'email': user.email,
            'email_verified': user.email_verified,
            'display_name': user.display_name,
            'photo_url': user.photo_url,
            'disabled': user.disabled
        }
    except Exception as e:
        raise ValueError(f"Failed to get Firebase user: {str(e)}")


def create_custom_token(uid: str) -> str:
    """
    Create a custom token for a user (optional, for advanced use cases)
    
    Args:
        uid: Firebase user UID
        
    Returns:
        str: Custom token
    """
    try:
        custom_token = auth.create_custom_token(uid)
        return custom_token.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to create custom token: {str(e)}")

