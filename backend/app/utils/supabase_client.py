"""
Supabase client initialization and utilities.

This module handles the connection to Supabase PostgreSQL database
and provides utility functions for database operations.
"""

import os
from dataclasses import dataclass
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

# Monkey-patch httpx to disable HTTP/2 globally
# This fixes Windows DNS resolution issues with HTTP/2 connections to Supabase
_original_httpx_client = httpx.Client
_original_httpx_async_client = httpx.AsyncClient

def _patched_httpx_client(*args, **kwargs):
    """Patched httpx.Client that disables HTTP/2."""
    kwargs['http2'] = False
    return _original_httpx_client(*args, **kwargs)

def _patched_httpx_async_client(*args, **kwargs):
    """Patched httpx.AsyncClient that disables HTTP/2."""
    kwargs['http2'] = False
    return _original_httpx_async_client(*args, **kwargs)

httpx.Client = _patched_httpx_client
httpx.AsyncClient = _patched_httpx_async_client


class SupabaseManager:
    """Manager for Supabase client initialization and connection."""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """
        Get or create Supabase client instance.
        
        Returns:
            Supabase Client instance
            
        Raises:
            ValueError: If SUPABASE_URL or SUPABASE_KEY not set
        """
        if cls._instance is None:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_KEY environment variables must be set"
                )
            
            # Create Supabase client (will use HTTP/1.1 due to httpx patching above)
            cls._instance = create_client(supabase_url, supabase_key)
        
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """
        Reset the Supabase client instance.
        Useful for testing or reinitializing the connection.
        """
        cls._instance = None


@dataclass(frozen=True)
class AuthenticatedContext:
    client: Client
    user_id: str


def get_authenticated_context(access_token: str) -> AuthenticatedContext:
    """Validate a Supabase access token and return an RLS-aware client."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY environment variables must be set"
        )

    client = create_client(supabase_url, supabase_key)
    user_response = client.auth.get_user(access_token)
    user = getattr(user_response, "user", None)
    user_id = getattr(user, "id", None)

    if not user_id:
        raise ValueError("Supabase access token did not identify a user")

    client.postgrest.auth(access_token)
    return AuthenticatedContext(client=client, user_id=user_id)


def get_supabase_client() -> Client:
    """
    Dependency injection function for Supabase client.
    
    Returns:
        Supabase Client instance
        
    Example:
        Can be used as a FastAPI dependency:
        @app.get("/transactions")
        async def get_transactions(client: Client = Depends(get_supabase_client)):
            ...
    """
    return SupabaseManager.get_client()
